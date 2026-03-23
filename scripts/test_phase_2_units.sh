#!/bin/bash

# Phase 2: Unit Tests Execution
# Expected time: 30 minutes
# Runs all unit tests across modules 1-12

set -e

echo "=========================================="
echo "Phase 2: Unit Tests Execution"
echo "=========================================="
echo ""

# Configuration
PYTEST_ARGS="-v --tb=short --color=yes"
COVERAGE_ARGS="--cov=app --cov-report=term-missing --cov-report=html"

# Test suites
declare -a TEST_SUITES=(
    "tests/test_settings.py"
    "tests/test_app_factory.py"
    "tests/test_storage_repositories.py"
    "tests/test_session_store.py"
    "tests/test_bilibili_auth_service.py"
    "tests/test_bilibili_content_service.py"
    "tests/test_subtitle_service.py"
    "tests/test_summary_service.py"
    "tests/test_summary_service_llm.py"
    "tests/test_indexing_service.py"
    "tests/test_indexing_chromadb.py"
    "tests/test_indexing_dashscope_embedding.py"
    "tests/test_rag_retrieval.py"
    "tests/test_rag_retrieval_chromadb.py"
    "tests/test_rag_routing.py"
    "tests/test_rag_self_rag.py"
    "tests/test_module_10_integration.py"
    "tests/test_task_queue.py"
)

# Route tests
declare -a ROUTE_TESTS=(
    "tests/test_health_routes.py"
    "tests/test_auth_routes.py"
    "tests/test_video_routes.py"
    "tests/test_subtitle_routes.py"
    "tests/test_search_routes.py"
    "tests/test_chat_routes.py"
    "tests/test_task_routes.py"
)

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Run core service tests
echo "Running core service tests..."
echo ""
for test_file in "${TEST_SUITES[@]}"; do
    if [ -f "$test_file" ]; then
        echo "Testing: $test_file"
        if pytest $PYTEST_ARGS "$test_file"; then
            ((PASSED_TESTS++))
        else
            ((FAILED_TESTS++))
        fi
        ((TOTAL_TESTS++))
        echo ""
    fi
done

# Run route tests
echo "Running API route tests..."
echo ""
for test_file in "${ROUTE_TESTS[@]}"; do
    if [ -f "$test_file" ]; then
        echo "Testing: $test_file"
        if pytest $PYTEST_ARGS "$test_file"; then
            ((PASSED_TESTS++))
        else
            ((FAILED_TESTS++))
        fi
        ((TOTAL_TESTS++))
        echo ""
    fi
done

# Run all tests with coverage
echo "=========================================="
echo "Running all tests with coverage report..."
echo "=========================================="
pytest tests/ $PYTEST_ARGS $COVERAGE_ARGS

echo ""
echo "=========================================="
echo "Phase 2 Summary"
echo "=========================================="
echo "Total test files: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo ""
echo "Coverage report: htmlcov/index.html"
echo "=========================================="
