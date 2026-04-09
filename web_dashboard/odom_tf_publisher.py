#!/usr/bin/env python3
"""
odom_tf_publisher.py — Broadcasts odom -> chassis TF from /agv/odometry
========================================================================

The Gazebo AckermannSteering plugin publishes nav_msgs/Odometry to
/agv/odometry, but does NOT publish the corresponding odom -> base_link
TF transform (the OdometryPublisher was removed to avoid TF conflicts
with PosePublisher).

This lightweight node subscribes to /agv/odometry and mirrors the odometry
message's own frame ids into TF so RViz follows the same odom/chassis chain
as Gazebo, instead of inventing a second legacy tree.

Usage:
    python3 odom_tf_publisher.py
    # or launched from simplified_port_agv_terrain_400m.launch.py
    # legacy compatibility launch: harbour_diff_drive.launch.py
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class OdomTFPublisher(Node):

    def __init__(self):
        super().__init__('odom_tf_publisher')
        self.br = TransformBroadcaster(self)
        self.create_subscription(Odometry, '/agv/odometry', self._on_odom, 10)
        self.get_logger().info('Broadcasting odom -> chassis TF from /agv/odometry')

    def _on_odom(self, msg: Odometry):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = msg.header.frame_id or 'agv_ackermann/odom'
        t.child_frame_id = msg.child_frame_id or 'agv_ackermann/chassis'

        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation

        self.br.sendTransform(t)


def main():
    node = None
    try:
        rclpy.init()
        node = OdomTFPublisher()
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
