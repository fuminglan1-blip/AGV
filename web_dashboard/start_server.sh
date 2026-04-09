#!/bin/bash
# AGV Digital Twin Web Dashboard Startup Script
# This script starts the Flask backend server with ROS2 integration

# Get the directory where this script is located (web_dashboard/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SRC_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Kill any existing Flask processes
pkill -f "python3 app.py" 2>/dev/null
sleep 1

# Source ROS2 + workspace via the shared compatibility bootstrap
source "$SRC_DIR/scripts/common_env.sh"

# Change to script directory and start Flask backend
cd "$SCRIPT_DIR"
python3 app.py
