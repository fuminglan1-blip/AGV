# Quick Start Guide - AGV Digital Twin Harbour Integration

## Prerequisites Check

```bash
# Verify ROS 2 is installed
ros2 --version

# Verify Gazebo Fortress is installed
ign gazebo --version

# Verify Python 3.10+
python3 --version
```

## One-Time Setup

### 1. Build the Workspace

```bash
cd /path/to/AGV_sim/src

# Source ROS2
source scripts/common_env.sh

# Build all packages
colcon build --symlink-install

# Re-source so the freshly built workspace overlay is loaded
source scripts/common_env.sh

# Note: every machine must build its own local install/ overlay
```

**Expected output**: `Summary: 5 packages finished`

### 2. Verify Installation

```bash
./scripts/verify_integration.sh
```

All checks should show ✓ (green checkmarks).

## Running the System

### Terminal 1: Launch Gazebo Simulation

```bash
cd /path/to/AGV_sim/src

# Source environment
source scripts/common_env.sh

# Launch the default 400 m experiment scene with AGV
ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py
```

**What you should see**:
- Gazebo window opens
- 400m simplified experiment scene with crane and containers
- `agv_ackermann` vehicle in the harbour scene
- No error messages in terminal

**Optional**: Disable RViz to save resources:
```bash
ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py rviz:=false
```

### Terminal 2: Start Web Dashboard

```bash
cd /path/to/AGV_sim/src/web_dashboard

# Start Flask backend
./start_server.sh
```

**What you should see**:
```
✓ ROS2 node initialized and subscribed to /agv/odometry
* Running on http://127.0.0.1:5000
```

### Browser: Open Dashboard

Open your web browser and navigate to:
```
http://localhost:5000
```

**What you should see**:
- Map with AGV marker
- Sidebar showing vehicle pose (X, Y, heading)
- Connection status: "✓ Connected"
- Real-time position updates as AGV moves

## Controlling the AGV

### Terminal 3: Send Velocity Commands

```bash
cd /path/to/AGV_sim/src

# Source environment
source scripts/common_env.sh

# Move forward
ros2 topic pub --once /agv/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 1.0}, angular: {z: 0.0}}"

# Turn left while moving
ros2 topic pub --once /agv/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 1.0}, angular: {z: 0.5}}"

# Stop
ros2 topic pub --once /agv/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

**What you should see**:
- AGV moves in Gazebo
- Position updates in web dashboard
- Blue trajectory line grows

## Troubleshooting

### Problem: "colcon build" fails

**Solution**:
```bash
# Clean build artifacts
rm -rf build/ install/ log/

# Rebuild
colcon build --symlink-install
```

### Problem: Gazebo doesn't show harbour models

**Solution**:
```bash
# Check if package is installed
ros2 pkg list | grep harbour_assets_description

# If not found, rebuild
colcon build --packages-select harbour_assets_description
source install/setup.bash
```

### Problem: Web dashboard shows "Connecting..."

**Solution**:
1. Check if Flask is running: `ps aux | grep "python3 app.py"`
2. Check if ROS2 environment is sourced in Flask terminal
3. Restart Flask: `cd web_dashboard && ./start_server.sh`

### Problem: No real-time updates in dashboard

**Solution**:
1. Check if Gazebo is publishing: `ros2 topic hz /agv/odometry`
2. Check Flask logs for "Emitting pose data" messages
3. Check browser console (F12) for Socket.IO errors

### Problem: "Permission denied" when running scripts

**Solution**:
```bash
chmod +x web_dashboard/start_server.sh
chmod +x scripts/verify_integration.sh
```

## Testing the System

### 1. Verify ROS2 Topics

```bash
# List all AGV topics
ros2 topic list | grep /agv

# Expected output:
#   /agv/cmd_vel
#   /agv/odometry
#   /agv/scan

# Check odometry frequency
ros2 topic hz /agv/odometry

# Expected: ~50 Hz
```

### 2. Test Web API

```bash
# Get vehicle state
curl http://localhost:5000/vehicle_state

# Get trajectory
curl http://localhost:5000/trajectory

# Get heatmap
curl http://localhost:5000/risk/heatmap
```

### 3. Test Socket.IO Connection

Open browser console (F12) and check for:
```
Initializing AGV Dashboard...
Socket.IO connected
```

## Stopping the System

### Stop Gazebo (Terminal 1)
Press `Ctrl+C`

### Stop Flask (Terminal 2)
Press `Ctrl+C`

### Or Kill All Processes
```bash
pkill -f "gz sim"
pkill -f "python3 app.py"
```

## Directory Structure

```
AGV_sim/src/
├── ros_gz_project_template/     # ROS2 + Gazebo simulation
│   ├── ros_gz_example_bringup/
│   │   └── launch/
│   │       ├── simplified_port_agv_terrain_400m.launch.py  ← Default agv_ackermann main-scene launch
│   │       └── harbour_diff_drive.launch.py                ← Legacy compatibility launch
│   └── ros_gz_example_gazebo/
│       └── worlds/
│           ├── simplified_port_agv_terrain_400m.sdf        ← Default 400m main scene
│           └── harbour_diff_drive.sdf                      ← Legacy compatibility world
├── harbour_assets_description/  # Port harbour models
│   └── models/
│       ├── crane1/
│       ├── container40/
│       └── container-multi-stack/
├── web_dashboard/               # Flask + Socket.IO dashboard
│   ├── app.py
│   ├── config.yaml             ← New config file
│   ├── start_server.sh         ← Updated script
│   ├── templates/
│   └── static/
├── docs/                        # Documentation
│   ├── integration_plan.md
│   └── DELIVERY_REPORT.md
├── README.md                    # Project overview
├── AGENTS.md                    # Development rules
├── CLAUDE.md                    # AI assistant guidance
└── scripts/verify_integration.sh # Verification script
```

## Next Steps

After successfully running the system:

1. **Explore the Scene**: Use Gazebo's camera controls to view harbour models
2. **Test Navigation**: Send various velocity commands to move the AGV
3. **Monitor Dashboard**: Watch real-time updates in the web interface
4. **Read Documentation**: Check `docs/integration_plan.md` for Phase 2 features

## Support

- **Issues**: Check `docs/DELIVERY_REPORT.md` for known issues
- **Development**: See `AGENTS.md` for development guidelines
- **Architecture**: See `CLAUDE.md` for system architecture

---

**Quick Reference Commands**:
```bash
# Build
colcon build --symlink-install && source install/setup.bash

# Launch
ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py

# Web
cd web_dashboard && ./start_server.sh

# Control
ros2 topic pub --once /agv/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}, angular: {z: 0.5}}"

# Verify
./scripts/verify_integration.sh
```
