#!/bin/bash
# Start AGV manual controller
# Usage:
#   ./start_controller.sh              # interactive mode (keyboard control)
#   ./start_controller.sh headless     # headless mode (remote control only)
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-interactive}"

# Runtime detection keeps this script compatible with Ubuntu 24.04 / ROS2 Jazzy.
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
    echo "[start_controller] Error: ROS2 setup.bash not found under /opt/ros" >&2
    return 1
  fi

  export ROS_DISTRO="${distro}"
  echo "/opt/ros/${distro}/setup.bash"
}

ROS_SETUP_FILE="$(resolve_ros_setup)"

set +u
source "${ROS_SETUP_FILE}"
if [[ ! -f "${SRC_DIR}/install/setup.bash" ]]; then
  echo "[start_controller] Error: ${SRC_DIR}/install/setup.bash not found. Run colcon build first." >&2
  exit 1
fi
source "${SRC_DIR}/install/setup.bash"
set -u

cd "${SRC_DIR}"

case "${MODE}" in
  interactive)
    echo "[start_controller] Starting in interactive mode (keyboard control)..."
    python3 agv_manual_controller.py
    ;;
  headless)
    echo "[start_controller] Starting in headless mode (remote control only)..."
    python3 agv_manual_controller.py < /dev/null
    ;;
  *)
    echo "Error: unknown mode '${MODE}'. Use 'interactive' or 'headless'."
    exit 1
    ;;
esac
