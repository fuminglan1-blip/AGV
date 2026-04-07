# InSAR 形变感知 MVP 计划

## 背景

本项目融合"北斗高精度定位 + InSAR 时序形变数据"实现港口 AGV 地基风险预警。
当前阶段优先打通 InSAR 形变感知链路，暂不做完整风险融合算法。

- 北斗定位: 暂用 ROS/Gazebo AGV 位姿代理 (/agv/odometry)
- InSAR 数据: 周口港实验背景，当前使用合成 (mock) 数据
- 风险融合: 下一阶段

## 数据目录

```
insar_data/zhoukou_port/
├── raw/                  # 原始数据占位 (Sentinel-1 SLC / MintPy 输入)
├── processed/            # 处理结果
│   ├── velocity.tif      # 形变速度 (mm/yr), EPSG:4326
│   ├── velocity.npz      # numpy 备份 (无需 rasterio)
│   ├── gradient.tif      # 形变梯度
│   ├── gradient.npz
│   └── risk_zones.geojson  # 风险分区 (基于阈值)
└── metadata/
    ├── aoi.geojson       # 研究区范围
    └── metadata.json     # 图层元数据
```

## Provider 抽象层

```
web_dashboard/deformation_provider/
├── base_provider.py      # 抽象接口
├── zhoukou_provider.py   # 周口港实现 (加载 GeoTIFF/npz)
└── coord_transform.py    # 仿真坐标 ↔ WGS84 转换
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/insar/layers | GET | 可用图层列表与元数据 |
| /api/insar/query?x=&y= | GET | 查询指定点的形变值 (仿真坐标) |
| /api/insar/query?lat=&lng= | GET | 查询指定点的形变值 (WGS84) |
| /api/insar/heatmap | GET | 形变热力图数据 |
| /api/insar/risk_zones | GET | 风险分区 GeoJSON |

## 当前状态

| 组件 | 状态 |
|------|------|
| 数据目录 | ✓ 已建立 |
| Mock GeoTIFF | ✓ 合成数据已生成 |
| Provider 抽象层 | ✓ 已实现 |
| Flask API | ✓ 4 个接口 |
| 前端图层 | ✓ InSAR 热力图 + 风险分区 + 点位查询 |
| 坐标转换 | ✓ coord_transform.py |
| 真实 MintPy 数据 | ✗ 待接入 |
| 风险融合算法 | ✗ 下一阶段 |

## 下一阶段

1. 接入 MintPy 真实处理结果替换 mock
2. 实现风险融合算法 (D-S 证据理论 / 加权模型)
3. 北斗 NMEA 数据格式适配层
4. 多时相形变时序分析
