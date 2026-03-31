# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Port AGV Digital Twin** — ROS2 Humble + Gazebo Fortress simulation with a Flask web dashboard for real-time visualization. Currently in **Phase 1: Minimal Viable Integration**.

Three main components:
1. **ROS2 + Gazebo Simulation** (`ros_gz_project_template/`) — Differential drive AGV in a port harbour scene. **Read-only; do not modify.**
2. **Harbour Assets** (`harbour_assets_description/`) — Custom ROS2 package providing port 3D models (crane, containers) to Gazebo via `GZ_SIM_RESOURCE_PATH`.
3. **Web Dashboard** (`web_dashboard/`) — Flask + Socket.IO + ROS2 node hybrid. This is the **active backend** (the `backend/` directory is deprecated).

## Architecture

```
Gazebo (harbour_diff_drive.sdf world)
    ↓ ros_gz_bridge (config: ros_gz_example_bringup/config/ros_gz_example_bridge.yaml)
ROS2 Topics: /agv/odometry (primary), /diff_drive/odometry (fallback)
    ↓ rclpy subscription (AGVPoseSubscriber node)
web_dashboard/app.py (Flask-SocketIO, threading mode)
    ├── risk_layer.py    → static 200x200 risk grid with port hotspots
    └── risk_fusion.py   → combines terrain risk + gradient → risk_score + risk_state
    ↓ Socket.IO emit (vehicle_pose event)
Browser Dashboard (templates/dashboard.html)
```

**Threading model**: Main thread runs Flask-SocketIO (threading mode, NOT eventlet). Background thread runs `rclpy.spin()`. Shared state (`vehicle_state`, `trajectory_history`) is protected by `state_lock`.

**Critical**: The backend MUST be run with ROS2 environment sourced. It starts without ROS2 but won't receive data.

## Development Commands

### Build (from workspace root `AGV_sim/src/`)

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Expected output: `Summary: 5 packages finished`

### Launch Simulation

```bash
# Harbour scene with AGV (main launch file)
ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py

# Without RViz (saves resources)
ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py rviz:=false
```

### Run Web Dashboard

```bash
cd web_dashboard
./start_server.sh
# Dashboard at http://localhost:5000
```

### Control AGV

```bash
ros2 topic pub --once /diff_drive/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 1.0}, angular: {z: 0.5}}"
```

### Verify / Debug

```bash
# Integration check
./verify_integration.sh

# ROS2 topics
ros2 topic list | grep diff_drive
ros2 topic hz /diff_drive/odometry
ros2 topic echo /diff_drive/odometry --once

# REST API
curl http://localhost:5000/vehicle_state
curl http://localhost:5000/trajectory
curl http://localhost:5000/risk/heatmap
```

## Important Constraints

- **`ros_gz_project_template/` is read-only.** All integration work goes in `web_dashboard/` or new packages.
- **Offline operation required.** All JS/CSS libraries live in `web_dashboard/static/`. No CDN or external network dependencies. New frontend deps must be downloaded to `static/`.
- **Threading mode only.** Do NOT use eventlet. Socket.IO emits from ROS2 callbacks use `socketio.emit(..., namespace='/')`.
- **Phase 1 scope only.** Do not add InSAR, GNSS, dynamic terrain, multi-vehicle, or complex vehicle models — those are Phase 2+.
- See `AGENTS.md` for the full constraint list and development workflow rules.

## ROS2 Topics

| Topic | Type | Direction |
|-------|------|-----------|
| `/diff_drive/odometry` | nav_msgs/msg/Odometry | Gazebo → ROS2 |
| `/diff_drive/cmd_vel` | geometry_msgs/msg/Twist | ROS2 → Gazebo |
| `/diff_drive/scan` | sensor_msgs/msg/LaserScan | Gazebo → ROS2 |
| `/joint_states` | sensor_msgs/msg/JointState | Gazebo → ROS2 |
| `/tf` | tf2_msgs/msg/TFMessage | Gazebo → ROS2 |
| `/clock` | rosgraph_msgs/msg/Clock | Gazebo → ROS2 |

Frames: `diff_drive/odom` (odometry), `diff_drive` (base), `diff_drive/lidar_link` (LIDAR).

## Web API

- `GET /` — Dashboard page
- `GET /vehicle_state` — Current pose, speed, risk_index
- `GET /trajectory` — Up to 500 historical points
- `GET /risk/heatmap` — Risk grid data
- **Socket.IO** `vehicle_pose` event: `{x, y, heading (deg), risk (0-1)}`

## Configuration

- `web_dashboard/config.yaml` — Server port, ROS2 topic selection, map center, heatmap grid size
- `backend/config/vehicle_source.yaml` — Vehicle type switch (agv_ackermann vs diff_drive)
- `ros_gz_example_bringup/config/ros_gz_example_bridge.yaml` — Gazebo↔ROS2 topic mappings

## Environment

- Ubuntu 22.04, ROS2 Humble, Gazebo Fortress, Python 3.10+
- Python packages: flask, flask-cors, flask-socketio, rclpy, nav_msgs
