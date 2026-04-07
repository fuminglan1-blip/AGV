# InSAR 数据流

## 数据链路

```
Sentinel-1 SLC (原始)
    ↓ MintPy / ISCE2 (SAR 处理)  [当前为 mock 替代]
velocity.tif (形变速度 mm/yr, EPSG:4326)
    ↓ prepare_insar_demo.py (梯度计算 + 风险分区)
gradient.tif + risk_zones.geojson
    ↓
ZhoukouProvider (加载 GeoTIFF/npz)
    ↓
Flask API
    ├── /api/insar/query    → 点查询
    ├── /api/insar/heatmap  → 热力图数据
    └── /api/insar/risk_zones → 风险分区
    ↓
Leaflet 前端
    ├── InSAR 形变热力图图层 (青紫色调)
    ├── InSAR 风险分区图层 (多边形)
    └── 当前点位形变摘要 (风险评估卡中)
```

## 坐标系说明

| 坐标系 | 用途 | 说明 |
|--------|------|------|
| Gazebo 仿真坐标 (x,y 米) | AGV 位姿 | 原点 = 仿真世界中心 |
| WGS84 EPSG:4326 (lat,lng) | InSAR 图层 | 周口港 ~33.63°N, 114.65°E |

转换: `coord_transform.py` 中的 `sim_to_wgs84()` / `wgs84_to_sim()`
锚点配置: `config.yaml` 的 `map.center_lat` / `map.center_lng`

**当前为实验性映射**, 仿真原点直接映射到配置的地理锚点。
后续接入真实北斗坐标后，可直接使用北斗输出的经纬度，跳过此映射。

## Mock vs 真实数据

当前所有 InSAR 数据为合成 (mock):
- `metadata.json` 中 `is_mock: true`
- API 返回中包含 `is_mock` 字段
- 前端标注 "(示例数据)"

替换为真实数据:
1. 将 MintPy 输出的 velocity.h5 转为 GeoTIFF
2. 放入 `insar_data/zhoukou_port/processed/velocity.tif`
3. 重新运行梯度+风险分区生成
4. 更新 `metadata.json` 中 `is_mock: false`
