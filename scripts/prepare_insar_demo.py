#!/usr/bin/env python3
"""
prepare_insar_demo.py — 生成周口港 InSAR 形变 MVP 演示数据

生成内容:
  1. velocity.tif   — 形变速度图 (mm/yr)，模拟港口地面沉降
  2. gradient.tif    — 形变梯度图 (mm/yr/m)，由速度图计算
  3. risk_zones.geojson — 风险分区 (基于阈值划分)
  4. aoi.geojson     — 研究区范围
  5. metadata.json   — 图层元数据

坐标系: EPSG:4326 (WGS84)
实验区: 周口港 (约 33.63°N, 114.65°E)

所有数据为 MOCK / 合成数据，用于打通链路。
后续可替换为 MintPy 真实处理结果。

用法:
  python3 scripts/prepare_insar_demo.py
"""

import json
import os
import sys
import numpy as np

# 尝试导入 rasterio，若不可用则仅生成 GeoJSON
try:
    import rasterio
    from rasterio.transform import from_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False
    print('⚠ rasterio 未安装，将跳过 GeoTIFF 生成 (pip install rasterio)')

# ═══════════════════════════════════════════════════════════════
# 参数配置 (外置，便于后续替换)
# ═══════════════════════════════════════════════════════════════

# 周口港实验区中心 (WGS84)
CENTER_LAT = 33.6310
CENTER_LNG = 114.6500

# 覆盖范围 (度)
EXTENT_DEG = 0.008  # 约 ±0.004° ≈ ±440m

# 栅格分辨率
GRID_SIZE = 200  # 200×200 像元

# 形变速度参数 (mm/yr, 负值=沉降)
BACKGROUND_VELOCITY = -2.0  # 背景沉降速率
HOTSPOTS = [
    # (lat_offset, lng_offset, peak_mm, sigma_deg, description)
    (-0.001, -0.0015, -25.0, 0.0012, '码头装卸区沉降'),
    (0.0005, 0.002, -18.0, 0.001, '集装箱堆场沉降'),
    (-0.002, 0.001, -12.0, 0.0015, '仓储区沉降'),
    (0.002, -0.001, -8.0, 0.002, '港区边缘轻微沉降'),
]

# 风险阈值 (mm/yr, 绝对值)
THRESH_LOW = 5.0     # |v| < 5 → 低风险
THRESH_MED = 15.0    # 5 ≤ |v| < 15 → 中风险
                     # |v| ≥ 15 → 高风险

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          '..', 'insar_data', 'zhoukou_port')

# ═══════════════════════════════════════════════════════════════
# 生成函数
# ═══════════════════════════════════════════════════════════════

def make_velocity_grid():
    """生成形变速度栅格 (mm/yr)."""
    lats = np.linspace(CENTER_LAT - EXTENT_DEG / 2,
                       CENTER_LAT + EXTENT_DEG / 2, GRID_SIZE)
    lngs = np.linspace(CENTER_LNG - EXTENT_DEG / 2,
                       CENTER_LNG + EXTENT_DEG / 2, GRID_SIZE)
    LNG, LAT = np.meshgrid(lngs, lats)

    grid = np.full((GRID_SIZE, GRID_SIZE), BACKGROUND_VELOCITY, dtype=np.float32)

    for lat_off, lng_off, peak, sigma, _ in HOTSPOTS:
        clat = CENTER_LAT + lat_off
        clng = CENTER_LNG + lng_off
        r2 = (LAT - clat) ** 2 + (LNG - clng) ** 2
        grid += peak * np.exp(-r2 / (2 * sigma ** 2))

    # 添加轻微噪声
    rng = np.random.default_rng(42)
    grid += rng.normal(0, 0.5, grid.shape).astype(np.float32)

    bounds = (
        CENTER_LNG - EXTENT_DEG / 2,
        CENTER_LAT - EXTENT_DEG / 2,
        CENTER_LNG + EXTENT_DEG / 2,
        CENTER_LAT + EXTENT_DEG / 2,
    )
    return grid, bounds, lats, lngs


def make_gradient(velocity):
    """从速度图计算梯度幅值 (mm/yr/pixel)."""
    gy, gx = np.gradient(velocity)
    return np.sqrt(gx ** 2 + gy ** 2).astype(np.float32)


def write_geotiff(filepath, data, bounds):
    """写入单波段 GeoTIFF (EPSG:4326)."""
    if not HAS_RASTERIO:
        print(f'  跳过: {filepath} (需要 rasterio)')
        return
    h, w = data.shape
    transform = from_bounds(*bounds, w, h)
    with rasterio.open(filepath, 'w', driver='GTiff',
                       height=h, width=w, count=1,
                       dtype=data.dtype, crs='EPSG:4326',
                       transform=transform) as dst:
        dst.write(data, 1)
        dst.update_tags(
            source='mock_synthetic',
            description='Zhoukou Port InSAR demo data',
        )
    print(f'  ✓ {filepath}')


