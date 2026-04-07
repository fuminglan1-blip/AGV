# 回归修复计划 — regression_fix_plan.md

> 日期: 2026-04-01
> 触发: 上一轮统一前端 MVP 改动引入的回归

## 识别到的回归项

### 回归 1: dev_start.sh 中 --headless 参数不兼容

**问题**: dev_start.sh 第 74 行使用 `python3 agv_manual_controller.py --headless`，
但 agv_manual_controller.py 不接受 `--headless` 参数。
控制器通过 `sys.stdin.isatty()` 自动检测模式。

**影响**: `--headless` 被传递为未知的 sys.argv 参数。虽然当前代码不解析 argv 所以不会报错，
但这与旧的启动方式不一致，且误导用户以为有 --headless 参数支持。

**修复**: 移除 `--headless` 参数，改用 `< /dev/null` 实现 headless 模式（与旧用法一致）。

### 回归 2: dev_start.sh overlay 路径在 tmux 子窗口中不统一

**问题**: 主脚本检查两个路径（$SRC_DIR/../install 和 $SRC_DIR/install），
但 tmux send-keys 中硬编码只尝试 `$SRC_DIR/../install/setup.bash`，
没有同步 fallback 到 $SRC_DIR/install/setup.bash。

**影响**: 如果 overlay 在 $SRC_DIR/install/ 下，tmux 窗口中的进程无法加载 overlay，
导致 ros2 launch 等命令找不到包。

**修复**: 将 overlay 路径封装为变量，在所有 tmux 窗口统一复用。

### 回归 3: dev_start.sh 直接 attach 导致失败时一闪而过

**问题**: 脚本最后 `tmux attach`，如果前面步骤创建 session 失败或 tmux 不可用，
用户看到终端一闪而过没有任何有用信息。

**影响**: 用户无法判断启动是否成功。

**修复**: 在 attach 前打印所有信息到日志，增加启动前检查，打印明确提示后再 attach。

### 回归 4: 前端右侧信息栏过宽 (360px)

**问题**: 侧边栏固定 360px 宽度，在 1366x768 / 1600x900 等屏幕上占比过大，
压缩地图展示区域。

**影响**: 地图区被压缩，右侧信息区与地图比例不协调。

**修复**: 将侧边栏宽度缩小到 300px，增加中小屏响应式适配。

### 回归 5: 任务选择功能在前端中不够突出

**问题**: 任务选择（路线按钮）虽然代码存在，但在"任务状态"卡片底部嵌套较深，
用户可能看不到，尤其在小屏上可能被截断。

**影响**: 核心演示功能（选择路线、启动任务）入口不明显。

**修复**: 确保任务选择在侧边栏可见位置，路线按钮区域有足够空间。

## 修复顺序

1. 修 dev_start.sh — 路径统一、移除 --headless、增加检查
2. 验证 agv_manual_controller.py 旧用法兼容 — 无需修改代码，只需确认
3. 修 dashboard.html 布局 — 侧边栏缩窄、确保滚动和可见性
4. 验证任务选择功能完整 — 路线按钮、取消任务、进度显示
5. 全链路验证

## 验证方式

- dev_start.sh web 模式可正常启动
- python3 agv_manual_controller.py 交互模式可运行
- python3 agv_manual_controller.py < /dev/null headless 模式可运行
- Flask 启动后所有接口正常
- 前端页面各卡片内容完整可见
- 任务选择入口可见并可操作
- 前端右侧面板可滚动
