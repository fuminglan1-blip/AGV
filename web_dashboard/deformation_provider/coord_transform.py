"""
coord_transform.py — 仿真坐标 ↔ WGS84 坐标转换

当前阶段:
  AGV 在 Gazebo 仿真中使用平面坐标 (x, y) 单位: 米
  InSAR 图层使用 WGS84 (lat, lng) 单位: 度
  需要一个映射函数将仿真坐标转换为地理坐标以查询形变图层

映射方式:
  仿真原点 (0, 0) 映射到配置的地理锚点 (anchor_lat, anchor_lng)
  x (东) → lng 偏移, y (北) → lat 偏移
  使用简单线性投影 (适用于小范围, <10km)

精度说明:
  当前为实验性映射, 不是精确地理配准。
  后续接入真实北斗坐标后, 可直接使用北斗输出的经纬度,
  此模块仅在仿真阶段提供代理映射。

配置:
  所有参数从 config.yaml 的 map 段读取, 不硬编码。
"""

import math
import os
import yaml


# ═══════════════════════════════════════════════════════════════
# 加载配置
# ═══════════════════════════════════════════════════════════════

_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'config.yaml')
try:
    with open(_cfg_path) as f:
        _cfg = yaml.safe_load(f) or {}
except Exception:
    _cfg = {}

_map_cfg = _cfg.get('map', {})

# 地理锚点 (仿真原点对应的 WGS84 坐标)
ANCHOR_LAT = _map_cfg.get('center_lat', 33.631)
ANCHOR_LNG = _map_cfg.get('center_lng', 114.65)

# 投影常数
METERS_PER_DEG_LAT = 111320.0
METERS_PER_DEG_LNG = 111320.0 * math.cos(math.radians(ANCHOR_LAT))


def sim_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """
    仿真平面坐标 → WGS84 经纬度。

    Args:
        x: 仿真 x 坐标 (m), 正东
        y: 仿真 y 坐标 (m), 正北

    Returns:
        (lat, lng) WGS84
    """
    lat = ANCHOR_LAT + y / METERS_PER_DEG_LAT
    lng = ANCHOR_LNG + x / METERS_PER_DEG_LNG
    return (lat, lng)


def wgs84_to_sim(lat: float, lng: float) -> tuple[float, float]:
    """
    WGS84 经纬度 → 仿真平面坐标。

    Returns:
        (x, y) 仿真坐标 (m)
    """
    x = (lng - ANCHOR_LNG) * METERS_PER_DEG_LNG
    y = (lat - ANCHOR_LAT) * METERS_PER_DEG_LAT
    return (x, y)
