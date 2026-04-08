# Run Guide — Port AGV Digital Twin

## Prerequisites

- Ubuntu 22.04
- ROS 2 Humble (`/opt/ros/humble/`) or ROS 2 Jazzy (`/opt/ros/jazzy/`)
- Gazebo Fortress (Ignition Gazebo)
- Python 3.10+ with: flask, flask-cors, flask-socketio, pyyaml

## Build

```bash
cd ~/AGV_sim/src
source scripts/common_env.sh
colcon build --symlink-install
source scripts/common_env.sh
```

Expected: `Summary: 5 packages finished`.
Note: each machine must build its own local `install/` overlay before launch.

## Launch (3 Terminals)

### Terminal 1 — Gazebo Simulation

```bash
source scripts/common_env.sh
ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py
```

Wait for Gazebo GUI to open. You should see the 400m simplified experiment scene with the crane, containers, and the `agv_ackermann` vehicle spawned near `(20, 12)`.

To save resources (no RViz):
```bash
source scripts/common_env.sh
ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py rviz:=false
```

Legacy compatibility entry remains available:
```bash
source scripts/common_env.sh
ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py
```

### Terminal 2 — Manual Controller

```bash
cd ~/AGV_sim/src
source scripts/common_env.sh
python3 agv_manual_controller.py
```

This starts the Ackermann controller with keyboard input. You can also run headless for remote-only control:
```bash
python3 agv_manual_controller.py < /dev/null
```

### Terminal 3 — Web Dashboard + Mission Controller

```bash
cd ~/AGV_sim/src/web_dashboard
source ../scripts/common_env.sh
python3 agv_mission_controller.py &
python3 app.py
```

Or use the startup script (starts app.py only — add mission controller separately):
```bash
python3 agv_mission_controller.py &
./start_server.sh
```

### Browser

Open: **http://localhost:5000**

## Controls

### From Dashboard (browser)
- **Direction pad**: Forward / Reverse / Left / Right / Center / Stop
- **Keyboard**: W/S/A/D/SPACE/R/Q (when browser is focused)
- **Demo Routes**: Click a route button to auto-execute
- **Cancel Mission**: Stop the running demo route
- **ESC**: Emergency stop

### From Terminal (agv_manual_controller)
- `w/s`: Speed up / down
- `a/d`: Steer left / right (angle holds)
- `SPACE`: Emergency stop
- `r`: Center steering
- `q`: Full reset
- `ESC`: Quit

## Verification

```bash
# Check topics
ros2 topic list | grep agv
ros2 topic hz /agv/odometry          # should be ~50 Hz
ros2 topic hz /agv/cmd_vel           # should be ~20 Hz

# Check web APIs
curl http://localhost:5000/vehicle_state
curl http://localhost:5000/mission/status
curl http://localhost:5000/mission/routes

# Test manual control from CLI
curl -X POST -H 'Content-Type: application/json' \
  -d '{"action":"speed_up"}' http://localhost:5000/control/manual
```

## Stopping

- Terminal 1: `Ctrl+C` (stops Gazebo)
- Terminal 2: `ESC` or `Ctrl+C` (stops manual controller)
- Terminal 3: `Ctrl+C` (stops Flask); `pkill -f agv_mission_controller` (stops mission)
