#!/bin/bash
# One-click launch: opens 3 gnome-terminal windows for the full simulation stack.
# Usage:
#   ./start_all.sh              # controller in interactive mode
#   ./start_all.sh headless     # controller in headless mode
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-interactive}"
printf -v SCRIPT_DIR_Q '%q' "${SCRIPT_DIR}"
printf -v MODE_Q '%q' "${MODE}"

source "${SCRIPT_DIR}/common_env.sh"

if [[ "${AGV_WS_SETUP_LOADED:-0}" -ne 1 ]]; then
  echo "[start_all] Error: workspace overlay is not available on this machine." >&2
  echo "[start_all] Run 'colcon build --symlink-install' before launching the full stack." >&2
  exit 1
fi

if ! command -v gnome-terminal &>/dev/null; then
  echo "Error: gnome-terminal not found. Use start_all_tmux.sh instead."
  exit 1
fi

echo "[start_all] Launching full AGV simulation stack (controller mode: ${MODE})..."
echo "[start_all] Default Gazebo scene: simplified_port_agv_terrain_400m"
echo "[start_all] Cleaning up stale local processes before launch..."
./stop_all.sh

echo "[start_all] Opening Gazebo terminal..."
gnome-terminal --title="AGV - Gazebo" -- bash -lc "cd ${SCRIPT_DIR_Q} && ./start_gazebo.sh; exec bash"

sleep 5

echo "[start_all] Opening Controller terminal..."
gnome-terminal --title="AGV - Controller (${MODE})" -- bash -lc "cd ${SCRIPT_DIR_Q} && ./start_controller.sh ${MODE_Q}; exec bash"

sleep 2

echo "[start_all] Opening Web Dashboard terminal..."
gnome-terminal --title="AGV - Web Dashboard" -- bash -lc "cd ${SCRIPT_DIR_Q} && ./start_web_dashboard.sh; exec bash"

echo "[start_all] All terminals launched. Dashboard will be at http://localhost:5000"
