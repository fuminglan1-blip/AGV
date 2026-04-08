#!/bin/bash
# AGV Digital Twin Web Dashboard Startup Script
# This script starts the Flask backend server with ROS2 integration

# Get the directory where this script is located (web_dashboard/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SRC_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

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
    echo "[start_server] Error: ROS2 setup.bash not found under /opt/ros" >&2
    return 1
  fi

  export ROS_DISTRO="${distro}"
  echo "/opt/ros/${distro}/setup.bash"
}

ROS_SETUP_FILE="$(resolve_ros_setup)"

# Kill any existing Flask processes
pkill -f "python3 app.py" 2>/dev/null
sleep 1

# Source ROS2 and workspace
source "$ROS_SETUP_FILE"
if [[ ! -f "$SRC_DIR/install/setup.bash" ]]; then
  echo "[start_server] Error: $SRC_DIR/install/setup.bash not found. Run colcon build first." >&2
  exit 1
fi
source "$SRC_DIR/install/setup.bash"

# Change to script directory and start Flask backend
cd "$SCRIPT_DIR"
python3 app.py
