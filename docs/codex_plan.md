# 统一前端 MVP 实施计划 (codex_plan.md)

> 编写日期: 2026-04-01
> 阶段: 第一阶段 — 统一前端 MVP

## 目标

将港口 AGV 数字孪生项目的关键展示信息统一收口到一个中文网页驾驶舱，
可用于答辩演示，不推翻现有可运行链路。

## 当前状态审计

### 已有可运行链路
- Gazebo Fortress 仿真 → agv_ackermann 主车
- agv_manual_controller.py → 唯一 /agv/cmd_vel 发布者
- agv_mission_controller.py → 预设路线自动执行
- web_dashboard/app.py → Flask + Socket.IO + ROS2 节点
- web_dashboard/templates/dashboard.html → Leaflet 地图 + 侧边栏
- risk_layer.py → 200×200 合成风险网格
- risk_fusion.py → 规则式风险融合

### 已有 REST 接口 (14个)
| 接口 | 方法 | 状态 |
|------|------|------|
| / | GET | 已有 |
| /health | GET | 已有 |
| /vehicle_state | GET | 已有 |
| /trajectory | GET | 已有 |
| /trajectory/clear | POST | 已有 |
| /risk/current | GET | 已有 |
| /risk/heatmap | GET | 已有 |
| /risk/heatmap/refresh | GET | 已有 |
| /control/manual | POST | 已有 |
| /control/stop | POST | 已有 |
| /mission/start | POST | 已有 |
| /mission/cancel | POST | 已有 |
| /mission/status | GET | 已有 |
| /mission/routes | GET | 已有 |

### 已有 WebSocket 事件 (1个)
- `vehicle_pose` — 实时位姿推送

### 缺失项
- 统一 /api/* 命名空间
- 系统状态接口 /api/system/status
- 告警事件接口 /api/alerts/recent
- 重置接口 /api/demo/reset
- WebSocket: agv_state, risk_state, alert_event, system_status, mission_status, log_event
- 前端中文化
- 前端告警面板、系统状态面板、仿真预留区
- 开发脚本 dev_start.sh, check.sh

## 实施步骤

### 步骤 1: 后端增强 (app.py)
- 添加 /api/system/status 接口
- 添加 /api/agv/latest 接口
- 添加 /api/agv/path 接口
- 添加 /api/risk/current 接口 (统一格式)
- 添加 /api/risk/heatmap 接口
- 添加 /api/alerts/recent 接口
- 添加 /api/demo/reset 接口
- 添加 WebSocket 事件: agv_state, risk_state, alert_event, system_status, mission_status
- 保留所有旧接口兼容
- 添加告警队列 (内存 deque)
- 添加定时广播 system_status

### 步骤 2: 风险闭环增强 (risk_fusion.py)
- 阈值从 config.yaml 读取
- 输出增加 risk_level_cn 字段

### 步骤 3: 前端升级 (dashboard.html)
- 全部文案改中文
- 布局: 左侧地图主区 + 右侧信息面板
- 右侧面板:
  1. AGV 实时状态
  2. 风险评估
  3. 任务状态
  4. 最近告警
  5. 系统状态
  6. 仿真预留区
- 底部: 控制区 + 图层开关
- WebSocket 断连中文提示
- 空数据中文兜底

### 步骤 4: 脚本与文档
- scripts/dev_start.sh — 一键启动开发环境
- scripts/check.sh — 健康检查脚本
- docs/architecture.md — 更新
- docs/api.md — 统一接口文档
- docs/demo.md — 演示说明
- README.md — 更新

### 步骤 5: 验证
- Python 语法检查
- Flask 启动测试
- 各接口可用性
- WebSocket 连接
- 中文显示正常

## 明确不做
- Gazebo/RViz 原生 GUI 嵌入
- Nav2 / SLAM / 自动避障
- 多车支持
- 真实 InSAR 数据接入
- 前端框架迁移 (保持原生 HTML+JS)

## 数据结构约定

见需求文档中的 agv_state, risk_state, alert_event, system_status 结构定义。
