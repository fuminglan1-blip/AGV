#!/usr/bin/env python3
"""
agv_manual_controller.py — Persistent-state manual Ackermann controller
=======================================================================

Problem solved:
    teleop_twist_keyboard sends a full Twist per keypress — pressing
    'forward' emits {linear.x: V, angular.z: 0}, which resets steering
    to zero.  Speed and steering are coupled in a single message rather
    than being independent state variables.

Solution:
    This node maintains two persistent states:
        target_speed       — changed only by w/s/SPACE/q
        target_steer_angle — changed only by a/d/r/q
    A fixed-rate timer converts these to Twist via Ackermann geometry
    and publishes to /agv/cmd_vel.  Rate-limiting provides smooth
    acceleration and steering transitions.

Ackermann conversion:
    angular.z = speed × tan(steer_angle) / wheel_base

    When stopped (speed ≈ 0) with non-zero steering, a tiny 0.01 m/s
    creep is sent so the plugin maintains the correct wheel angle.
    (AckermannSteering computes steer = atan2(ω·L, |v|); when v=0
    the angle jumps to ±max regardless of ω.)

Usage:
    source /opt/ros/humble/setup.bash
    source install/setup.bash
    python3 agv_manual_controller.py

Keys:
    w / s     increase / decrease target speed
    a / d     steer left / right  (angle holds between presses)
    SPACE     emergency stop  (speed → 0, steering preserved)
    r         center steering (speed preserved)
    q         full reset      (speed → 0, steering → 0)
    ESC       quit            (sends stop command first)

Configuration:
    agv_manual_config.yaml  (same directory as this script)
"""

import math
import os
import select
import sys
import termios
import tty

import yaml
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


# ─── Config loader ────────────────────────────────────────────────

def load_config():
    cfg_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'agv_manual_config.yaml')
    with open(cfg_path, 'r') as f:
        return yaml.safe_load(f)


# ─── Non-blocking key reader ─────────────────────────────────────

def get_key(settings, timeout=0.02):
    """Read one character from stdin without blocking (returns '' on timeout)."""
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    key = sys.stdin.read(1) if rlist else ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


# ─── Controller node ─────────────────────────────────────────────

