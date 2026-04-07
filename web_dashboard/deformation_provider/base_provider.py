"""
base_provider.py — 形变数据查询基类

所有 provider (mock / geotiff / mintpy) 实现此接口。
Flask API 只依赖此接口，不关心底层数据来源。
"""

from abc import ABC, abstractmethod
from typing import Optional


class DeformationProvider(ABC):
    """形变数据查询统一接口."""

    @abstractmethod
    def query(self, lat: float, lng: float) -> dict:
        """
        查询指定经纬度的形变信息。

        Returns:
            {
                "ok": bool,
                "source": str,           # 数据来源标识
                "is_mock": bool,         # 是否为合成数据
                "position": {"lat": float, "lng": float},
                "deformation_velocity": float | None,  # mm/yr
                "deformation_gradient": float | None,  # mm/yr/pixel
                "risk_band": "low" | "medium" | "high" | None,
                "risk_band_cn": str,
                "valid": bool,           # 该点是否有有效数据
                "crs": str,
                "timestamp": str,
            }
        """

    @abstractmethod
    def get_layers_info(self) -> dict:
        """
        返回可用图层元信息。

        Returns:
            {
                "site": str,
                "site_cn": str,
                "layers": [...],
                "bounds": {...},
                "crs": str,
                "is_mock": bool,
            }
        """

    @abstractmethod
    def get_heatmap_data(self, step: int = 4) -> list[dict]:
        """
        导出形变热力图数据 (用于 Leaflet 渲染)。

        Returns:
            [{lat, lng, value}, ...]
        """

    @abstractmethod
    def get_risk_zones_geojson(self) -> Optional[dict]:
        """返回风险分区 GeoJSON FeatureCollection, 或 None."""
