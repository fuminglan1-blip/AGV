#!/bin/bash
# Stop the full local AGV simulation stack so the next launch starts cleanly.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/common_env.sh"

echo "[stop_all] Stopping local AGV simulation stack..."

agv_stop_processes "stop_all" \
  'python3 app.py' \
  'python3 agv_mission_controller.py' \
  'python3 agv_manual_controller.py' \
  'python3 odom_tf_publisher.py' \
  'python3 odom_visual_helper.py' \
  'ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py' \
  'ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py' \
  'gz sim' \
  'ign gazebo' \
  'ros_gz_bridge' \
  'robot_state_publisher' \
  'rviz2'

echo "[stop_all] Done."
