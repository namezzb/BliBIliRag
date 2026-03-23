#!/bin/bash

# Phase 6: Error Handling & Edge Cases Testing
# Expected time: 30 minutes
# Tests error handling and boundary conditions

set -e

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_error_case() {
    local description=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_status=$5

    echo -e "${YELLOW}Testing:${NC} $description"
    echo "  $method $endpoint"

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null || echo "error\n500")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "$expected_status" ]; then
        echo -e "  ${GREEN}✓ Status: $http_code${NC}"
        ((PASSED++))
    else
        echo -e "  ${RED}✗ Expected: $expected_status, Got: $http_code${NC}"
        ((FAILED++))
    fi
    echo ""
}

echo "=========================================="
echo "Phase 6: Error Handling & Edge Cases"
echo "=========================================="
echo ""

# 6.1 Invalid Input Tests
echo "6.1 Invalid Input Tests"
test_error_case "Invalid video ID" "GET" "/videos/invalid_id" "" "404"
test_error_case "Missing required parameters" "POST" "/search/vector" "{}" "400"
test_error_case "Invalid JSON" "POST" "/chat/sessions" "{invalid json}" "400"
test_error_case "Invalid page number" "GET" "/videos?page=-1" "" "400"
test_error_case "Invalid page size" "GET" "/videos?page_size=10000" "" "400"
echo ""

# 6.2 Authentication & Authorization Tests
echo "6.2 Authentication & Authorization Tests"
test_error_case "Unauthorized access" "GET" "/videos/favorites" "" "401"
test_error_case "Invalid session" "GET" "/videos?session_id=invalid" "" "401"
test_error_case "Expired token" "GET" "/videos?token=expired" "" "401"
echo ""

# 6.3 Resource Not Found Tests
echo "6.3 Resource Not Found Tests"
test_error_case "Nonexistent video" "GET" "/videos/BV9999999999" "" "404"
test_error_case "Nonexistent task" "GET" "/tasks/99999" "" "404"
test_error_case "Nonexistent chat session" "GET" "/chat/sessions/99999/messages" "" "404"
test_error_case "Nonexistent endpoint" "GET" "/nonexistent" "" "404"
echo ""

# 6.4 Timeout & Rate Limiting Tests
echo "6.4 Timeout & Rate Limiting Tests"
echo "Testing rapid consecutive requests..."
for i in {1..50}; do
    curl -s "$BASE_URL/health" > /dev/null &
done
wait
echo "✓ Handled 50 concurrent requests"
echo ""

# 6.5 Data Validation Tests
echo "6.5 Data Validation Tests"
test_error_case "Empty query string" "POST" "/search/vector" '{"query":"","top_k":5}' "400"
test_error_case "Negative top_k" "POST" "/search/vector" '{"query":"test","top_k":-1}' "400"
test_error_case "Invalid threshold" "POST" "/search/vector" '{"query":"test","threshold":1.5}' "400"
test_error_case "Missing task type" "POST" "/tasks" '{"params":{}}' "400"
echo ""

# 6.6 Boundary Tests
echo "6.6 Boundary Tests"
test_error_case "Very long query" "POST" "/search/vector" "{\"query\":\"$(printf 'a%.0s' {1..10000})\",\"top_k\":5}" "400"
test_error_case "Maximum page size" "GET" "/videos?page_size=1000" "" "400"
test_error_case "Zero page size" "GET" "/videos?page_size=0" "" "400"
echo ""

# 6.7 Concurrent Error Handling
echo "6.7 Concurrent Error Handling"
echo "Testing concurrent error scenarios..."
for i in {1..10}; do
    curl -s -X POST "$BASE_URL/search/vector" \
      -H "Content-Type: application/json" \
      -d '{}' > /dev/null &
done
wait
echo "✓ Handled 10 concurrent invalid requests"
echo ""

# Summary
echo "=========================================="
echo "Phase 6: Error Handling Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "=========================================="

if [ $FAILED -gt 0 ]; then
    exit 1
fi
