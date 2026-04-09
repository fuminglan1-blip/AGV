#!/usr/bin/env python3
"""
odom_visual_helper.py — High-visibility RViz markers for AGV motion
====================================================================

Publishes a continuous trailing path for RViz visualization:

  /agv/odom_path_vis  (nav_msgs/Path)
   - Continuous trailing path (last ~260 poses) showing recent trajectory
   - Raised slightly above ground to avoid z-fighting with grid

Subscribes to: /agv/odometry
Does NOT modify any control or physics topics.

Usage:
    python3 odom_visual_helper.py
    # or launched from simplified_port_agv_terrain_400m.launch.py
    # legacy compatibility launch: harbour_diff_drive.launch.py
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import PoseStamped
from collections import deque
from math import sqrt


class OdomVisualHelper(Node):

    def __init__(self):
        super().__init__('odom_visual_helper')

        # Config
        self.path_z_offset = 0.10       # meters above ground
        self.path_max_points = 260
        self.min_dist_between_points = 0.12  # smooth enough for a readable curve
        self.max_segment_distance_m = 3.0    # reset path on spawn / reset jumps

        # State
        self.path_points = deque(maxlen=self.path_max_points)
        self.last_x = None
        self.last_y = None
        self.last_frame_id = None
        self.last_stamp_ns = None
        self.last_reset_log_ns = 0

        # Publisher (path only — vehicle heading arrow removed for cleaner display)
        self.path_pub = self.create_publisher(Path, '/agv/odom_path_vis', 10)

        # Subscriber
        self.create_subscription(Odometry, '/agv/odometry', self._on_odom, 10)

        self.get_logger().info('Visual helper active: /agv/odom_path_vis')

    def _make_pose_stamped(self, frame_id, stamp, x, y, z, orientation):
        ps = PoseStamped()
        ps.header.frame_id = frame_id
        ps.header.stamp = stamp
        ps.pose.position.x = x
        ps.pose.position.y = y
        ps.pose.position.z = z + self.path_z_offset
        ps.pose.orientation = orientation
        return ps

    def _reset_path(self, frame_id, x, y, pose_stamped):
        self.path_points.clear()
        self.path_points.append(pose_stamped)
        self.last_x = x
        self.last_y = y
        self.last_frame_id = frame_id
        self.last_stamp_ns = (
            pose_stamped.header.stamp.sec * 1_000_000_000 +
            pose_stamped.header.stamp.nanosec
        )

    def _log_reset(self, reason, distance_m=None):
        now_ns = self.get_clock().now().nanoseconds
        if now_ns - self.last_reset_log_ns < 2_000_000_000:
            return
        self.last_reset_log_ns = now_ns
        if distance_m is None:
            self.get_logger().info(f'Resetting RViz path: {reason}')
        else:
            self.get_logger().info(
                f'Resetting RViz path: {reason} (jump={distance_m:.2f} m)')

    def _on_odom(self, msg: Odometry):
        frame_id = msg.header.frame_id or 'agv_ackermann/odom'
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        z = msg.pose.pose.position.z
        orientation = msg.pose.pose.orientation
        stamp = msg.header.stamp
        stamp_ns = stamp.sec * 1_000_000_000 + stamp.nanosec
        pose_stamped = self._make_pose_stamped(frame_id, stamp, x, y, z, orientation)

        # ── Trailing path ─────────────────────────────────────────
        # Gazebo restart / respawn can rewind sim time back near zero while this
        # helper is still alive. If we keep the old deque, RViz draws a fake
        # connector from the previous run into the new one.
        if self.last_stamp_ns is not None and stamp_ns < self.last_stamp_ns:
            self._log_reset('simulation time moved backwards')
            self._reset_path(frame_id, x, y, pose_stamped)
        # First valid sample starts the path at the current vehicle pose.
        elif self.last_x is None or self.last_y is None or self.last_frame_id is None:
            self._reset_path(frame_id, x, y, pose_stamped)
        elif frame_id != self.last_frame_id:
            self._log_reset(
                f'frame changed from {self.last_frame_id} to {frame_id}')
            self._reset_path(frame_id, x, y, pose_stamped)
        else:
            dx = x - self.last_x
            dy = y - self.last_y
            segment_distance_m = sqrt(dx * dx + dy * dy)

            # Spawn/reset/teleport jumps should restart the path instead of
            # drawing a long straight connector across the scene.
            if segment_distance_m > self.max_segment_distance_m:
                self._log_reset('detected odom jump', segment_distance_m)
                self._reset_path(frame_id, x, y, pose_stamped)
            elif segment_distance_m >= self.min_dist_between_points:
                self.last_x = x
                self.last_y = y
                self.last_stamp_ns = stamp_ns
                self.path_points.append(pose_stamped)
            else:
                self.last_stamp_ns = stamp_ns

        path_msg = Path()
        path_msg.header.frame_id = frame_id
        path_msg.header.stamp = stamp
        path_msg.poses = list(self.path_points)
        self.path_pub.publish(path_msg)


def main():
    node = None
    try:
        rclpy.init()
        node = OdomVisualHelper()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            try:
                node.destroy_node()
            except Exception:
                pass
            try:
                if rclpy.ok(context=node.context):
                    rclpy.shutdown(context=node.context)
            except Exception:
                pass


if __name__ == '__main__':
    main()
