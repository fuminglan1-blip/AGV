#!/usr/bin/env python3
"""
agv_mission_controller.py — Waypoint-following mission executor
================================================================

Drives agv_ackermann through a sequence of predefined waypoints.
Does NOT publish /agv/cmd_vel directly — instead sends high-level
commands to agv_manual_controller via /agv/control_cmd (String).
This preserves all rate-limiting and Ackermann conversion in one place.

Control flow:
    /agv/odometry  →  this node  →  /agv/control_cmd  →  agv_manual_controller
                                                               ↓
                                                        /agv/cmd_vel (Twist)

Mission commands (received via /agv/mission_cmd String topic):
    start:<route_name>    — load route and begin following
    cancel                — abort current mission, send stop

Mission status (published to /agv/mission_status String topic):
    JSON: {"mode","route_name","running","progress","waypoint_index","total_waypoints"}

Waypoint tracking algorithm:
    1. Compute heading error to current waypoint
    2. If heading error > tolerance: rotate in place (set_speed:slow, set_steer:angle)
    3. If heading OK: drive toward waypoint (set_speed:cruise, set_steer:proportional)
    4. When within arrive_radius: advance to next waypoint
    5. When all waypoints done: stop and report complete

Configuration: config/demo_routes.yaml
"""

import json
import math
import os
import time

import yaml
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import String


def load_routes():
    cfg_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'config', 'demo_routes.yaml')
    with open(cfg_path, 'r') as f:
        return yaml.safe_load(f)


def normalize_angle(a):
    """Normalize angle to [-pi, pi]."""
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


class AGVMissionController(Node):

    def __init__(self):
        super().__init__('agv_mission_controller')

        # Load route config
        cfg = load_routes()
        self.routes = cfg.get('demo_routes', {})
        wp_cfg = cfg.get('waypoint_tracking', {})
        self.arrive_radius = wp_cfg.get('arrive_radius', 1.5)
        self.cruise_speed  = wp_cfg.get('speed', 1.0)
        self.slow_radius   = wp_cfg.get('slow_radius', 3.0)
        self.slow_speed    = wp_cfg.get('slow_speed', 0.5)
        self.heading_tol   = wp_cfg.get('heading_tolerance', 0.3)

        # Mission state
        self.mode = 'idle'           # idle | mission
        self.route_name = ''
        self.waypoints = []
        self.wp_index = 0
        self.running = False

        # Current vehicle pose (from odometry)
        self.veh_x = 0.0
        self.veh_y = 0.0
        self.veh_yaw = 0.0          # radians

        # ROS2 interfaces
        self.cmd_pub = self.create_publisher(
            String, '/agv/control_cmd', 10)
        self.status_pub = self.create_publisher(
            String, '/agv/mission_status', 10)

        self.create_subscription(
            Odometry, '/agv/odometry', self._on_odom, 10)
        self.create_subscription(
            String, '/agv/mission_cmd', self._on_mission_cmd, 10)

        # Control loop at 10 Hz
        self.create_timer(0.1, self._control_loop)
        # Status publish at 2 Hz
        self.create_timer(0.5, self._publish_status)

        self.get_logger().info(
            f'Mission controller ready — {len(self.routes)} routes loaded')

    # ── Odometry callback ─────────────────────────────────────────

    def _on_odom(self, msg: Odometry):
        self.veh_x = msg.pose.pose.position.x
        self.veh_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.veh_yaw = math.atan2(siny, cosy)

    # ── Mission command handler ───────────────────────────────────

    def _on_mission_cmd(self, msg: String):
        cmd = msg.data.strip()

        if cmd.startswith('start:'):
            route_name = cmd.split(':', 1)[1]
            self._start_mission(route_name)
        elif cmd == 'cancel':
            self._cancel_mission()

    def _start_mission(self, route_name: str):
        if route_name not in self.routes:
            self.get_logger().warn(f'Unknown route: {route_name}')
            return

        route = self.routes[route_name]
        wps = route.get('waypoints', route) if isinstance(route, dict) else route
        if not wps:
            return

        self.route_name = route_name
        self.waypoints = [(w[0], w[1]) for w in wps]
        self.wp_index = 0
        self.running = True
        self.mode = 'mission'
        self.get_logger().info(
            f'Mission started: {route_name} ({len(self.waypoints)} waypoints)')

    def _cancel_mission(self):
        self.running = False
        self.mode = 'idle'
        self.route_name = ''
        self.waypoints = []
        self.wp_index = 0
        # Stop the vehicle
        self._send_cmd('reset_all')
        self.get_logger().info('Mission cancelled')

    # ── Main control loop (10 Hz) ─────────────────────────────────

    def _control_loop(self):
        if not self.running or self.wp_index >= len(self.waypoints):
            if self.running:
                # All waypoints reached
                self.running = False
                self.mode = 'idle'
                self._send_cmd('reset_all')
                self.get_logger().info(
                    f'Mission complete: {self.route_name}')
            return

        # Current target waypoint
        tx, ty = self.waypoints[self.wp_index]
        dx = tx - self.veh_x
        dy = ty - self.veh_y
        dist = math.sqrt(dx * dx + dy * dy)

        # Check arrival
        if dist < self.arrive_radius:
            self.wp_index += 1
            self.get_logger().info(
                f'Waypoint {self.wp_index}/{len(self.waypoints)} reached')
            return

        # Desired heading to waypoint
        desired_yaw = math.atan2(dy, dx)
        heading_err = normalize_angle(desired_yaw - self.veh_yaw)

        # Proportional steering (clamped)
        # Gain: 1.5 gives responsive but stable steering for 3m wheelbase
        steer_cmd = max(-0.5, min(0.5, heading_err * 1.5))

        # Speed: slow down near waypoint or when heading is off
        if dist < self.slow_radius:
            speed_cmd = self.slow_speed
        elif abs(heading_err) > self.heading_tol * 2:
            speed_cmd = self.slow_speed
        else:
            speed_cmd = self.cruise_speed

        # If heading is very wrong, slow down more to turn
        if abs(heading_err) > math.pi / 3:
            speed_cmd = 0.3

        self._send_cmd(f'set_speed:{speed_cmd:.3f}')
        self._send_cmd(f'set_steer:{steer_cmd:.4f}')

    # ── Status publisher (2 Hz) ───────────────────────────────────

    def _publish_status(self):
        status = {
            'mode': self.mode,
            'route_name': self.route_name,
            'running': self.running,
            'waypoint_index': self.wp_index,
            'total_waypoints': len(self.waypoints),
            'progress': (f'{self.wp_index}/{len(self.waypoints)}'
                         if self.waypoints else ''),
        }
        msg = String()
        msg.data = json.dumps(status)
        self.status_pub.publish(msg)

    # ── Helper ────────────────────────────────────────────────────

    def _send_cmd(self, cmd: str):
        msg = String()
        msg.data = cmd
        self.cmd_pub.publish(msg)


def main():
    rclpy.init()
    node = AGVMissionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._cancel_mission()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
