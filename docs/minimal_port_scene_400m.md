# Minimal Port Scene 400m

## Purpose

`simplified_port_agv_terrain_400m` is a minimal Gazebo experiment scene for the
current `agv_ackermann + /agv/*` runtime path. It is meant for repeatable tests
around:

- localization error impact on AGV safety
- terrain / deformation perception impact on risk early warning
- next-stage integration of BeiDou proxy localization, InSAR deformation, and
  fused risk logic

This scene is intentionally not a full port operations layout.

It is now the default main scene used by:

- `scripts/start_all.sh`
- `scripts/start_all_tmux.sh`
- `scripts/start_gazebo.sh`
- `scripts/dev_start.sh`
- the default README / run guide launch path

## Runtime Contract

- Primary vehicle remains `agv_ackermann`
- `agv_manual_controller.py` remains the only `/agv/cmd_vel` publisher
- `/agv/control_cmd`, `/agv/odometry`, and `/agv/mission_status` contracts are unchanged
- Gazebo still uses the same ROS-Gazebo bridge configuration as the main demo chain
- The new world keeps world name `demo` to preserve `/world/demo/...` bridge topics

## Scene Contents

The world keeps only:

- `ground_plane` at `400 m × 400 m`
- `agv_ackermann`
- `port_crane`
- `container_single`
- `container_stack`

No berth, ship, full quay layout, sea, shoreline, gate, rail, truck staging,
or other unavailable business assets are added.

## Corridor Layout

- Main corridor: `(-120, 10)` to `(120, 10)`, width `12 m`
- Secondary corridor: `(-120, -40)` to `(120, -40)`, width `12 m`
- Connector lane: `(120, 10) -> (120, -40) -> (-120, -40)`

The world renders these corridors as visual overlays only so experiments stay
simple and deterministic.

## Deformation Zones

The authoritative parameter source is:

- [deformation_zones.yaml](/home/loong/AGV_sim/src/ros_gz_project_template/ros_gz_example_bringup/config/deformation_zones.yaml)

Current status:

- Zone A: annotation + parameter layer
- Zone B: annotation + parameter layer
- Zone C: annotation + parameter layer

Why not full physical terrain yet:

- The current phase-1 runtime still relies on a single flat `400 × 400 m`
  ground plane for stability and for preserving the existing demo chain.
- True negative terrain patches would require segmenting the base ground or
  replacing parts of it with local height/mesh patches.

Next-stage physical upgrade path:

- replace Zone A with a local settlement patch
- replace Zone B with a sloped settlement patch
- replace Zone C with a local depression patch
- keep the YAML contract unchanged while swapping the Gazebo representation

## Web Dashboard Boundary Note

The current Gazebo experiment world is `400 m × 400 m`, and the main test
corridors extend to `x = ±120 m`.

The current Web dashboard now uses a 400 m synthetic compatibility grid aligned
to this scene and reads the same `deformation_zones.yaml` metadata for Zone
annotations. The risk layer is still synthetic, not a true terrain solver.

## Launch

```bash
source scripts/common_env.sh
ros2 launch ros_gz_example_bringup simplified_port_agv_terrain_400m.launch.py rviz:=false
```

Optional environment bindings exposed by launch:

- `AGV_SCENE_PROFILE=simplified_port_agv_terrain_400m`
- `AGV_DEFORMATION_ZONES_FILE=<...>/deformation_zones.yaml`
