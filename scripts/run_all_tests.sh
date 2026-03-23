#!/bin/bash

# Master Test Runner - B站 RAG 项目完整测试
# 执行所有 6 个测试阶段
# 总耗时：约 3.5 小时

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPORT_FILE="test_report_$(date +%Y%m%d_%H%M%S).md"
LOG_FILE="test_execution_$(date +%Y%m%d_%H%M%S).log"

# Counters
PHASES_PASSED=0
PHASES_FAILED=0
START_TIME=$(date +%s)

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}=========================================="
    echo "  $1"
    echo "==========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

run_phase() {
    local phase_num=$1
    local phase_name=$2
    local script=$3
    local expected_time=$4

    print_header "Phase $phase_num: $phase_name ($expected_time)"

    if [ -f "$script" ]; then
        if bash "$script" 2>&1 | tee -a "$LOG_FILE"; then
            print_success "Phase $phase_num completed"
            ((PHASES_PASSED++))
            return 0
        else
            print_error "Phase $phase_num failed"
            ((PHASES_FAILED++))
            return 1
        fi
    else
        print_error "Script not found: $script"
        ((PHASES_FAILED++))
        return 1
    fi
}

# Main execution
print_header "B站 RAG 项目完整测试套件"
echo "开始时间：$(date)"
echo "日志文件：$LOG_FILE"
echo ""

# Check prerequisites
echo "检查前置条件..."
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "虚拟环境未激活，请运行: source .venv/bin/activate"
    exit 1
fi
print_success "虚拟环境已激活"

if ! command -v pytest &> /dev/null; then
    print_error "pytest 未安装"
    exit 1
fi
print_success "pytest 已安装"

echo ""

# Phase 1: Environment Setup
run_phase 1 "Environment Setup & Verification" "scripts/test_phase_1_setup.sh" "15 分钟"

# Phase 2: Unit Tests
run_phase 2 "Unit Tests Execution" "scripts/test_phase_2_units.sh" "30 分钟"

# Phase 3: API Endpoints
run_phase 3 "API Endpoint Testing" "scripts/test_phase_3_api.sh" "45 分钟"

# Phase 4: Integration Tests
# Note: This phase requires manual interaction or test data setup
print_header "Phase 4: End-to-End Integration Testing (60 分钟)"
print_warning "Phase 4 需要手动执行或测试数据准备"
print_warning "请参考 docs/TEST-EXECUTION-GUIDE.md 中的 Phase 4 部分"
echo ""

# Phase 5: Performance Testing
run_phase 5 "Performance & Stability Testing" "scripts/test_phase_5_performance.sh" "30 分钟"

# Phase 6: Error Handling
print_header "Phase 6: Error Handling & Edge Cases (30 分钟)"
print_warning "Phase 6 需要手动执行"
print_warning "请参考 docs/TEST-EXECUTION-GUIDE.md 中的 Phase 6 部分"
echo ""

# Calculate execution time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Generate report
print_header "测试执行完成"
echo "总耗时：${MINUTES}分${SECONDS}秒"
echo ""
echo "测试结果："
echo -e "  ${GREEN}通过的阶段：$PHASES_PASSED${NC}"
echo -e "  ${RED}失败的阶段：$PHASES_FAILED${NC}"
echo ""

# Create summary report
cat > "$REPORT_FILE" << EOF
# B站 RAG 项目测试报告

## 测试概览
- 测试日期：$(date +%Y-%m-%d)
- 测试时间：$(date +%H:%M:%S)
- 总耗时：${MINUTES}分${SECONDS}秒
- 测试环境：Python 3.10+, FastAPI, ChromaDB

## 测试结果汇总
| 阶段 | 名称 | 状态 | 备注 |
|------|------|------|------|
| 1 | Environment Setup | $([ $PHASES_PASSED -ge 1 ] && echo "✓ PASSED" || echo "✗ FAILED") | 环境准备与基础验证 |
| 2 | Unit Tests | $([ $PHASES_PASSED -ge 2 ] && echo "✓ PASSED" || echo "✗ FAILED") | 单元测试验证 |
| 3 | API Endpoints | $([ $PHASES_PASSED -ge 3 ] && echo "✓ PASSED" || echo "✗ FAILED") | API 端点测试 |
| 4 | Integration | ⏳ MANUAL | 端到端集成测试 |
| 5 | Performance | $([ $PHASES_PASSED -ge 5 ] && echo "✓ PASSED" || echo "✗ FAILED") | 性能与稳定性测试 |
| 6 | Error Handling | ⏳ MANUAL | 错误处理与边界情况 |

## 自动化测试结果
- 通过的阶段：$PHASES_PASSED
- 失败的阶段：$PHASES_FAILED
- 总阶段数：6

## 后续步骤
1. 查看详细日志：$LOG_FILE
2. 执行 Phase 4（端到端集成测试）
3. 执行 Phase 6（错误处理与边界情况）
4. 生成最终测试报告

## 参考文档
- 测试执行指南：docs/TEST-EXECUTION-GUIDE.md
- 项目进度：docs/PROJECT-PROGRESS.md
- 快速开始：docs/QUICK-START.md

---
生成时间：$(date)
EOF

echo "测试报告已生成：$REPORT_FILE"
echo "详细日志：$LOG_FILE"
echo ""

if [ $PHASES_FAILED -eq 0 ]; then
    print_success "所有自动化测试阶段通过！"
    exit 0
else
    print_error "部分测试阶段失败，请查看日志"
    exit 1
fi