class AGVManualController(Node):

    def __init__(self, cfg):
        super().__init__('agv_manual_controller')

        # Vehicle geometry & limits (from config, matches model.sdf)
        self.wheel_base    = cfg['wheel_base']
        self.max_speed     = cfg['max_speed']
        self.max_reverse   = cfg.get('max_reverse_speed', self.max_speed * 0.4)
        self.max_steer     = cfg['max_steer_angle']
        self.max_accel     = cfg['max_accel']
        self.max_steer_rate = cfg['max_steer_rate']
        self.speed_step    = cfg.get('speed_step', 0.2)
        self.steer_step    = cfg.get('steer_step', 0.05)
        self.publish_rate  = cfg.get('publish_rate', 20)

        # ── Persistent control state ──
        self.target_speed  = 0.0    # m/s, + = forward
        self.target_steer  = 0.0    # rad, + = left
        self.current_speed = 0.0    # rate-limited actual
        self.current_steer = 0.0    # rate-limited actual

        # Publisher
        topic = cfg.get('cmd_vel_topic', '/agv/cmd_vel')
        self.pub = self.create_publisher(Twist, topic, 10)

        # Fixed-rate publish timer
        self.dt = 1.0 / self.publish_rate
        self.timer = self.create_timer(self.dt, self._publish)

        # Display helper
        self._display_lines = 0

        self.get_logger().info(
            f'Ready — publishing {topic} @ {self.publish_rate} Hz')

    # ── Keyboard → state ──────────────────────────────────────────

    def handle_key(self, key):
        """Update target state from a single keypress."""
        if key == 'w':
            self.target_speed = min(
                self.target_speed + self.speed_step, self.max_speed)
        elif key == 's':
            self.target_speed = max(
                self.target_speed - self.speed_step, -self.max_reverse)
        elif key == 'a':                       # steer left (+)
            self.target_steer = min(
                self.target_steer + self.steer_step, self.max_steer)
        elif key == 'd':                       # steer right (−)
            self.target_steer = max(
                self.target_steer - self.steer_step, -self.max_steer)
        elif key == ' ':                       # emergency stop
            self.target_speed = 0.0
        elif key == 'r':                       # center steering
            self.target_steer = 0.0
        elif key == 'q':                       # full reset
            self.target_speed = 0.0
            self.target_steer = 0.0

    # ── Fixed-rate publish with rate limiting ─────────────────────

    def _publish(self):
        # Smooth approach to targets
        self.current_speed = self._approach(
            self.current_speed, self.target_speed,
            self.max_accel * self.dt)
        self.current_steer = self._approach(
            self.current_steer, self.target_steer,
            self.max_steer_rate * self.dt)

        v     = self.current_speed
        delta = self.current_steer

        # Ackermann: omega = v * tan(delta) / L
        #
        # When stopped with non-zero steering, the AckermannSteering
        # plugin cannot hold an arbitrary wheel angle (it computes
        # steer = atan2(ω·L, |v|) — when v=0 the angle saturates).
        # Workaround: send a tiny 0.01 m/s creep so the geometry
        # resolves correctly.  The vehicle moves ~1 cm/s — negligible.
        if abs(v) < 0.01 and abs(delta) > 0.001:
            v_eff = 0.01
        else:
            v_eff = v

        msg = Twist()
        msg.linear.x = v_eff
        if abs(v_eff) > 1e-6:
            msg.angular.z = v_eff * math.tan(delta) / self.wheel_base
        else:
            msg.angular.z = 0.0

        self.pub.publish(msg)

    @staticmethod
    def _approach(current, target, max_step):
        """Move current toward target by at most max_step."""
        diff = target - current
        if abs(diff) <= max_step:
            return target
        return current + math.copysign(max_step, diff)

    # ── Send zero and clear state ─────────────────────────────────

    def stop(self):
        self.target_speed = self.target_steer = 0.0
        self.current_speed = self.current_steer = 0.0
        self.pub.publish(Twist())

    # ── Terminal status display ───────────────────────────────────

    def print_status(self):
        ts = self.target_speed
        cs = self.current_speed
        ta_deg = math.degrees(self.target_steer)
        ca_deg = math.degrees(self.current_steer)

        # Visual steering bar: left ←──│──→ right
        bar_w = 21
        mid = bar_w // 2
        pos = mid - int(round(
            self.current_steer / self.max_steer * mid))
        pos = max(0, min(bar_w - 1, pos))
        bar = list('─' * bar_w)
        bar[mid] = '│'
        bar[pos] = '◆'

        lines = [
            '',
            f'  Speed : {ts:+5.2f} → {cs:+5.2f} m/s'
            f'    (max fwd {self.max_speed}, rev {self.max_reverse})',
            f'  Steer : {ta_deg:+6.1f} → {ca_deg:+6.1f}°'
            f'    (max ±{math.degrees(self.max_steer):.0f}°)',
            f'     L  {"".join(bar)}  R',
            f'  ─────────────────────────────────────────────',
            f'  w/s: speed ↑↓   a/d: steer ←→',
            f'  SPACE: stop   r: center steer   q: reset   ESC: quit',
        ]

        if self._display_lines > 0:
            sys.stdout.write(f'\033[{self._display_lines}A')
        for line in lines:
            sys.stdout.write(f'\r{line}\033[K\n')
        sys.stdout.flush()
        self._display_lines = len(lines)


# ─── Entry point ──────────────────────────────────────────────────

def main():
    cfg = load_config()
    rclpy.init()
    ctrl = AGVManualController(cfg)

    if not sys.stdin.isatty():
        print('Error: stdin is not a terminal. Run this in an interactive shell.')
        ctrl.destroy_node()
        rclpy.shutdown()
        return

    settings = termios.tcgetattr(sys.stdin)

    print()
    print('╔══════════════════════════════════════════════╗')
    print('║   AGV Manual Controller  (Ackermann)         ║')
    print('║   Steering HOLDS between keypresses          ║')
    print('╚══════════════════════════════════════════════╝')

    try:
        while rclpy.ok():
            key = get_key(settings, timeout=0.02)

            if key in ('\x1b', '\x03'):        # ESC or Ctrl-C
                break
            if key:
                ctrl.handle_key(key)

            rclpy.spin_once(ctrl, timeout_sec=0)
            ctrl.print_status()

    except Exception as e:
        print(f'\nError: {e}')
    finally:
        ctrl.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        ctrl.destroy_node()
        rclpy.shutdown()
        print('\n\nStopped.')


if __name__ == '__main__':
    main()
