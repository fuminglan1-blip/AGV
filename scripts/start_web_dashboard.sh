#!/bin/bash
# Start Flask web dashboard + mission controller
# Launches agv_mission_controller.py in background, then app.py in foreground.
# On exit, cleans up the background process.
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WEB_DIR="${SRC_DIR}/web_dashboard"
MISSION_PID=""
SERVER_HOST=""
SERVER_PORT=""
CLEANUP_DONE=0

read_server_config() {
  local cfg_path="${WEB_DIR}/config.yaml"
  if [[ ! -f "${cfg_path}" ]]; then
    echo "[start_web_dashboard] Error: missing config file: ${cfg_path}" >&2
    exit 1
  fi

  local cfg
  cfg="$(python3 - "${cfg_path}" <<'PY'
import sys
import yaml

cfg_path = sys.argv[1]
with open(cfg_path, 'r') as f:
    cfg = yaml.safe_load(f) or {}
server = cfg.get('server', {})
host = str(server.get('host', '127.0.0.1'))
port = int(server.get('port', 5000))
print(f"{host}\t{port}")
PY
)"

  SERVER_HOST="${cfg%%$'\t'*}"
  SERVER_PORT="${cfg##*$'\t'}"
}

check_server_port() {
  if python3 - "${SERVER_HOST}" "${SERVER_PORT}" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
bind_host = '0.0.0.0' if host in ('', '*') else host
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind((bind_host, port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
  then
    return 0
  fi

  echo "[start_web_dashboard] Error: configured Flask endpoint ${SERVER_HOST}:${SERVER_PORT} is already in use." >&2
  echo "[start_web_dashboard] Fix the port conflict, then restart the dashboard." >&2
  echo "[start_web_dashboard] Suggested checks:" >&2
  echo "  ss -ltnp \"( sport = :${SERVER_PORT} )\"" >&2
  echo "  lsof -i :${SERVER_PORT}" >&2
  ss -ltnp "( sport = :${SERVER_PORT} )" 2>/dev/null || true
  return 1
}

cleanup() {
  if [[ "${CLEANUP_DONE}" -eq 1 ]]; then
    return
  fi
  CLEANUP_DONE=1
  echo ""
  echo "[start_web_dashboard] Shutting down..."
  if [[ -n "${MISSION_PID}" ]] && kill -0 "${MISSION_PID}" 2>/dev/null; then
    echo "[start_web_dashboard] Stopping agv_mission_controller (PID ${MISSION_PID})..."
    kill -INT "${MISSION_PID}" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      if ! kill -0 "${MISSION_PID}" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    if kill -0 "${MISSION_PID}" 2>/dev/null; then
      kill "${MISSION_PID}" 2>/dev/null || true
    fi
    wait "${MISSION_PID}" 2>/dev/null || true
  fi
  echo "[start_web_dashboard] Cleanup done."
}

trap cleanup EXIT INT TERM

source "${SCRIPT_DIR}/common_env.sh"

read_server_config
echo "[start_web_dashboard] Using Flask endpoint ${SERVER_HOST}:${SERVER_PORT}"
check_server_port

cd "${WEB_DIR}"

echo "[start_web_dashboard] Starting agv_mission_controller.py in background..."
python3 agv_mission_controller.py &
MISSION_PID=$!

echo "[start_web_dashboard] Starting Flask app (app.py)..."
python3 app.py
