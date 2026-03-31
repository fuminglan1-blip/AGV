#!/usr/bin/env python3
"""
agv_manual_controller.py — Persistent-state manual Ackermann controller
=======================================================================

Maintains two persistent states:
    target_speed       — changed only by w/s/SPACE/q or remote commands
    target_steer_angle — changed only by a/d/r/q or remote commands
A fixed-rate timer converts these to Twist via Ackermann geometry
and publishes to /agv/cmd_vel.  Rate-limiting provides smooth
acceleration and steering transitions.

Control inputs (two sources, same command set):
    1. Local keyboard  (when run in a terminal)
    2. /agv/control_cmd topic (std_msgs/String) — from Flask or mission controller

Supported commands (keyboard key → command string):
    w → speed_up       s → speed_down
    a → steer_left     d → steer_right
    SPACE → stop       r → center_steer
    q → reset_all

Mission-specific commands (from agv_mission_controller):
    set_speed:<value>       — set target speed directly (m/s)
    set_steer:<value>       — set target steer directly (rad)

Ackermann conversion:
    angular.z = speed × tan(steer_angle) / wheel_base

Configuration: agv_manual_config.yaml (same directory)
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
from std_msgs.msg import String


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


# ─── Command constants ────────────────────────────────────────────

KEY_TO_CMD = {
    'w': 'speed_up',
    's': 'speed_down',
    'a': 'steer_left',
    'd': 'steer_right',
    ' ': 'stop',
    'r': 'center_steer',
    'q': 'reset_all',
}


# ─── Controller node ─────────────────────────────────────────────

class AGVManualController(Node):

    def __init__(self, cfg):
        super().__init__('agv_manual_controller')

        # Vehicle geometry & limits
        self.wheel_base     = cfg['wheel_base']
        self.max_speed      = cfg['max_speed']
        self.max_reverse    = cfg.get('max_reverse_speed', self.max_speed * 0.4)
        self.max_steer      = cfg['max_steer_angle']
        self.max_accel      = cfg['max_accel']
        self.max_steer_rate = cfg['max_steer_rate']
        self.speed_step     = cfg.get('speed_step', 0.2)
        self.steer_step     = cfg.get('steer_step', 0.05)
        self.publish_rate   = cfg.get('publish_rate', 20)

        # ── Persistent control state ──
        self.target_speed  = 0.0
        self.target_steer  = 0.0
        self.current_speed = 0.0
        self.current_steer = 0.0

        # Publisher: /agv/cmd_vel
        topic = cfg.get('cmd_vel_topic', '/agv/cmd_vel')
        self.pub = self.create_publisher(Twist, topic, 10)

        # Subscriber: /agv/control_cmd — remote commands from Flask / mission
        self.create_subscription(
            String, '/agv/control_cmd', self._on_control_cmd, 10)

        # Fixed-rate publish timer
        self.dt = 1.0 / self.publish_rate
        self.timer = self.create_timer(self.dt, self._publish)

        self._display_lines = 0
        self.get_logger().info(
            f'Ready — {topic} @ {self.publish_rate} Hz, '
            f'listening on /agv/control_cmd')

    # ── Remote command handler ────────────────────────────────────

    def _on_control_cmd(self, msg: String):
        """Handle commands from /agv/control_cmd topic."""
        self.execute_command(msg.data)

    # ── Unified command execution ─────────────────────────────────

    def execute_command(self, cmd: str):
        """Execute a named command (from keyboard or remote)."""
        if cmd == 'speed_up':
            self.target_speed = min(
                self.target_speed + self.speed_step, self.max_speed)
        elif cmd == 'speed_down':
            self.target_speed = max(
                self.target_speed - self.speed_step, -self.max_reverse)
        elif cmd == 'steer_left':
            self.target_steer = min(
                self.target_steer + self.steer_step, self.max_steer)
        elif cmd == 'steer_right':
            self.target_steer = max(
                self.target_steer - self.steer_step, -self.max_steer)
        elif cmd == 'stop':
            self.target_speed = 0.0
        elif cmd == 'center_steer':
            self.target_steer = 0.0
        elif cmd == 'reset_all':
            self.target_speed = 0.0
            self.target_steer = 0.0
        elif cmd.startswith('set_speed:'):
            try:
                v = float(cmd.split(':', 1)[1])
                self.target_speed = max(-self.max_reverse,
                                        min(v, self.max_speed))
            except ValueError:
                pass
        elif cmd.startswith('set_steer:'):
            try:
                s = float(cmd.split(':', 1)[1])
                self.target_steer = max(-self.max_steer,
                                         min(s, self.max_steer))
            except ValueError:
                pass

    def handle_key(self, key):
        """Translate keypress to command and execute."""
        cmd = KEY_TO_CMD.get(key)
        if cmd:
            self.execute_command(cmd)

    # ── Fixed-rate publish with rate limiting ─────────────────────

    def _publish(self):
        self.current_speed = self._approach(
            self.current_speed, self.target_speed,
            self.max_accel * self.dt)
        self.current_steer = self._approach(
            self.current_steer, self.target_steer,
            self.max_steer_rate * self.dt)

        v     = self.current_speed
        delta = self.current_steer

        # Ackermann: omega = v * tan(delta) / L
        # Tiny creep when stopped with steering set (see module docstring)
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
        diff = target - current
        if abs(diff) <= max_step:
            return target
        return current + math.copysign(max_step, diff)

    # ── Emergency stop ────────────────────────────────────────────

    def stop(self):
        self.target_speed = self.target_steer = 0.0
        self.current_speed = self.current_steer = 0.0
        try:
            self.pub.publish(Twist())
        except Exception:
            pass

    # ── Terminal status display ───────────────────────────────────

    def print_status(self):
        ts = self.target_speed
        cs = self.current_speed
        ta_deg = math.degrees(self.target_steer)
        ca_deg = math.degrees(self.current_steer)

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
            f'  (also accepts remote commands on /agv/control_cmd)',
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
        # Headless mode: only accept remote commands via /agv/control_cmd
        print('[agv_manual_controller] Running headless (no keyboard).')
        print('  Send commands via: ros2 topic pub /agv/control_cmd std_msgs/String "data: speed_up"')
        try:
            rclpy.spin(ctrl)
        except KeyboardInterrupt:
            pass
        finally:
            ctrl.stop()
            ctrl.destroy_node()
            rclpy.shutdown()
        return

    settings = termios.tcgetattr(sys.stdin)

    print()
    print('╔══════════════════════════════════════════════╗')
    print('║   AGV Manual Controller  (Ackermann)         ║')
    print('║   Steering HOLDS between keypresses          ║')
    print('║   Also accepts /agv/control_cmd (remote)     ║')
    print('╚══════════════════════════════════════════════╝')

    try:
        while rclpy.ok():
            key = get_key(settings, timeout=0.02)

            if key in ('\x1b', '\x03'):
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
