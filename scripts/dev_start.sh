#!/usr/bin/env bash
# dev_start.sh — 一键启动开发环境（港口 AGV 数字孪生）
#
# 用法:
#   ./scripts/dev_start.sh              # 完整仿真链路 (tmux)
#   ./scripts/dev_start.sh web          # 仅启动 Web 服务 (无 Gazebo)
#   ./scripts/dev_start.sh noattach     # 创建 tmux 会话但不自动 attach
#
# 控制器在 tmux 中以 headless 模式运行 (< /dev/null)，
# 接受 /agv/control_cmd 远程命令。
# 如需键盘交互，请在独立终端运行:
#   python3 agv_manual_controller.py
#
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMMON_ENV="$SCRIPT_DIR/common_env.sh"

echo "════════════════════════════════════════════"
echo "  港口 AGV 数字孪生 — 开发环境启动"
echo "════════════════════════════════════════════"

# ── 1. 加载统一环境 ──
source "$COMMON_ENV"
echo "✓ ROS2 环境已加载: ${ROS_DISTRO:-${AGV_ROS_DISTRO_SELECTED:-unknown}}"
if [ "${AGV_WS_SETUP_LOADED:-0}" -eq 1 ]; then
    echo "✓ 工作空间 overlay 已加载: ${AGV_WS_SETUP}"
else
    echo "⚠ 未找到本地 install/setup.bash — Gazebo 仿真前请先在当前机器上 colcon build"
    echo "  (Web 模式可正常使用)"
fi

# ── 3. 检查关键文件 ──
if [ ! -f "$SRC_DIR/agv_manual_controller.py" ]; then
    echo "✗ 错误: 找不到 $SRC_DIR/agv_manual_controller.py"
    exit 1
fi
if [ ! -f "$SRC_DIR/web_dashboard/app.py" ]; then
    echo "✗ 错误: 找不到 $SRC_DIR/web_dashboard/app.py"
    exit 1
fi

MODE="${1:-full}"

# ── Web 模式: 仅启动 Flask 服务 ──
if [ "$MODE" = "web" ]; then
    echo ""
    echo "模式: 仅 Web 服务 (无 Gazebo)"
    echo "  http://localhost:5000"
    echo ""
    cd "$SRC_DIR/web_dashboard"
    python3 app.py
    exit $?
fi

# ── Full / noattach 模式: tmux 多窗口 ──

if [ "${AGV_WS_SETUP_LOADED:-0}" -ne 1 ]; then
    echo ""
    echo "✗ 错误: 完整仿真链路需要本地工作空间 overlay。"
    echo "  请先在当前机器执行: colcon build --symlink-install"
    exit 1
fi

if ! command -v tmux &>/dev/null; then
    echo ""
    echo "✗ 错误: 需要 tmux。"
    echo "  安装: sudo apt install tmux"
    echo "  或使用 web 模式: ./scripts/dev_start.sh web"
    exit 1
fi

SESSION="agv_sim"

# 清理旧 session
tmux kill-session -t "$SESSION" 2>/dev/null || true

ROS_SETUP="source '$COMMON_ENV'"

echo ""
echo "模式: 完整仿真链路 (tmux)"
echo ""

# ── Window 0: Gazebo ──
tmux new-session -d -s "$SESSION" -n "gazebo"
tmux send-keys -t "$SESSION:gazebo" \
    "${ROS_SETUP}; cd '$SCRIPT_DIR'; echo '[Gazebo] 启动仿真...'; echo '  默认主场景: simplified_port_agv_terrain_400m'; echo '  legacy 兼容入口: harbour_diff_drive.launch.py'; echo '  当前主车/主链: agv_ackermann + /agv/*'; ./start_gazebo.sh" Enter

sleep 2

# ── Window 1: Controller (headless via < /dev/null, 与旧 start_controller.sh headless 一致) ──
tmux new-window -t "$SESSION" -n "controller"
tmux send-keys -t "$SESSION:controller" \
    "${ROS_SETUP}; cd '$SRC_DIR'; echo '[Controller] 启动 AGV 控制器 (headless)...'; echo '  键盘交互请在独立终端运行: python3 agv_manual_controller.py'; python3 agv_manual_controller.py < /dev/null" Enter

sleep 1

# ── Window 2: Mission + Web ──
tmux new-window -t "$SESSION" -n "web"
tmux send-keys -t "$SESSION:web" \
    "${ROS_SETUP}; cd '$SRC_DIR/web_dashboard'; echo '[Web] 启动任务控制器...'; python3 agv_mission_controller.py & sleep 1; echo '[Web] 启动 Web 驾驶舱...'; echo '  http://localhost:5000'; python3 app.py" Enter

echo "════════════════════════════════════════════"
echo "  tmux 会话已创建: $SESSION"
echo ""
echo "  窗口:"
echo "    0: gazebo     — Gazebo 仿真"
echo "    1: controller — AGV 控制器 (headless)"
echo "    2: web        — 任务控制器 + Web 驾驶舱"
echo ""
echo "  操作:"
echo "    tmux attach -t $SESSION        进入会话"
echo "    Ctrl+B, 数字键                 切换窗口"
echo "    tmux kill-session -t $SESSION  关闭全部"
echo ""
echo "  浏览器: http://localhost:5000"
echo ""
echo "  如需键盘交互控制器，另开终端运行:"
echo "    cd $SRC_DIR && python3 agv_manual_controller.py"
echo "════════════════════════════════════════════"

if [ "$MODE" = "noattach" ]; then
    echo ""
    echo "  (noattach 模式 — 会话在后台运行)"
    echo ""
else
    tmux attach -t "$SESSION"
fi
