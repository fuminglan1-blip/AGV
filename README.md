# 港口 AGV 数字孪生 — Port AGV Digital Twin

ROS 2 Humble + Gazebo Fortress + Flask + Leaflet 港口 AGV 实时数字孪生系统。

**当前主车: `agv_ackermann`** (Ackermann 转向港口卡车)

## 项目结构

```
AGV_sim/src/
├── web_dashboard/                  # Flask + Socket.IO 后端与前端
│   ├── app.py                      #   主服务 (ROS2 节点 + REST + WebSocket)
│   ├── risk_layer.py               #   合成风险网格
│   ├── risk_fusion.py              #   风险融合评估
│   ├── agv_mission_controller.py   #   航点跟踪任务控制器
│   ├── config.yaml                 #   服务器与 ROS2 话题配置
│   ├── config/demo_routes.yaml     #   预设演示路线
│   ├── templates/dashboard.html    #   中文统一驾驶舱
│   └── static/                     #   Leaflet, Socket.IO (离线)
│
├── agv_manual_controller.py        # 持久状态 Ackermann 手动控制器
├── agv_manual_config.yaml          # 控制器配置 (轴距、限幅、步长)
│
├── ros_gz_project_template/        # ROS2 + Gazebo 仿真包
├── harbour_assets_description/     # 港口 3D 模型资产包
│
├── docs/                           # 文档
│   ├── codex_plan.md               #   统一前端 MVP 实施计划
│   ├── architecture.md             #   系统架构
│   ├── api.md                      #   API 接口文档
│   └── demo.md                     #   演示说明
│
└── scripts/                        # 脚本
    ├── start_all.sh                #   主入口 (gnome-terminal 3窗口)
    ├── start_all_tmux.sh           #   备选 (tmux, 无桌面时)
    ├── dev_start.sh                #   开发调试入口
    ├── check.sh                    #   系统健康检查
    └── start_*.sh                  #   各组件独立启动脚本
```

## 快速启动

### 环境要求

- Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, Python 3.10+
- Python 包: flask, flask-cors, flask-socketio, pyyaml, numpy

### 一键启动 — 答辩演示 (推荐)

```bash
cd AGV_sim/src/scripts
./start_all.sh              # 打开 3 个 gnome-terminal 窗口
```

自动启动 Gazebo + 控制器 (交互模式) + Web 驾驶舱。

> 无桌面环境时使用 tmux 版: `./start_all_tmux.sh`
>
> 开发调试用: `./dev_start.sh web` (仅启动 Web 服务，无 Gazebo)

### 手动分步启动

```bash
# 1. 构建
cd AGV_sim/src
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# 2. 启动 Gazebo
ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py

# 3. 启动控制器 (新终端)
python3 agv_manual_controller.py

# 4. 启动 Web 服务 (新终端)
cd web_dashboard
python3 agv_mission_controller.py &
python3 app.py
```

### 打开驾驶舱

浏览器访问: **http://localhost:5000**

## 驾驶舱功能

- **港口平面孪生图** — AGV 实时位置、轨迹、风险热力图
- **AGV 实时状态** — 位置、航向、速度、当前模式
- **风险评估** — 风险等级、风险分数、风险原因、实时告警
- **任务状态** — 当前任务、进度、预设路线一键执行
- **最近告警** — 风险变化自动告警推送
- **系统状态** — 后端/ROS2/WebSocket 连接监控
- **车辆控制** — 键盘 W/S/A/D 或面板按钮
- **图层控制** — 轨迹/热力图/网格显示切换

## 统一 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/system/status` | GET | 系统状态 |
| `/api/agv/latest` | GET | AGV 最新状态 |
| `/api/agv/path` | GET | 历史轨迹 |
| `/api/risk/current` | GET | 当前风险评估 |
| `/api/risk/heatmap` | GET | 风险热力图 |
| `/api/alerts/recent` | GET | 最近告警 |
| `/api/mission/status` | GET | 任务状态 |
| `/api/demo/reset` | POST | 重置演示 |

旧版接口 (`/vehicle_state`, `/trajectory`, `/risk/*` 等) 保留兼容。

## 健康检查

```bash
./scripts/check.sh
```

## 文档

- [实施计划](docs/codex_plan.md) — 统一前端 MVP 计划
- [系统架构](docs/architecture.md) — 模块与数据流
- [API 文档](docs/api.md) — 接口详细说明
- [演示说明](docs/demo.md) — 操作指南
- [运行指南](docs/run_guide.md) — 分步启动
- [CLAUDE.md](CLAUDE.md) — AI 辅助开发指南
