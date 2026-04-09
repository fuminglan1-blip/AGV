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

relaunch_in_gui_terminal_if_needed() {
  # Gazebo GUI can render as a black window when launched from non-interactive
  # shells such as IDE task runners where TERM is "dumb". Reuse the same script
  # inside a real graphical terminal so direct launches behave like start_all.sh.
  if [[ "${AGV_GAZEBO_GUI_RELAUNCHED:-0}" == "1" ]]; then
    return 0
  fi

  if [[ -z "${DISPLAY:-}" ]]; then
    return 0
  fi

  if [[ "${TERM:-dumb}" != "dumb" ]]; then
    return 0
  fi

  if ! command -v gnome-terminal &>/dev/null; then
    return 0
  fi

  echo "[start_gazebo] Detected a non-GUI shell context (TERM=${TERM:-unset})."
  echo "[start_gazebo] Relaunching Gazebo in gnome-terminal to avoid a black GUI window..."
  printf -v SCRIPT_DIR_Q '%q' "${SCRIPT_DIR}"
  gnome-terminal -- bash -lc \
    "cd ${SCRIPT_DIR_Q} && AGV_GAZEBO_GUI_RELAUNCHED=1 ./start_gazebo.sh; exec bash" &
  disown || true
  exit 0
}

cleanup_gazebo_processes() {
  # Clean both direct `gz sim ...` runs and launch-managed Gazebo chains so a
  # stale simulator does not keep publishing a second vehicle state source.
  agv_stop_processes "start_gazebo" \
    'gz sim' \
    'ign gazebo' \
    'ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py' \
    'ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py' \
    'ros_gz_bridge' \
    'robot_state_publisher'
}

echo "[start_gazebo] Launching Gazebo default scene..."
echo "[start_gazebo] Default scene: simplified_port_agv_terrain_400m (400m experiment world)"
echo "[start_gazebo] Legacy compatibility entry: harbour_diff_drive.launch.py"
echo "[start_gazebo] Active runtime chain: agv_ackermann + /agv/*"
relaunch_in_gui_terminal_if_needed
cleanup_gazebo_processes
exec ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py