def make_risk_zones(velocity, bounds):
    """基于阈值将速度图划分为风险分区 GeoJSON."""
    west, south, east, north = bounds
    features = []

    abs_v = np.abs(velocity)
    # 将栅格分成若干块, 每块判定风险等级
    block = 20  # 每 20×20 像元一个区块
    h, w = velocity.shape
    for iy in range(0, h, block):
        for ix in range(0, w, block):
            patch = abs_v[iy:iy + block, ix:ix + block]
            mean_v = float(np.mean(patch))
            if mean_v < THRESH_LOW:
                level, level_cn = 'low', '低风险'
            elif mean_v < THRESH_MED:
                level, level_cn = 'medium', '中风险'
            else:
                level, level_cn = 'high', '高风险'

            # 只输出中/高风险区
            if level == 'low':
                continue

            # 像元 → 经纬度
            x0 = west + (ix / w) * (east - west)
            x1 = west + (min(ix + block, w) / w) * (east - west)
            y0 = south + (iy / h) * (north - south)
            y1 = south + (min(iy + block, h) / h) * (north - south)

            features.append({
                'type': 'Feature',
                'properties': {
                    'risk_level': level,
                    'risk_level_cn': level_cn,
                    'mean_velocity_mm_yr': round(mean_v, 2),
                },
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [[
                        [x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]
                    ]],
                },
            })

    return {'type': 'FeatureCollection', 'features': features}


def make_aoi(bounds):
    """生成 AOI 范围 GeoJSON."""
    w, s, e, n = bounds
    return {
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'properties': {
                'name': '周口港实验区',
                'description': 'Zhoukou Port InSAR study area (mock)',
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
            },
        }],
    }


def make_metadata(bounds):
    """生成图层元数据."""
    return {
        'site': 'zhoukou_port',
        'site_cn': '周口港',
        'description': '周口港 InSAR 地面形变监测 (合成演示数据)',
        'crs': 'EPSG:4326',
        'bounds': {
            'west': bounds[0], 'south': bounds[1],
            'east': bounds[2], 'north': bounds[3],
        },
        'center': {'lat': CENTER_LAT, 'lng': CENTER_LNG},
        'resolution_m': round(EXTENT_DEG * 111320 / GRID_SIZE, 2),
        'grid_size': GRID_SIZE,
        'unit': 'mm/yr',
        'data_source': 'mock_synthetic',
        'is_mock': True,
        'note': '合成数据，仅用于系统链路验证。后续替换为 MintPy 真实处理结果。',
        'timestamp': '2024-01-01T00:00:00Z',
        'layers': {
            'velocity': 'processed/velocity.tif',
            'gradient': 'processed/gradient.tif',
            'risk_zones': 'processed/risk_zones.geojson',
            'aoi': 'metadata/aoi.geojson',
        },
        'thresholds': {
            'low_max_mm_yr': THRESH_LOW,
            'medium_max_mm_yr': THRESH_MED,
        },
        'hotspots': [
            {'description': desc, 'peak_mm_yr': peak}
            for _, _, peak, _, desc in HOTSPOTS
        ],
    }


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    print('═' * 50)
    print('  周口港 InSAR 演示数据生成')
    print('═' * 50)

    processed = os.path.join(OUTPUT_DIR, 'processed')
    metadata_dir = os.path.join(OUTPUT_DIR, 'metadata')
    os.makedirs(processed, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)

    # 1. 形变速度
    print('\n1. 生成形变速度图...')
    velocity, bounds, lats, lngs = make_velocity_grid()
    write_geotiff(os.path.join(processed, 'velocity.tif'), velocity, bounds)
    # 同时保存 numpy 备份 (无需 rasterio 也可加载)
    np.savez_compressed(
        os.path.join(processed, 'velocity.npz'),
        velocity=velocity, bounds=np.array(bounds),
        lats=lats, lngs=lngs,
    )
    print(f'  ✓ velocity.npz (fallback)')

    # 2. 形变梯度
    print('\n2. 生成形变梯度图...')
    gradient = make_gradient(velocity)
    write_geotiff(os.path.join(processed, 'gradient.tif'), gradient, bounds)
    np.savez_compressed(
        os.path.join(processed, 'gradient.npz'),
        gradient=gradient, bounds=np.array(bounds),
    )
    print(f'  ✓ gradient.npz (fallback)')

    # 3. 风险分区
    print('\n3. 生成风险分区...')
    risk_zones = make_risk_zones(velocity, bounds)
    rz_path = os.path.join(processed, 'risk_zones.geojson')
    with open(rz_path, 'w') as f:
        json.dump(risk_zones, f, indent=2)
    print(f'  ✓ {rz_path} ({len(risk_zones["features"])} 个风险区块)')

    # 4. AOI
    print('\n4. 生成 AOI...')
    aoi = make_aoi(bounds)
    aoi_path = os.path.join(metadata_dir, 'aoi.geojson')
    with open(aoi_path, 'w') as f:
        json.dump(aoi, f, indent=2)
    print(f'  ✓ {aoi_path}')

    # 5. 元数据
    print('\n5. 生成元数据...')
    meta = make_metadata(bounds)
    meta_path = os.path.join(metadata_dir, 'metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f'  ✓ {meta_path}')

    print('\n' + '═' * 50)
    print('  完成！所有文件输出到:')
    print(f'  {OUTPUT_DIR}/')
    print('  注意: 所有数据为 MOCK 合成数据')
    print('═' * 50)


if __name__ == '__main__':
    main()
