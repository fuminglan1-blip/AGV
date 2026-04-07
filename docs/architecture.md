# 系统架构 — 港口 AGV 数字孪生

> Architecture — Port AGV Digital Twin

## 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│  浏览器 (驾驶舱 dashboard.html)                               │
│  ├── Leaflet 地图 (轨迹 / 热力图 / AGV 标记)                  │
│  ├── 右侧面板 (状态 / 风险 / 任务 / 告警 / 系统 / 仿真预留)    │
│  └── Socket.IO 客户端                                        │
└──────────────┬────────────────────────────────────────────────┘
               │ REST API + WebSocket (Socket.IO)
┌──────────────▼────────────────────────────────────────────────┐
│  Flask 后端 (web_dashboard/app.py)                            │
│  ├── 主线程: Flask-SocketIO (threading 模式)                   │
│  ├── 后台线程: rclpy.spin(AGVPoseSubscriber)                   │
│  ├── 共享状态: vehicle_state / trajectory / mission / alerts    │
│  ├── 风险管道: risk_layer.query() → risk_fusion.fuse()          │
│  ├── 旧版接口: /vehicle_state, /trajectory, /risk/*             │
│  └── 统一接口: /api/system/status, /api/agv/*, /api/risk/*, ... │
└──────┬───────────────────┬────────────────────────────────────┘
       │                   │
       │ /agv/control_cmd  │ /agv/mission_cmd
       │ /agv/mission_status
       ▼                   ▼
┌──────────────┐  ┌─────────────────────┐
│ 手动控制器    │  │ 任务控制器            │
│ agv_manual_  │  │ agv_mission_         │
│ controller   │  │ controller           │
│              │  │                      │
│ 唯一发布者:   │  │ /agv/odometry 订阅    │
│ /agv/cmd_vel │◄─│ /agv/control_cmd 发布 │
└──────┬───────┘  └──────────────────────┘
       │
       │ /agv/cmd_vel (geometry_msgs/Twist)
       ▼
┌─────────────────────────────────────────────────────────────┐
│  Gazebo Fortress 仿真                                       │
│  ├── 世界: harbour_diff_drive.sdf (港口场景)                  │
│  ├── 主车: agv_ackermann (Ackermann 转向, 3m 轴距)           │
│  ├── ros_gz_bridge (ros_gz_agv_ackermann_bridge.yaml)        │
│  └── 输出: /agv/odometry, /agv/joint_states, /tf             │
└─────────────────────────────────────────────────────────────┘
```

## 模块说明

### 1. Gazebo 仿真层 (`ros_gz_project_template/`)

- **harbour_diff_drive.sdf** — 港口场景 (起重机、集装箱、agv_ackermann)
- **agv_ackermann/model.sdf** — Ackermann 转向港口卡车 (10吨, 3m 轴距)
- **harbour_diff_drive.launch.py** — 启动 Gazebo + ros_gz_bridge + RViz
- **ros_gz_agv_ackermann_bridge.yaml** — Gazebo ↔ ROS2 话题桥接

### 2. 港口资产 (`harbour_assets_description/`)

自定义 ROS2 包，通过 `GZ_SIM_RESOURCE_PATH` 向 Gazebo 提供港口 3D 模型。

### 3. Flask 后端 (`web_dashboard/app.py`)

混合 ROS2 + Web 服务器:

- **主线程**: Flask-SocketIO 服务 (threading 模式, 非 eventlet)
- **后台线程**: `rclpy.spin()` 运行 AGVPoseSubscriber
- **数据流**: `/agv/odometry` → risk_layer → risk_fusion → Socket.IO 推送 + REST 接口
- **控制桥接**: 代浏览器发布到 `/agv/control_cmd` 和 `/agv/mission_cmd`
- **告警系统**: 风险状态变化时自动生成告警推送
- **系统广播**: 每 3 秒广播 system_status

### 4. 风险管道 (`risk_layer.py`, `risk_fusion.py`)

开发期合成风险评估:

- `risk_layer.py` — 200×200 静态风险网格 (起重机区、集装箱区、港口边缘热点)
- `risk_fusion.py` — 地面风险 + 梯度幅值 → `risk_score` (0-1) + `risk_state` (safe/warn/danger)
- 阈值可通过 `config.yaml` 的 `risk_thresholds` 配置

### 5. 手动控制器 (`agv_manual_controller.py`)

持久状态 Ackermann 控制器，`/agv/cmd_vel` 的**唯一发布者**。

- 接受键盘 (终端) 或 `/agv/control_cmd` 话题 (远程) 命令
- 速率限制输出: max_accel, max_steer_rate
- Ackermann 转换: `angular.z = speed × tan(steer) / wheel_base`

### 6. 任务控制器 (`agv_mission_controller.py`)

航点跟踪自动驾驶 (演示路线):

- 订阅 `/agv/odometry` 获取车辆位姿
- 通过 `/agv/mission_cmd` 接收任务命令
- 发布高级命令到 `/agv/control_cmd`
- 发布状态到 `/agv/mission_status`

### 7. 前端 (`dashboard.html`)

统一中文驾驶舱:

- Leaflet + CRS.Simple 地图 (米坐标)
- 实时 AGV 标记 + 轨迹 + 风险热力图
- 右侧信息面板: 状态/风险/任务/告警/系统/仿真预留
- 车辆控制面板 + 图层开关
- 底部日志面板
- 全中文文案

## ROS2 话题映射

| 话题 | 类型 | 方向 |
|------|------|------|
| `/agv/cmd_vel` | Twist | 手动控制器 → Gazebo |
| `/agv/odometry` | Odometry | Gazebo → app.py, 任务控制器 |
| `/agv/control_cmd` | String | app.py, 任务控制器 → 手动控制器 |
| `/agv/mission_cmd` | String | app.py → 任务控制器 |
| `/agv/mission_status` | String | 任务控制器 → app.py |
| `/agv/joint_states` | JointState | Gazebo → ROS2 |
| `/tf` | TFMessage | Gazebo → ROS2 |

## 线程模型

```
app.py 进程:
  主线程:     Flask-SocketIO 服务 (端口 5000)
  后台线程1:  rclpy.spin(AGVPoseSubscriber)
  后台线程2:  system_status 广播 (每3秒)
  共享状态:   vehicle_state{}, trajectory_history, mission_state{}, alert_history
  锁:        state_lock (threading.Lock)

agv_manual_controller 进程:
  主线程:     键盘循环 (或 headless 模式下 rclpy.spin)
  定时回调:   _publish() 20 Hz → /agv/cmd_vel

agv_mission_controller 进程:
  主线程:     rclpy.spin()
  定时回调:   _control_loop() 10 Hz, _publish_status() 2 Hz
```

## WebSocket 事件

| 事件名 | 方向 | 频率 | 说明 |
|--------|------|------|------|
| `agv_state` | 服务器 → 浏览器 | ~50 Hz | AGV 统一状态 |
| `risk_state` | 服务器 → 浏览器 | ~50 Hz | 风险评估结果 |
| `alert_event` | 服务器 → 浏览器 | 事件驱动 | 告警推送 |
| `system_status` | 服务器 → 浏览器 | 每3秒 | 系统状态广播 |
| `mission_status` | 服务器 → 浏览器 | 事件驱动 | 任务状态更新 |
| `vehicle_pose` | 服务器 → 浏览器 | ~50 Hz | 旧版位姿推送 (兼容) |
