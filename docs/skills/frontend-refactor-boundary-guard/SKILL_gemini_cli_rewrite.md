---
name: frontend-refactor-boundary-guard

description: >
  Use before making any frontend change in the Port AGV Digital Twin repo,
  especially when introducing Vue, Three.js, Vite, new routing, new state
  management, new render layers, or any frontend build tooling. This skill
  defines non-negotiable protocol boundaries, hidden runtime dependencies,
  safe migration order, forbidden change patterns, and required verification
  steps so frontend work does not break Flask rendering, Socket.IO, REST,
  ROS2, Gazebo, or the agv_ackermann + /agv/* runtime chain.
---

# Frontend Refactor Boundary Guard

This skill is a hard-guardrail for frontend work in this repo.

Use it whenever the task involves any of the following:

- redesigning or relayouting the dashboard
- splitting HTML/CSS/JS into modules or components
- introducing Vue, Three.js, Vite, React, a bundler, or a frontend dev server
- renaming routes, events, fields, DOM ids, map layers, config keys, or scene keys
- changing Socket.IO, REST, Leaflet, Flask template loading, static assets, or map logic
- centralizing constants, transport logic, state logic, or protocol models
- deleting or replacing legacy frontend code that “looks unused”

## Operating Principles

Follow these priorities in order:

1. **Keep the app running.** Do not break the current dashboard load path, live state, or control flow.
2. **Preserve protocol compatibility.** Do not silently change routes, events, field names, topic names, coordinate semantics, or command grammar.
3. **Prefer adapters over rewrites.** Add compatibility layers first, then migrate incrementally.
4. **Trust code over docs.** Old docs drift. Verify behavior from current source.
5. **Never modernize by assumption.** Read the actual producers and consumers before changing shared logic.

## Known Documentation Drift

Do not rely on old docs alone.

Current runtime code emits:

- `agv_state`
- `risk_state`
- `system_status`
- `mission_status`
- `alert_event`

Older docs may still mention:

- `vehicle_pose`
- `log_event`

Also note:

- the live page still uses several legacy REST endpoints directly
- the current frontend is **not** API-v2-only

Source evidence:

- `web_dashboard/app.py:245-311`
- `web_dashboard/app.py:410-435`
- `web_dashboard/app.py:544-845`
- `web_dashboard/app.py:851-864`
- `web_dashboard/templates/dashboard.html:575-865`

> Line numbers are evidence snapshots, not stable identifiers. If line numbers drift,
> match by route name, event name, function, variable, template block, or payload shape.

## Mandatory Workflow Before Any Frontend Change

Before editing code, do this in order:

1. Read the relevant source files.
2. List every affected protocol boundary.
3. Check whether the change touches any **Hard Red Lines**.
4. If yes, propose a compatibility layer first.
5. Do **not** edit until the compatibility plan is clear.
6. After editing, run the required verification checklist.
7. Report exactly what changed and whether any compatibility bridge was added.

## Hard Red Lines

Treat everything below as **do not change directly**.

If a change is unavoidable:

- add a compatibility bridge first
- preserve old external behavior during migration
- update every producer and consumer deliberately
- document the migration path in the change summary

### 1. Runtime vehicle/topic chain

Do not rename, replace, or bypass the current primary chain:

- `/agv/odometry`
- `/agv/cmd_vel`
- `/agv/control_cmd`
- `/agv/mission_cmd`
- `/agv/mission_status`
- `agv_ackermann`

Definition:

- `ros_gz_project_template/ros_gz_example_bringup/config/ros_gz_agv_ackermann_bridge.yaml:17-43`

Primary consumers:

- `web_dashboard/app.py:157`
- `web_dashboard/app.py:372-379`
- `agv_manual_controller.py:107-113`
- `web_dashboard/agv_mission_controller.py:95-103`
- `web_dashboard/odom_tf_publisher.py:31-35`
- `web_dashboard/odom_visual_helper.py:49-55`

Why this is dangerous:

- This is the root Gazebo -> ROS2 -> Flask -> browser data/control contract.
- If broken, the frontend loses both live state and control.

### 2. Flask page entry and static asset loading

Do not break:

- `/` -> `render_template('dashboard.html', scene_context=SCENE_CONTEXT)`
- Flask `static/` serving for vendored JS/CSS
- same-page loading of local `leaflet.js`, `leaflet-heat.js`, `socket.io.min.js`

Definition:

- `web_dashboard/app.py:516-518`
- `web_dashboard/templates/dashboard.html:7-10`

Why this is dangerous:

- The dashboard is currently Flask-served, not a separate SPA.
- Renaming the template or moving assets without preserving Flask URLs causes immediate white-screen failure.

### 3. Same-origin frontend transport assumptions

Current frontend assumes:

- page, API, and Socket.IO are same-origin
- default Socket.IO path is used
- REST calls use relative URLs such as `fetch('/api/agv/latest')`

Definition:

- `web_dashboard/templates/dashboard.html:575-577`
- `web_dashboard/templates/dashboard.html:683-747`
- `web_dashboard/app.py:159-160`
- `web_dashboard/app.py:927-930`
- `web_dashboard/config.yaml:7-8`

Why this is dangerous:

- Moving Vue to another port without a proxy breaks both API and WebSocket access.

### 4. Socket.IO event names and payload shapes

Do not rename or reshape these without a compatibility bridge:

- `agv_state`
- `risk_state`
- `system_status`
- `mission_status`
- `alert_event`

Definition and emit points:

- `web_dashboard/app.py:410-411`
- `web_dashboard/app.py:435`
- `web_dashboard/app.py:494`
- `web_dashboard/app.py:128`
- `web_dashboard/app.py:856-864`

Current consumers:

- `web_dashboard/templates/dashboard.html:581-585`

Critical payload fields:

- `agv_state`: `timestamp`, `id`, `position.x`, `position.y`, `position.z`, `orientation.yaw`, `speed`, `mode`, `source`
- `risk_state`: `risk_level`, `risk_level_cn`, `risk_score`, `risk_state`, `reasons`, `terrain_risk`, `gradient_mag`
- `system_status`: `backend`, `ros2`, `websocket`, `last_update`, `active_vehicle`, `scene_profile`, `world_size_m`, `local_map_bounds`, `risk_layer_mode`, `uptime_s`
- `mission_status`: `mode`, `route_name`, `running`, `waypoint_index`, `total_waypoints`, `progress`, `timestamp`
- `alert_event`: `timestamp`, `level`, `level_cn`, `title`, `message`, `agv_id`

Definition:

- `web_dashboard/app.py:245-311`
- `web_dashboard/app.py:117-128`

Why this is dangerous:

- These payloads drive multiple UI regions at once.
- `agv_state` is mirrored by `/api/agv/latest`.
- `mission_status` is mirrored by `/api/mission/status`.

### 5. Control and mission command grammar

Do not change manual action names or mission command format without updating every producer and consumer.

Manual actions:

- `speed_up`
- `speed_down`
- `steer_left`
- `steer_right`
- `center_steer`
- `stop`
- `reset_all`
- `emergency_stop`

Mission command format:

- `start:<route_name>`
- `cancel`

Definition:

- `web_dashboard/app.py:610-672`
- `web_dashboard/templates/dashboard.html:724-737`
- `agv_manual_controller.py:132-168`
- `web_dashboard/agv_mission_controller.py:127-137`
- `web_dashboard/agv_mission_controller.py:216-217`

Why this is dangerous:

- UI buttons, keyboard control, Flask endpoints, mission controller, and manual controller all share this grammar.

### 6. Legacy REST endpoints still used by the live page

Do not delete, rename, or silently change these yet:

- `GET /trajectory`
- `POST /trajectory/clear`
- `GET /risk/heatmap`
- `GET /mission/routes`

Definition:

- `web_dashboard/app.py:565-603`
- `web_dashboard/app.py:693-695`

Consumers:

- `web_dashboard/templates/dashboard.html:691-709`
- `web_dashboard/templates/dashboard.html:746`

Why this is dangerous:

- The current page still calls them directly.
- The dashboard currently mixes old and new API usage.

### 7. Scene/map protocol and coordinate convention

Do not directly change:

- `SCENE_CONTEXT` shape
- `local_map_bounds`
- `corridors`, `zones`, `landmarks`
- CRS.Simple `simToLatLng()` convention: simple mode uses `[y, x]`
- map container id `map`

Definition:

- `web_dashboard/app.py:185-217`
- `web_dashboard/templates/dashboard.html:196`
- `web_dashboard/templates/dashboard.html:348-357`
- `web_dashboard/templates/dashboard.html:384-388`
- `web_dashboard/templates/dashboard.html:399-549`

Shared config source:

- `ros_gz_project_template/ros_gz_example_bringup/config/deformation_zones.yaml:11-94`
- `web_dashboard/risk_layer.py:92-143`
- `web_dashboard/risk_layer.py:201-217`

Why this is dangerous:

- The same scene fields are used by backend risk generation and frontend overlays.
- Changing field names or coordinate semantics breaks both display and meaning.

### 8. Leaflet static asset layout

Do not move these casually:

- `web_dashboard/static/css/leaflet.css`
- `web_dashboard/static/css/images/marker-icon.png`
- `web_dashboard/static/css/images/marker-shadow.png`
- `web_dashboard/static/css/images/layers.png`

Definition:

- `web_dashboard/templates/dashboard.html:7`
- `web_dashboard/static/css/leaflet.css:359-407`

Why this is dangerous:

- Leaflet CSS references image paths relative to the CSS file.

## Explicitly Forbidden Change Patterns

Unless the task explicitly requires a full migration plan, **never do these in the same change**:

- rename Socket.IO events and update UI consumption at the same time without an adapter
- rename REST fields and update templates/components in the same step without a protocol bridge
- move the frontend to another origin/port without a proxy plan
- replace Leaflet as the primary operational map before transport/state stabilization
- replace Flask `/` entry while also changing static asset organization
- delete legacy REST endpoints because they “look old”
- delete `dashboard.html` before replacing Flask template entry safely
- remove vendored Leaflet or Socket.IO assets before verifying Flask static delivery
- change scene keys and coordinate semantics in the same change
- centralize duplicated constants while silently changing behavior

## Soft Constraints

These can change, but only through compatibility-minded migration.

### Vue introduction

Preferred approach:

1. Keep Flask serving `/`.
2. Keep same-origin API and Socket.IO.
3. Add a transport adapter first.
4. Add a store/state layer second.
5. Mount Vue into parts of `dashboard.html`.
6. Replace panels incrementally.

Do **not** start with:

- a separate dev server on another origin without a proxy
- renaming endpoints, events, or fields in the same step as framework introduction
- replacing the map engine before transport/state stabilization

### Three.js introduction

Preferred approach:

- add a read-only 3D sidecar view first
- consume the same `agv_state` and `SCENE_CONTEXT`
- keep Leaflet as the primary operational view during first migration

### Build tooling

You may add Vite or another bundler, but preserve:

- Flask `/` entry
- Flask static accessibility
- same-origin API and WebSocket behavior

## Safe Refactor Zones

### A. Visual-safe zone

Usually safe if contracts remain unchanged:

- CSS theme
- layout
- typography
- colors
- icons
- motion/animation
- panel spacing
- visual hierarchy
- responsive refinements
- alert styling
- log styling

### B. Structural-safe zone

Usually safe if external behavior stays identical:

- componentization of right-side panels and bottom cards
- unified store from current globals
- transport helpers and protocol adapters
- refactoring alert/log rendering
- replacing inline JS with modules
- richer error states and debug logs
- code organization and utility extraction

## Hidden Traps

### 1. The current page mixes new and old APIs

Examples:

- `agv_state` fallback uses `GET /api/agv/latest`
- trajectory uses `GET /trajectory`
- heatmap uses `GET /risk/heatmap`
- mission status fallback uses `GET /api/mission/status`
- routes use `GET /mission/routes`

Evidence:

- `web_dashboard/templates/dashboard.html:683-719`

### 2. InSAR is not a pure display layer

It depends on all of these:

- `web_dashboard/config.yaml:48-57`
- `web_dashboard/deformation_provider/coord_transform.py:42-64`
- `web_dashboard/deformation_provider/zhoukou_provider.py:171-259`
- `web_dashboard/app.py:802-844`
- `web_dashboard/templates/dashboard.html:752-845`

Important current behavior:

- the dashboard summary query is currently hardcoded to `GET /api/insar/query?x=0&y=0`
- it is **not** actually querying live AGV position yet

Evidence:

- `web_dashboard/templates/dashboard.html:820-825`

Do not redesign InSAR assuming it is already fully coupled to AGV motion.

### 3. Some constants are duplicated across layers

Examples:

- trajectory cap `500`
- polling interval `3000 ms`
- mission polling `2000 ms`
- system status broadcast `3.0 s`

Evidence:

- `web_dashboard/config.yaml:21`
- `web_dashboard/app.py:81`
- `web_dashboard/app.py:492`
- `web_dashboard/app.py:721`
- `web_dashboard/templates/dashboard.html:352-353`
- `web_dashboard/templates/dashboard.html:859`

If you centralize them, do it as a compatibility refactor, not a silent behavior change.

## Compatibility Layer Templates

Use adapters before rewriting shared behavior.

### Transport adapter

If transport logic is being modernized:

- create `apiClient` for REST access
- create `socketClient` for Socket.IO access
- preserve current routes, methods, and event names externally

### Protocol adapter

If data models are being cleaned up:

- map legacy payloads into internal view/store models
- do **not** rename external payload fields first
- convert at the edge, not in the producer

### State adapter

If globals are being replaced:

- create a store that accepts current payloads unchanged
- migrate UI consumers to the store incrementally
- do not rewrite transport and store contracts in one step

### Vue adapter strategy

If introducing Vue:

- mount into existing Flask page
- attach to stable DOM anchors
- keep existing data sources alive until component migration is complete

## Do Not Delete Yet

Do not remove any of the following without full dependency verification:

- `dashboard.html`
- Flask `/` template entry
- current vendored Leaflet assets
- current vendored Socket.IO asset loading
- legacy REST endpoints still called by the page
- map container id `map`
- `SCENE_CONTEXT` keys used by both frontend and backend

## Protocol Checklist

Before changing frontend structure, lock these into Types or JSON Schema:

- `AgvState`
- `RiskState`
- `SystemStatus`
- `MissionStatus`
- `AlertEvent`
- `TrajectoryPoint`
- `RiskHeatmapPoint`
- `DemoRoutesMap`
- `InsarLayersResponse`
- `InsarQueryResponse`
- `InsarHeatmapResponse`

## Preferred Modernization Path

When asked to modernize the frontend, use this default order:

1. Freeze event names, REST paths, ROS topic names, scene keys, and coordinate semantics.
2. Write protocol Types/Schemas from current code.
3. Extract `apiClient`, `socketClient`, and a protocol adapter layer.
4. Extract a store/state layer.
5. Move non-map UI into Vue components.
6. Keep Leaflet live during the first migration.
7. Add Three.js only as a read-only sidecar view first.
8. Only after that, consider route/build/hosting changes.

## Required Verification After Any Frontend Change

Run or request verification for all of the following:

- `./scripts/check.sh`
- page loads at `http://localhost:5000`
- WebSocket connects and receives `agv_state`
- manual controls still hit `/control/manual`
- mission buttons still hit `/mission/start` and `/mission/cancel`
- trajectory still loads
- risk heatmap still renders
- no broken static asset paths for Leaflet

## Required Change Report Format

After making any frontend change, report all of the following:

1. files changed
2. whether any **Hard Red Lines** were touched
3. whether a compatibility bridge or adapter was added
4. whether any routes/events/fields/topics/scene keys changed
5. what was verified after the change
6. any remaining migration debt or hidden risk

If a task risks breaking current behavior, say so explicitly before editing.

## Recommended Files To Inspect First

Inspect these before editing shared frontend behavior:

- `web_dashboard/app.py`
- `web_dashboard/templates/dashboard.html`
- `web_dashboard/config.yaml`
- `web_dashboard/config/demo_routes.yaml`
- `agv_manual_controller.py`
- `web_dashboard/agv_mission_controller.py`
- `web_dashboard/risk_layer.py`
- `web_dashboard/risk_fusion.py`
- `web_dashboard/deformation_provider/coord_transform.py`
- `web_dashboard/deformation_provider/zhoukou_provider.py`
- `ros_gz_project_template/ros_gz_example_bringup/config/ros_gz_agv_ackermann_bridge.yaml`
- `ros_gz_project_template/ros_gz_example_bringup/config/deformation_zones.yaml`
