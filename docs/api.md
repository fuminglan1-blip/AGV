# API 接口文档 — 港口 AGV 数字孪生

> 基地址: `http://localhost:5000`

## 统一接口 (/api/*)

### GET /api/system/status

系统状态查询。

**响应示例:**
```json
{
  "backend": "online",
  "ros2": "online",
  "websocket": "connected",
  "last_update": "2026-04-01T10:30:00",
  "active_vehicle": "agv_ackermann",
  "uptime_s": 3600.5
}
```

### GET /api/agv/latest

AGV 最新状态。

**响应示例:**
```json
{
  "timestamp": "2026-04-01T10:30:00",
  "id": "agv-001",
  "position": {"x": 5.0, "y": 3.0, "z": 0.0},
  "orientation": {"roll": 0.0, "pitch": 0.0, "yaw": 45.0},
  "speed": 1.2,
  "mode": "mission",
  "source": "ros2"
}
```

### GET /api/agv/path

AGV 历史轨迹。

**响应示例:**
```json
{
  "count": 150,
  "max_points": 500,
  "path": [
    {"x": 5.0, "y": 3.0, "timestamp": 1711958400.0},
    ...
  ]
}
```

### GET /api/risk/current

当前风险评估。

**响应示例:**
```json
{
  "timestamp": "2026-04-01T10:30:00",
  "agv_id": "agv-001",
  "risk_level": "low",
  "risk_level_cn": "低风险",
  "risk_score": 0.15,
  "risk_state": "safe",
  "reasons": ["正常运行 / Normal operation"],
  "terrain_risk": 0.12,
  "gradient_mag": 0.003
}
```

### GET /api/risk/heatmap

风险热力图数据。

**响应示例:**
```json
{
  "count": 1200,
  "grid_resolution": 1.0,
  "grid_range": [-100.0, 100.0],
  "points": [
    {"x": -15.0, "y": 8.0, "risk": 0.55},
    ...
  ]
}
```

### GET /api/alerts/recent

最近告警事件。

**查询参数:** `limit` (int, 默认 20)

**响应示例:**
```json
{
  "count": 5,
  "alerts": [
    {
      "timestamp": "2026-04-01T10:30:00",
      "level": "warn",
      "level_cn": "警告",
      "title": "中风险提示",
      "message": "AGV 进入中风险区域",
      "agv_id": "agv-001"
    }
  ]
}
```

### GET /api/mission/status

任务状态查询。

**响应示例:**
```json
{
  "timestamp": "2026-04-01T10:30:00",
  "mode": "mission",
  "route_name": "standard_operation",
  "running": true,
  "waypoint_index": 3,
  "total_waypoints": 7,
  "progress": "3/7"
}
```

### POST /api/demo/reset

重置演示状态 (清除轨迹、告警、取消任务)。

**响应示例:**
```json
{"status": "reset", "message": "演示数据已清除"}
```

---

## 旧版接口 (兼容保留)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 系统健康检查 |
| `/vehicle_state` | GET | 车辆状态 (位姿+速度+风险) |
| `/trajectory` | GET | 历史轨迹 (最多 500 点) |
| `/trajectory/clear` | POST | 清除轨迹 |
| `/risk/current` | GET | 当前位置风险 |
| `/risk/heatmap` | GET | 风险热力图数据 |
| `/risk/heatmap/refresh` | GET | 刷新热力图缓存 |
| `/control/manual` | POST | 手动控制 `{"action":"speed_up"}` |
| `/control/stop` | POST | 紧急停车 |
| `/mission/start` | POST | 启动预设路线 `{"route_name":"..."}` |
| `/mission/cancel` | POST | 取消任务 |
| `/mission/status` | GET | 任务状态 |
| `/mission/routes` | GET | 可用路线列表 |

---

## WebSocket 事件

| 事件名 | 方向 | 说明 |
|--------|------|------|
| `agv_state` | 服务器→客户端 | AGV 统一状态 (位置/航向/速度/模式) |
| `risk_state` | 服务器→客户端 | 风险评估 (等级/分数/原因) |
| `alert_event` | 服务器→客户端 | 告警事件推送 |
| `system_status` | 服务器→客户端 | 系统状态 (每3秒广播) |
| `mission_status` | 服务器→客户端 | 任务状态更新 |
| `vehicle_pose` | 服务器→客户端 | 旧版位姿推送 (兼容) |

### 手动控制可用动作

`speed_up`, `speed_down`, `steer_left`, `steer_right`, `center_steer`, `stop`, `reset_all`
