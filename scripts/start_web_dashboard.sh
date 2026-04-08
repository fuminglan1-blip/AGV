#!/bin/bash
# Start Flask web dashboard + mission controller
# Launches agv_mission_controller.py in background, then app.py in foreground.
# On exit, cleans up the background process.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WEB_DIR="${SRC_DIR}/web_dashboard"
MISSION_PID=""

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
    echo "[start_web_dashboard] Error: ROS2 setup.bash not found under /opt/ros" >&2
    return 1
  fi

  export ROS_DISTRO="${distro}"
  echo "/opt/ros/${distro}/setup.bash"
}

ROS_SETUP_FILE="$(resolve_ros_setup)"

cleanup() {
  echo ""
  echo "[start_web_dashboard] Shutting down..."
  if [[ -n "${MISSION_PID}" ]] && kill -0 "${MISSION_PID}" 2>/dev/null; then
    echo "[start_web_dashboard] Stopping agv_mission_controller (PID ${MISSION_PID})..."
    kill "${MISSION_PID}" 2>/dev/null
    wait "${MISSION_PID}" 2>/dev/null || true
  fi
  echo "[start_web_dashboard] Cleanup done."
}

trap cleanup EXIT INT TERM

set +u
source "${ROS_SETUP_FILE}"
if [[ ! -f "${SRC_DIR}/install/setup.bash" ]]; then
  echo "[start_web_dashboard] Error: ${SRC_DIR}/install/setup.bash not found. Run colcon build first." >&2
  exit 1
fi
source "${SRC_DIR}/install/setup.bash"
set -u

cd "${WEB_DIR}"

echo "[start_web_dashboard] Starting agv_mission_controller.py in background..."
python3 agv_mission_controller.py &
MISSION_PID=$!

echo "[start_web_dashboard] Starting Flask app (app.py)..."
python3 app.py
