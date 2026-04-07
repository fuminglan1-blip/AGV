"""
zhoukou_provider.py — 周口港 InSAR 形变数据 Provider

加载 prepare_insar_demo.py 生成的数据文件:
  - velocity.npz / velocity.tif   (形变速度 mm/yr)
  - gradient.npz / gradient.tif   (形变梯度)
  - risk_zones.geojson            (风险分区)
  - metadata.json                 (元数据)

优先使用 GeoTIFF (rasterio)，若不可用则回退到 .npz (numpy)。
当数据文件不存在时，自动回退到内置 mock 模式。

坐标系: EPSG:4326 (WGS84)
"""

import json
import math
import os
from datetime import datetime
from typing import Optional

import numpy as np

from .base_provider import DeformationProvider

# 尝试导入 rasterio
try:
    import rasterio
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

# ═══════════════════════════════════════════════════════════════
# 默认路径
# ═══════════════════════════════════════════════════════════════

_DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'insar_data', 'zhoukou_port',
)

# 风险阈值 (mm/yr 绝对值)
_THRESH_LOW = 5.0
_THRESH_MED = 15.0

_RISK_CN = {'low': '低风险', 'medium': '中风险', 'high': '高风险'}


class ZhoukouProvider(DeformationProvider):
    """周口港 InSAR 形变数据查询."""

    def __init__(self, data_dir: str = _DEFAULT_DATA_DIR):
        self.data_dir = os.path.abspath(data_dir)
        self.velocity = None    # np.ndarray (H, W)
        self.gradient = None    # np.ndarray (H, W)
        self.bounds = None      # (west, south, east, north)
        self.lats = None        # 1D array
        self.lngs = None        # 1D array
        self.metadata = None    # dict
        self.risk_zones = None  # GeoJSON dict
        self.is_mock = True
        self._loaded = False
        self._load()

    def _load(self):
        """尝试加载数据文件."""
        processed = os.path.join(self.data_dir, 'processed')
        meta_dir = os.path.join(self.data_dir, 'metadata')

        # 1. 加载元数据
        meta_path = os.path.join(meta_dir, 'metadata.json')
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                self.metadata = json.load(f)
            self.is_mock = self.metadata.get('is_mock', True)

        # 2. 加载速度图 (优先 GeoTIFF, 回退 npz)
        vel_tif = os.path.join(processed, 'velocity.tif')
        vel_npz = os.path.join(processed, 'velocity.npz')

        if HAS_RASTERIO and os.path.exists(vel_tif):
            self._load_from_tif(vel_tif, 'velocity')
            grad_tif = os.path.join(processed, 'gradient.tif')
            if os.path.exists(grad_tif):
                self._load_from_tif(grad_tif, 'gradient')
        elif os.path.exists(vel_npz):
            self._load_from_npz(vel_npz)
            grad_npz = os.path.join(processed, 'gradient.npz')
            if os.path.exists(grad_npz):
                d = np.load(grad_npz)
                self.gradient = d['gradient']
        else:
            print('[ZhoukouProvider] ⚠ 无数据文件，使用内置 mock')
            self._generate_inline_mock()

        # 3. 加载风险分区
        rz_path = os.path.join(processed, 'risk_zones.geojson')
        if os.path.exists(rz_path):
            with open(rz_path) as f:
                self.risk_zones = json.load(f)

        self._loaded = True
        src = 'GeoTIFF' if (HAS_RASTERIO and os.path.exists(vel_tif)) else 'npz'
        if self.velocity is not None:
            print(f'[ZhoukouProvider] ✓ 周口港数据已加载 ({src}, '
                  f'{self.velocity.shape}, mock={self.is_mock})')

    def _load_from_tif(self, path, attr):
        with rasterio.open(path) as ds:
            data = ds.read(1)
            b = ds.bounds
            if attr == 'velocity':
                self.velocity = data
                self.bounds = (b.left, b.bottom, b.right, b.top)
                h, w = data.shape
                self.lats = np.linspace(b.bottom, b.top, h)
                self.lngs = np.linspace(b.left, b.right, w)
            else:
                self.gradient = data

    def _load_from_npz(self, path):
        d = np.load(path)
        self.velocity = d['velocity']
        self.bounds = tuple(d['bounds'])
        self.lats = d['lats']
        self.lngs = d['lngs']

    def _generate_inline_mock(self):
        """内置最小 mock (当外部文件完全缺失时)."""
        sz = 100
        center_lat, center_lng = 33.631, 114.65
        ext = 0.004
        self.lats = np.linspace(center_lat - ext, center_lat + ext, sz)
        self.lngs = np.linspace(center_lng - ext, center_lng + ext, sz)
        self.bounds = (center_lng - ext, center_lat - ext,
                       center_lng + ext, center_lat + ext)
        LNG, LAT = np.meshgrid(self.lngs, self.lats)
        r = np.sqrt((LAT - center_lat) ** 2 + (LNG - center_lng) ** 2)
        self.velocity = (-15.0 * np.exp(-r ** 2 / (2 * 0.001 ** 2)) - 2.0).astype(np.float32)
        gy, gx = np.gradient(self.velocity)
        self.gradient = np.sqrt(gx ** 2 + gy ** 2).astype(np.float32)
        self.is_mock = True

    # ── 坐标 → 像元索引 ──

    def _latlng_to_idx(self, lat, lng):
        """WGS84 (lat, lng) → (row, col) 像元索引, 或 None."""
        if self.velocity is None or self.bounds is None:
            return None
        w, s, e, n = self.bounds
        if not (s <= lat <= n and w <= lng <= e):
            return None
        h, width = self.velocity.shape
        row = int((lat - s) / (n - s) * (h - 1))
        col = int((lng - w) / (e - w) * (width - 1))
        row = max(0, min(h - 1, row))
        col = max(0, min(width - 1, col))
        return row, col

    def _velocity_to_risk(self, vel):
        """速度绝对值 → 风险等级."""
        av = abs(vel)
        if av >= _THRESH_MED:
            return 'high'
        if av >= _THRESH_LOW:
            return 'medium'
        return 'low'

    # ═══ 接口实现 ═══

    def query(self, lat: float, lng: float) -> dict:
        idx = self._latlng_to_idx(lat, lng)
        if idx is None:
            return {
                'ok': False,
                'source': 'zhoukou_port_insar',
                'is_mock': self.is_mock,
                'position': {'lat': lat, 'lng': lng},
                'deformation_velocity': None,
                'deformation_gradient': None,
                'risk_band': None,
                'risk_band_cn': '超出范围',
                'valid': False,
                'crs': 'EPSG:4326',
                'timestamp': self._timestamp(),
            }
        row, col = idx
        vel = float(self.velocity[row, col])
        grad = float(self.gradient[row, col]) if self.gradient is not None else 0.0
        risk = self._velocity_to_risk(vel)
        return {
            'ok': True,
            'source': 'zhoukou_port_insar',
            'is_mock': self.is_mock,
            'position': {'lat': round(lat, 6), 'lng': round(lng, 6)},
            'deformation_velocity': round(vel, 3),
            'deformation_gradient': round(grad, 5),
            'risk_band': risk,
            'risk_band_cn': _RISK_CN.get(risk, risk),
            'valid': True,
            'crs': 'EPSG:4326',
            'timestamp': self._timestamp(),
        }

    def get_layers_info(self) -> dict:
        layers = []
        if self.velocity is not None:
            layers.append({
                'id': 'velocity', 'name': '形变速度', 'unit': 'mm/yr',
                'type': 'raster', 'available': True,
            })
        if self.gradient is not None:
            layers.append({
                'id': 'gradient', 'name': '形变梯度', 'unit': 'mm/yr/px',
                'type': 'raster', 'available': True,
            })
        if self.risk_zones is not None:
            layers.append({
                'id': 'risk_zones', 'name': '风险分区', 'unit': '',
                'type': 'vector', 'available': True,
            })

        meta = self.metadata or {}
        return {
            'site': 'zhoukou_port',
            'site_cn': '周口港',
            'description': meta.get('description', '周口港 InSAR 形变监测'),
            'layers': layers,
            'bounds': meta.get('bounds', {
                'west': self.bounds[0], 'south': self.bounds[1],
                'east': self.bounds[2], 'north': self.bounds[3],
            }) if self.bounds else None,
            'center': meta.get('center', {'lat': 33.631, 'lng': 114.65}),
            'crs': 'EPSG:4326',
            'is_mock': self.is_mock,
            'timestamp': self._timestamp(),
        }

    def get_heatmap_data(self, step: int = 4) -> list[dict]:
        if self.velocity is None:
            return []
        h, w = self.velocity.shape
        result = []
        for iy in range(0, h, step):
            for ix in range(0, w, step):
                vel = float(self.velocity[iy, ix])
                if abs(vel) < 1.0:  # 跳过极小值
                    continue
                lat = float(self.lats[iy]) if iy < len(self.lats) else 0
                lng = float(self.lngs[ix]) if ix < len(self.lngs) else 0
                # 归一化到 0-1 (用于热力图强度)
                intensity = min(abs(vel) / 30.0, 1.0)
                result.append({
                    'lat': round(lat, 6),
                    'lng': round(lng, 6),
                    'value': round(intensity, 3),
                    'velocity': round(vel, 2),
                })
        return result

    def get_risk_zones_geojson(self) -> Optional[dict]:
        return self.risk_zones

    def _timestamp(self):
        if self.metadata and 'timestamp' in self.metadata:
            return self.metadata['timestamp']
        return datetime.now().isoformat()
