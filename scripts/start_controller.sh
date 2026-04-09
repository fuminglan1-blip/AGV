#!/bin/bash
# Start AGV manual controller
# Usage:
#   ./start_controller.sh              # interactive mode (keyboard control)
#   ./start_controller.sh headless     # headless mode (remote control only)
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-interactive}"

source "${SCRIPT_DIR}/common_env.sh"

cd "${SRC_DIR}"

# Make sure only one `/agv/cmd_vel` publisher remains active.
agv_stop_processes "start_controller" \
  'python3 agv_manual_controller.py'

case "${MODE}" in
  interactive)
    echo "[start_controller] Starting in interactive mode (keyboard control)..."
    exec python3 agv_manual_controller.py
    ;;
  headless)
    echo "[start_controller] Starting in headless mode (remote control only)..."
    exec python3 agv_manual_controller.py < /dev/null
    ;;
  *)
    echo "Error: unknown mode '${MODE}'. Use 'interactive' or 'headless'."
    exit 1
    ;;
esac
