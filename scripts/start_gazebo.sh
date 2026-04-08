#!/bin/bash
# Start Gazebo simulation with the default 400 m experiment world.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/common_env.sh"

if [[ "${AGV_WS_SETUP_LOADED:-0}" -ne 1 ]]; then
  echo "[start_gazebo] Error: workspace overlay is not available." >&2
  echo "[start_gazebo] Run 'colcon build --symlink-install' on this machine first." >&2
  exit 1
fi

echo "[start_gazebo] Launching Gazebo default scene..."
echo "[start_gazebo] Default scene: simplified_port_agv_terrain_400m (400m experiment world)"
echo "[start_gazebo] Legacy compatibility entry: harbour_diff_drive.launch.py"
echo "[start_gazebo] Active runtime chain: agv_ackermann + /agv/*"
ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py
