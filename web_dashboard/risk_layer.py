#!/usr/bin/env python3
"""
risk_layer.py - Synthetic compatibility risk layer for the 400 m main scene.

This module keeps the Phase-1 rule-based risk pipeline intact while aligning
the synthetic grid with the default 400 m experiment scene:

  simplified_port_agv_terrain_400m

The heatmap is still synthetic, but it now reads the shared scene profile and
deformation zone parameters so the Gazebo world, backend APIs, and dashboard
all describe the same 400 m layout.
"""

from __future__ import annotations

import math
import os

import numpy as np
import yaml


_MODULE_DIR = os.path.dirname(__file__)
_CFG_PATH = os.path.join(_MODULE_DIR, 'config.yaml')
_DEFAULT_ZONES_PATH = os.path.normpath(os.path.join(
    _MODULE_DIR,
    '..',
    'ros_gz_project_template',
    'ros_gz_example_bringup',
    'config',
    'deformation_zones.yaml',
))


def _load_yaml(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_scene_cfg() -> tuple[dict, dict, str]:
    cfg = _load_yaml(_CFG_PATH)
    scene_cfg = cfg.get('scene', {}) if isinstance(cfg.get('scene'), dict) else {}

    zones_path = os.environ.get('AGV_DEFORMATION_ZONES_FILE')
    if not zones_path:
        zones_path = scene_cfg.get('deformation_zones_file', _DEFAULT_ZONES_PATH)
    if not os.path.isabs(zones_path):
        zones_path = os.path.normpath(os.path.join(_MODULE_DIR, zones_path))

    return cfg, scene_cfg, zones_path


_CFG, _SCENE_CFG, _ZONES_PATH = _resolve_scene_cfg()
_ZONES_CFG = _load_yaml(_ZONES_PATH)
_BOUNDS_CFG = _SCENE_CFG.get('local_map_bounds', {})
_SCENE_WORLD_SIZE = _SCENE_CFG.get('world_size_m', [400.0, 400.0])

SCENE_PROFILE = _SCENE_CFG.get('profile', 'simplified_port_agv_terrain_400m')
RISK_LAYER_MODE = _SCENE_CFG.get('risk_layer_mode', 'synthetic_compat_deformation_yaml')
GRID_MIN_M = float(min(_BOUNDS_CFG.get('min_x', -200.0), _BOUNDS_CFG.get('min_y', -200.0)))
GRID_MAX_M = float(max(_BOUNDS_CFG.get('max_x', 200.0), _BOUNDS_CFG.get('max_y', 200.0)))
GRID_RES_M = float(_CFG.get('heatmap', {}).get('grid_resolution_m', 1.0))
GRID_CELLS = int(round((GRID_MAX_M - GRID_MIN_M) / GRID_RES_M)) + 1

_risk_grid: np.ndarray | None = None


def _rectangle_mask(xx: np.ndarray, yy: np.ndarray, center_xy: list[float], size_m: list[float]) -> np.ndarray:
    cx, cy = center_xy
    sx, sy = size_m
    return (np.abs(xx - cx) <= sx / 2.0) & (np.abs(yy - cy) <= sy / 2.0)


def _landmark_gaussian(xx: np.ndarray, yy: np.ndarray, center_xy: tuple[float, float], sigma_m: float, amplitude: float) -> np.ndarray:
    cx, cy = center_xy
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return amplitude * np.exp(-(rr ** 2) / (2.0 * sigma_m ** 2))


def _build_grid() -> np.ndarray:
    xs = np.linspace(GRID_MIN_M, GRID_MAX_M, GRID_CELLS)
    ys = np.linspace(GRID_MIN_M, GRID_MAX_M, GRID_CELLS)
    xx, yy = np.meshgrid(xs, ys)

    grid = np.full((GRID_CELLS, GRID_CELLS), 0.06, dtype=np.float32)

    zones_cfg = _ZONES_CFG.get('zones', {})

    zone_a = zones_cfg.get('zone_A', {})
    if zone_a:
        mask_a = _rectangle_mask(xx, yy, zone_a.get('center_xy', [-20.0, 10.0]), zone_a.get('size_m', [40.0, 14.0]))
        grid[mask_a] = np.maximum(grid[mask_a], 0.26)

    zone_b = zones_cfg.get('zone_B', {})
    if zone_b:
        center_b = zone_b.get('center_xy', [35.0, 10.0])
        size_b = zone_b.get('size_m', [50.0, 14.0])
        mask_b = _rectangle_mask(xx, yy, center_b, size_b)
        left = center_b[0] - size_b[0] / 2.0
        x_norm = np.clip((xx - left) / max(size_b[0], 1e-6), 0.0, 1.0)
        gradient_band = 0.18 + 0.34 * x_norm
        grid[mask_b] = np.maximum(grid[mask_b], gradient_band[mask_b])

    zone_c = zones_cfg.get('zone_C', {})
    if zone_c:
        cx, cy = zone_c.get('center_xy', [0.0, -40.0])
        radius = float(zone_c.get('radius_m', 2.0))
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        inner = rr <= radius
        ring = 0.48 * np.exp(-(rr ** 2) / (2.0 * (radius * 1.8) ** 2))
        grid = np.maximum(grid, ring.astype(np.float32))
        grid[inner] = np.maximum(grid[inner], 0.72)

    landmarks = _ZONES_CFG.get('landmarks', {})
    crane_pose = landmarks.get('port_crane_pose_xyzrpy', [-60.0, 32.0, 0.0, 0.0, 0.0, 0.0])
    single_pose = landmarks.get('container_single_pose_xyzrpy', [36.876, -44.364, 0.0, 0.0, 0.0, 1.57])
    stack_pose = landmarks.get('container_stack_pose_xyzrpy', [-30.84, -76.44, 0.0, 0.0, 0.0, 0.0])

    grid += _landmark_gaussian(xx, yy, (crane_pose[0], crane_pose[1]), sigma_m=10.0, amplitude=0.18)
    grid += _landmark_gaussian(xx, yy, (single_pose[0], single_pose[1]), sigma_m=7.5, amplitude=0.14)
    grid += _landmark_gaussian(xx, yy, (stack_pose[0], stack_pose[1]), sigma_m=8.5, amplitude=0.16)

    return np.clip(grid, 0.0, 1.0)


def _get_grid() -> np.ndarray:
    global _risk_grid
    if _risk_grid is None:
        _risk_grid = _build_grid()
    return _risk_grid


def _xy_to_idx(x: float, y: float) -> tuple[int, int]:
    ix = int(round((x - GRID_MIN_M) / GRID_RES_M))
    iy = int(round((y - GRID_MIN_M) / GRID_RES_M))
    ix = max(0, min(GRID_CELLS - 1, ix))
    iy = max(0, min(GRID_CELLS - 1, iy))
    return ix, iy


def query(x: float, y: float) -> dict:
    grid = _get_grid()
    in_bounds = (GRID_MIN_M <= x <= GRID_MAX_M) and (GRID_MIN_M <= y <= GRID_MAX_M)

    ix, iy = _xy_to_idx(x, y)
    risk = float(grid[iy, ix])

    ix_l = max(0, ix - 1)
    ix_r = min(GRID_CELLS - 1, ix + 1)
    iy_b = max(0, iy - 1)
    iy_t = min(GRID_CELLS - 1, iy + 1)

    grad_x = float(grid[iy, ix_r] - grid[iy, ix_l]) / (2.0 * GRID_RES_M)
    grad_y = float(grid[iy_t, ix] - grid[iy_b, ix]) / (2.0 * GRID_RES_M)
    grad_mag = math.sqrt(grad_x ** 2 + grad_y ** 2)

    return {
        'risk': round(risk, 4),
        'gradient_x': round(grad_x, 6),
        'gradient_y': round(grad_y, 6),
        'gradient_mag': round(grad_mag, 6),
        'in_bounds': in_bounds,
    }


def get_heatmap_data(step: int = 4) -> list[dict]:
    grid = _get_grid()
    result = []
    for iy in range(0, GRID_CELLS, step):
        for ix in range(0, GRID_CELLS, step):
            risk = float(grid[iy, ix])
            if risk > 0.12:
                x = GRID_MIN_M + ix * GRID_RES_M
                y = GRID_MIN_M + iy * GRID_RES_M
                result.append({'x': round(x, 3), 'y': round(y, 3), 'risk': round(risk, 3)})
    return result


def get_scene_metadata() -> dict:
    zones_cfg = _ZONES_CFG.get('zones', {})
    return {
        'profile': SCENE_PROFILE,
        'mode': RISK_LAYER_MODE,
        'grid_range': [GRID_MIN_M, GRID_MAX_M],
        'grid_resolution_m': GRID_RES_M,
        'world_size_m': _SCENE_WORLD_SIZE,
        'deformation_zones_file': _ZONES_PATH,
        'zones': {
            'zone_A': zones_cfg.get('zone_A', {}),
            'zone_B': zones_cfg.get('zone_B', {}),
            'zone_C': zones_cfg.get('zone_C', {}),
        },
        'landmarks': _ZONES_CFG.get('landmarks', {}),
        'corridors': _ZONES_CFG.get('corridors', {}),
    }
