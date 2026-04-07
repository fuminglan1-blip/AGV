#!/usr/bin/env bash
# check.sh — 系统健康检查（港口 AGV 数字孪生）
#
# 用法: ./scripts/check.sh
#
set -euo pipefail

BASE_URL="${1:-http://localhost:5000}"
PASS=0
FAIL=0
TOTAL=0

check() {
    local desc="$1"
    local url="$2"
    local expect="${3:-200}"
    TOTAL=$((TOTAL + 1))

    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$url" 2>/dev/null || echo "000")

    if [ "$code" = "$expect" ]; then
        echo "  ✓ $desc ($url → $code)"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc ($url → $code, 期望 $expect)"
        FAIL=$((FAIL + 1))
    fi
}

check_json() {
    local desc="$1"
    local url="$2"
    TOTAL=$((TOTAL + 1))

    local body
    body=$(curl -s --connect-timeout 3 "$url" 2>/dev/null || echo "")

    if echo "$body" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "  ✓ $desc — 返回有效 JSON"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc — 无效 JSON 或连接失败"
        FAIL=$((FAIL + 1))
    fi
}

echo "════════════════════════════════════════════"
echo "  港口 AGV 数字孪生 — 系统健康检查"
echo "  目标: $BASE_URL"
echo "════════════════════════════════════════════"
echo ""

echo "1. 基础连接检查"
check "首页" "$BASE_URL/"
check "健康检查" "$BASE_URL/health"
echo ""

echo "2. 旧版接口检查"
check "车辆状态" "$BASE_URL/vehicle_state"
check "轨迹数据" "$BASE_URL/trajectory"
check "当前风险" "$BASE_URL/risk/current"
check "风险热力图" "$BASE_URL/risk/heatmap"
check "任务状态" "$BASE_URL/mission/status"
check "可用路线" "$BASE_URL/mission/routes"
echo ""

echo "3. 统一 API 接口检查"
check "系统状态" "$BASE_URL/api/system/status"
check "AGV 最新状态" "$BASE_URL/api/agv/latest"
check "AGV 轨迹" "$BASE_URL/api/agv/path"
check "风险评估" "$BASE_URL/api/risk/current"
check "风险热力图(API)" "$BASE_URL/api/risk/heatmap"
check "最近告警" "$BASE_URL/api/alerts/recent"
check "任务状态(API)" "$BASE_URL/api/mission/status"
echo ""

echo "4. JSON 格式验证"
check_json "系统状态 JSON" "$BASE_URL/api/system/status"
check_json "AGV 状态 JSON" "$BASE_URL/api/agv/latest"
check_json "风险状态 JSON" "$BASE_URL/api/risk/current"
echo ""

echo "════════════════════════════════════════════"
echo "  结果: $PASS 通过 / $FAIL 失败 / $TOTAL 总计"
if [ "$FAIL" -eq 0 ]; then
    echo "  状态: 全部通过 ✓"
else
    echo "  状态: 存在失败项 ✗"
fi
echo "════════════════════════════════════════════"

exit "$FAIL"
