# 演示说明 — 港口 AGV 数字孪生

## 快速启动演示

### 方式一: 答辩演示一键启动 (推荐)

```bash
cd AGV_sim/src/scripts
./start_all.sh
```

自动打开 3 个 gnome-terminal 窗口:
1. **Gazebo** — 港口仿真环境
2. **Controller** — AGV 手动控制器 (键盘交互)
3. **Web Dashboard** — 任务控制器 + Flask 驾驶舱

> 无桌面时使用 tmux 版: `./start_all_tmux.sh`

### 方式二: 仅 Web 服务 (前端调试)

```bash
./dev_start.sh web
```

适合前端调试，车辆位置固定在 (0,0)。

### 方式三: 手动分步启动

```bash
# 终端 1: Gazebo 仿真
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ros_gz_example_bringup harbour_diff_drive.launch.py

# 终端 2: AGV 控制器
python3 agv_manual_controller.py

# 终端 3: Web 服务
cd web_dashboard
python3 agv_mission_controller.py &
python3 app.py
```

## 打开驾驶舱

浏览器访问: **http://localhost:5000**

## 演示操作

### 1. 手动控制
- 键盘 W/S/A/D 控制前进/后退/左转/右转
- 空格键紧急停车
- R 键方向盘归正
- Q 键重置全部控制

### 2. 预设路线
- 点击右侧"任务状态"面板中的路线按钮
- 可选路线:
  - **码头巡线**: 沿码头直线来回
  - **转向测试**: 蛇形路线测试转向
  - **避障演示**: 绕过港口障碍物
- 点击"取消任务"停止当前路线

### 3. 风险观察
- 地图上热力图显示风险区域分布
- 右侧"风险评估"面板实时显示:
  - 风险等级 (低/中/高)
  - 风险分数 (0-1)
  - 风险原因
- 驾驶 AGV 进入红色高风险区域可触发告警

### 4. 告警系统
- 风险等级变化时自动生成告警
- 右侧"最近告警"面板显示告警历史
- 底部"系统日志"记录所有事件

### 5. 图层控制
- 勾选/取消"显示轨迹"、"显示风险热力图"、"显示网格"
- "清除轨迹"清除历史路径
- "重置演示"清除全部数据

## 健康检查

```bash
./scripts/check.sh
```

## 关键接口验证

```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/system/status
curl http://localhost:5000/api/agv/latest
curl http://localhost:5000/api/risk/current
curl http://localhost:5000/api/alerts/recent
```
