#!/bin/bash
# One-click launch: opens 3 gnome-terminal windows for the full simulation stack.
# Usage:
#   ./start_all.sh              # controller in interactive mode
#   ./start_all.sh headless     # controller in headless mode
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-interactive}"

if ! command -v gnome-terminal &>/dev/null; then
  echo "[start_all] gnome-terminal not found. Falling back to tmux launcher..."
  exec "${SCRIPT_DIR}/start_all_tmux.sh" "${MODE}"
fi

if ! gnome-terminal --version >/dev/null 2>&1; then
  echo "[start_all] gnome-terminal is not usable in this environment."
  echo "[start_all] Falling back to tmux launcher..."
  exec "${SCRIPT_DIR}/start_all_tmux.sh" "${MODE}"
fi

echo "[start_all] Launching full AGV simulation stack (controller mode: ${MODE})..."

echo "[start_all] Opening Gazebo terminal..."
if ! env -u LD_LIBRARY_PATH gnome-terminal --title="AGV - Gazebo" -- bash -lc "${SCRIPT_DIR}/start_gazebo.sh; exec bash"; then
  echo "[start_all] Failed to open gnome-terminal. Falling back to tmux launcher..."
  exec "${SCRIPT_DIR}/start_all_tmux.sh" "${MODE}"
fi

sleep 5

echo "[start_all] Opening Controller terminal..."
env -u LD_LIBRARY_PATH gnome-terminal --title="AGV - Controller (${MODE})" -- bash -lc "${SCRIPT_DIR}/start_controller.sh ${MODE}; exec bash"

sleep 2

echo "[start_all] Opening Web Dashboard terminal..."
env -u LD_LIBRARY_PATH gnome-terminal --title="AGV - Web Dashboard" -- bash -lc "${SCRIPT_DIR}/start_web_dashboard.sh; exec bash"

echo "[start_all] All terminals launched. Dashboard will be at http://localhost:5000"
