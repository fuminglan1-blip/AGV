# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Port AGV Digital Twin** — ROS2 Humble + Gazebo Fortress + Flask web dashboard for real-time harbour AGV simulation and visualization. Currently in **Phase 1: Minimal Viable Integration**.

Primary vehicle: `agv_ackermann` (Ackermann-steered port truck, 3m wheelbase, 10t). diff_drive is archived.

## Architecture

```
Gazebo Fortress (harbour_diff_drive.sdf)
    ↓ ros_gz_bridge (ros_gz_agv_ackermann_bridge.yaml)
/agv/odometry, /agv/cmd_vel, /agv/joint_states, /agv/scan
    ↓
agv_manual_controller.py        ← sole /agv/cmd_vel publisher
    ↑ /agv/control_cmd (String commands from Flask or mission controller)
    ↑ set_speed:<val>, set_steer:<val> (from agv_mission_controller)
    ↓
web_dashboard/app.py (Flask-SocketIO + ROS2 node hybrid)
    ├── risk_layer.py    → 200×200 synthetic risk grid (-100..+100m)
    ├── risk_fusion.py   → rule-based: terrain×0.7 + gradient×0.3 → score/state
    ├── alert_history    → deque(maxlen=100), risk transitions trigger alerts
    ├── Socket.IO emit   → agv_state, risk_state, alert_event, system_status
    └── REST API         → /api/* unified + legacy /vehicle_state etc.
    ↓
Browser (templates/dashboard.html — Leaflet + Socket.IO, fully offline)
```

**Threading model**: Main thread = Flask-SocketIO (threading mode, **NOT eventlet**). Background thread = `rclpy.spin()`. Third thread = system_status broadcaster (3s interval). All shared state protected by `state_lock` (threading.Lock). The eventlet import is explicitly blocked at the top of app.py to prevent engineio auto-detection.

**Control chain**: Browser → POST /control/manual → app.py publishes String to /agv/control_cmd → agv_manual_controller receives, updates persistent target_speed/target_steer → timer at 20Hz applies rate-limiting → publishes Twist to /agv/cmd_vel → Gazebo AckermannSteering plugin.

**Mission chain**: Browser → POST /mission/start → app.py publishes "start:route_name" to /agv/mission_cmd → agv_mission_controller loads waypoints, runs 10Hz control loop publishing set_speed/set_steer to /agv/control_cmd → status published as JSON on /agv/mission_status → app.py receives and emits to browser.

## Build and Launch

```bash
# Build (from AGV_sim/src/)
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# One-click launch (recommended for demo — opens 3 gnome-terminal windows)
cd scripts && ./start_all.sh

# Or tmux version (headless)
cd scripts && ./start_all_tmux.sh

# Or manual step-by-step:
# Terminal 1: Gazebo
ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py
# Terminal 2: Controller (interactive keyboard)
python3 agv_manual_controller.py
# Terminal 3: Mission + Flask
cd web_dashboard && python3 agv_mission_controller.py & python3 app.py

# Web-only mode (no Gazebo, for frontend dev)
cd scripts && ./dev_start.sh web
```

Dashboard: http://localhost:5000 — switch map provider with `?provider=osm` or `?provider=carto`.

## Verify

```bash
# Health check script (tests all endpoints)
./scripts/check.sh

# Manual checks
ros2 topic list | grep agv
ros2 topic hz /agv/odometry
curl http://localhost:5000/health
curl http://localhost:5000/api/system/status
curl http://localhost:5000/api/agv/latest
curl http://localhost:5000/api/risk/current
```

## ROS2 Topics

| Topic | Type | Direction |
|-------|------|-----------|
| `/agv/cmd_vel` | geometry_msgs/Twist | controller → Gazebo |
| `/agv/odometry` | nav_msgs/Odometry | Gazebo → app.py, mission_controller |
| `/agv/control_cmd` | std_msgs/String | app.py, mission_controller → manual_controller |
| `/agv/mission_cmd` | std_msgs/String | app.py → mission_controller |
| `/agv/mission_status` | std_msgs/String (JSON) | mission_controller → app.py |
| `/agv/joint_states` | sensor_msgs/JointState | Gazebo → ROS2 |
| `/agv/scan` | sensor_msgs/LaserScan | Gazebo → ROS2 |
| `/tf` | tf2_msgs/TFMessage | Gazebo + robot_state_publisher |

## Web API

Legacy endpoints preserved for backward compatibility. Unified `/api/*` endpoints added:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/system/status` | GET | Backend/ROS2/WebSocket status, uptime |
| `/api/agv/latest` | GET | Position, orientation, speed, mode |
| `/api/agv/path` | GET | Trajectory history (max 500 pts) |
| `/api/risk/current` | GET | Risk level/score/reasons |
| `/api/risk/heatmap` | GET | Full risk grid |
| `/api/alerts/recent` | GET | Alert history (newest first) |
| `/api/mission/status` | GET | Mission mode/route/progress |
| `/api/demo/reset` | POST | Clear trajectory + alerts + cancel mission |
| `/vehicle_state` | GET | Legacy: pose + speed + risk |
| `/control/manual` | POST | `{"action":"speed_up"}` — 7 actions |
| `/control/stop` | POST | Emergency stop + cancel mission |
| `/mission/start` | POST | `{"route_name":"standard_operation"}` |
| `/mission/cancel` | POST | Cancel running mission |
| `/mission/routes` | GET | Available demo routes |

WebSocket events (server → client): `agv_state` (~50Hz), `risk_state` (~50Hz), `alert_event` (on risk transition), `system_status` (3s), `mission_status` (on change), `vehicle_pose` (legacy compat).

## Configuration

| File | Purpose |
|------|---------|
| `web_dashboard/config.yaml` | Flask port, ROS2 topic, map provider (simple/osm/carto), risk thresholds |
| `web_dashboard/config/demo_routes.yaml` | 3 demo routes with waypoint tracking params |
| `agv_manual_config.yaml` | Vehicle geometry (wheel_base: 3.0m), limits, control rates |
| `ros_gz_example_bringup/config/ros_gz_agv_ackermann_bridge.yaml` | Gazebo↔ROS2 topic bridge |

## Important Constraints

- **Offline operation required.** All JS/CSS in `web_dashboard/static/`. No CDN.
- **Threading mode only.** Do NOT use eventlet — app.py blocks its import explicitly.
- **Phase 1 scope only.** No InSAR, GNSS, dynamic terrain, multi-vehicle, Nav2/SLAM.
- **agv_manual_controller.py is the sole /agv/cmd_vel publisher.** Never publish cmd_vel from elsewhere.
- **Do not modify ros_gz_project_template/** — treat as read-only base.
- **Do not break the existing demo chain:** Gazebo → controller → Flask → browser.
- **Chinese UI.** Dashboard text is all Chinese for thesis defense presentation.
- See `AGENTS.md` for the full constraint and code style list.

## Environment

- Ubuntu 22.04, ROS2 Humble, Gazebo Fortress, Python 3.10+
- Python packages: flask, flask-cors, flask-socketio, pyyaml, rclpy, nav_msgs, numpy
