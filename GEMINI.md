# GEMINI.md

This file provides foundational mandates and instructional context for the **Port AGV Digital Twin** project.

## Project Overview

The **Port AGV Digital Twin** is a real-time simulation and visualization system for Automated Guided Vehicles (AGVs) in a port environment. It integrates **ROS 2** (Humble/Jazzy) for robotic middleware, **Gazebo Fortress** for 3D physics simulation, and a **Flask-based web dashboard** for monitoring and control.

### Main Technologies
- **Robotics:** ROS 2 (Humble or Jazzy), Gazebo Fortress.
- **Backend:** Python 3.10+, Flask, Flask-SocketIO (Threading mode, **NOT eventlet**), NumPy, PyYAML.
- **Frontend:** Leaflet (Maps), Socket.IO (Real-time updates), Bootstrap/Vanilla CSS (UI).
- **Communication:** ROS 2 Topics (Odometry, Cmd Vel, Laser Scan), WebSocket (Real-time telemetry), REST API.

### Key Architecture
- **Primary Vehicle:** `agv_ackermann` (Ackermann-steered port truck, 3m wheelbase).
- **Default Scene:** `simplified_port_agv_terrain_400m` (400m port scene with terrain/deformation verification).
- **Control Chain:** Browser → Flask (POST) → `agv_manual_controller.py` (Sole `/agv/cmd_vel` publisher) → Gazebo.
- **Data Flow:** Gazebo → ROS 2 Bridge → `app.py` (Flask) → Socket.IO → Browser (Leaflet).

---

## Building and Running

### Prerequisites
- Ubuntu 22.04 + ROS 2 Humble OR Ubuntu 24.04 + ROS 2 Jazzy.
- Gazebo Fortress installed.
- Python dependencies: `flask`, `flask-cors`, `flask-socketio`, `pyyaml`, `numpy`.

### Key Commands

#### 1. Environment Setup & Build
```bash
# Source ROS 2 and workspace (using helper script)
source scripts/common_env.sh

# Build from the src directory
colcon build --symlink-install

# Refresh environment after build
source scripts/common_env.sh
```

#### 2. One-Click Launch (Recommended)
```bash
cd scripts
./start_all.sh        # Opens 3 gnome-terminal windows (Gazebo, Controller, Web)
./start_all_tmux.sh   # Alternative for headless/remote sessions via tmux
```

#### 3. Manual Step-by-Step Launch
- **Terminal 1 (Gazebo):** `ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py`
- **Terminal 2 (Controller):** `python3 agv_manual_controller.py`
- **Terminal 3 (Web Dashboard):** `cd web_dashboard && python3 app.py`

#### 4. Verification & Health Check
```bash
./scripts/check.sh             # Comprehensive system health check
ros2 topic hz /agv/odometry    # Verify telemetry rate
curl http://localhost:5000/api/system/status  # Check backend status
```

---

## Development Conventions

### 1. Architectural Mandates
- **Phase 1 Scope:** Focus on stability and minimal viable integration. Do NOT add InSAR, GNSS, or multi-vehicle features unless explicitly requested (reserved for Phase 2+).
- **Offline Operation:** All static assets (JS/CSS) MUST be kept in `web_dashboard/static/`. No CDN or external network dependencies are allowed.
- **Threading Model:** Use **Threading mode** for Flask-SocketIO. Do NOT use `eventlet` or `gevent`. The `eventlet` import is explicitly blocked in `app.py`.
- **Sole Publisher:** `agv_manual_controller.py` is the **only** node authorized to publish to `/agv/cmd_vel`.

### 2. Coding Standards
- **ROS 2:** Follow standard package structures. Use `package://` URIs for resources.
- **Python:** Use `state_lock` (threading.Lock) for all shared state in the Flask app.
- **Configuration:** Always prefer YAML/config files (e.g., `web_dashboard/config.yaml`) over hardcoded values.
- **Relative Paths:** Never use absolute paths like `/home/user/...`. Use paths relative to the project root or ROS 2 package paths.

### 3. UI & Localization
- **Dashboard:** The user interface is in **Chinese** (UTF-8) for thesis defense requirements. Maintain consistent terminology (e.g., "极简实验港口场景", "风险评估").

### 4. Important Files
- `CLAUDE.md`: AI-specific development guidelines and technical constraints.
- `AGENTS.md`: Detailed engineering standards and phase boundaries.
- `web_dashboard/app.py`: Main integration point for ROS 2 and Web.
- `scripts/common_env.sh`: Centralized environment management.

---

## Directory Overview

- `web_dashboard/`: Flask/Socket.IO backend and Leaflet frontend.
- `ros_gz_project_template/`: Core ROS 2 + Gazebo integration packages.
- `harbour_assets_description/`: 3D models and SDF assets for the harbor.
- `scripts/`: Automation scripts for lifecycle management (start/stop/check).
- `docs/`: Architectural maps, API specs, and implementation plans.
- `insar_data/`: Placeholder/Initial data for future InSAR integration.
