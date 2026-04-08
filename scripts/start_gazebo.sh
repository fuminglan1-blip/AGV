#!/bin/bash
# Start Gazebo simulation with harbour world and agv_ackermann
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Keep startup portable across Ubuntu/ROS2 versions by resolving setup path at runtime.
resolve_ros_setup() {
  local distro=""
  if [[ -n "${ROS_DISTRO:-}" ]] && [[ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]]; then
    distro="${ROS_DISTRO}"
  elif [[ -f "/opt/ros/jazzy/setup.bash" ]]; then
    distro="jazzy"
  else
    distro="$(ls /opt/ros 2>/dev/null | head -n1 || true)"
  fi

  if [[ -z "${distro}" ]] || [[ ! -f "/opt/ros/${distro}/setup.bash" ]]; then
    echo "[start_gazebo] Error: ROS2 setup.bash not found under /opt/ros" >&2
    return 1
  fi

  export ROS_DISTRO="${distro}"
  echo "/opt/ros/${distro}/setup.bash"
}

ROS_SETUP_FILE="$(resolve_ros_setup)"

set +u
source "${ROS_SETUP_FILE}"
if [[ ! -f "${SRC_DIR}/install/setup.bash" ]]; then
  echo "[start_gazebo] Error: ${SRC_DIR}/install/setup.bash not found. Run colcon build first." >&2
  exit 1
fi
source "${SRC_DIR}/install/setup.bash"
set -u

echo "[start_gazebo] Launching Gazebo harbour simulation..."
ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py
