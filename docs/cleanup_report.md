# Cleanup Report — 2026-03-31

## Summary

Project file reorganization for maintainability. No core logic was changed. All moves are reversible (files archived, not deleted).

## Files Archived → `archive_pending_review/`

| Original Path | Reason |
|----------------|--------|
| `backend/` (entire directory) | Deprecated old backend. Active backend is `web_dashboard/app.py`. The old app.py was a simpler version without control/mission endpoints. `backend/config/vehicle_source.yaml` had useful config but its values are now integrated into `web_dashboard/config.yaml`. |
| `harbour_assets_description/models/container40/model (copy).sdf` | Old buggy version of container model (referenced container20, wrong scale). The current `model.sdf` has the corrected box collision. |
| `harbour_assets_description/models/container40/Container-40.skp` | SketchUp source file (1.2 MB binary). Not used by Gazebo; the `.dae` mesh is what matters. |
| `web_dashboard/README.md` | Contained outdated references to `backend/` directory. |

## Files Moved (reorganized)

| From | To | Reason |
|------|----|--------|
| `verify_integration.sh` | `scripts/verify_integration.sh` | Consolidate utility scripts |
| `verify_collision_fix.sh` | `scripts/verify_collision_fix.sh` | Consolidate utility scripts |
| `Gazebo_Harbour_Models/` | `third_party/Gazebo_Harbour_Models/` | Third-party reference repo (already COLCON_IGNORE). Separate from project source. |
| `QUICKSTART.md` | `docs/quickstart.md` | Consolidate documentation |
| `web_dashboard/README_OFFLINE.md` | `docs/offline_setup.md` | Consolidate documentation |

## Files Cleaned

| Path | Reason |
|------|--------|
| `web_dashboard/build/`, `install/`, `log/` | colcon build artifacts from an accidental build inside web_dashboard/. Not source files. |

## References Updated

| File | Change |
|------|--------|
| `CLAUDE.md` | `./verify_integration.sh` → `./scripts/verify_integration.sh`; removed `backend/config/vehicle_source.yaml` reference |
| `README.md` | Complete rewrite reflecting current project state |

## Files NOT Moved (with reasons)

| Path | Reason to keep in place |
|------|------------------------|
| `agv_manual_controller.py` (root) | Referenced by start instructions; runs independently of web_dashboard. Moving would break existing workflow docs. |
| `agv_manual_config.yaml` (root) | Loaded by agv_manual_controller.py via `dirname(__file__)` — must stay alongside it. |
| `CLAUDE.md`, `AGENTS.md` (root) | Convention: AI guidance files stay at project root for auto-discovery. |
| `ros_gz_project_template/` | ROS2 package structure — paths are hardcoded in CMakeLists.txt and colcon. Cannot move. |
| `harbour_assets_description/` | Same — ROS2 package with environment hooks. |
| `.claude/` | Claude Code IDE configuration. |

## New Documentation Created

| File | Content |
|------|---------|
| `docs/architecture.md` | Module responsibilities, topic map, threading model |
| `docs/run_guide.md` | Step-by-step launch instructions |
| `docs/cleanup_report.md` | This file |
| `README.md` | Complete rewrite with current architecture |
