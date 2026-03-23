#!/bin/bash

# Phase 3: API Endpoint Testing
# Expected time: 45 minutes
# Tests all API endpoints with curl

set -e

BASE_URL="http://localhost:8000"
PASSED=0
FAILED=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5

    echo -e "${YELLOW}Testing:${NC} $description"
    echo "  $method $endpoint"

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "$expected_status" ]; then
        echo -e "  ${GREEN}✓ Status: $http_code${NC}"
        echo "  Response: $body" | head -c 100
        echo ""
        ((PASSED++))
    else
        echo -e "  ${RED}✗ Expected: $expected_status, Got: $http_code${NC}"
        echo "  Response: $body"
        echo ""
        ((FAILED++))
    fi
}

echo "=========================================="
echo "Phase 3: API Endpoint Testing"
echo "=========================================="
echo ""

# 3.1 Health Check
echo "3.1 Health Check Endpoint"
test_endpoint "GET" "/health" "" "200" "Health check"
echo ""

# 3.2 Auth Endpoints
echo "3.2 Authentication Endpoints"
test_endpoint "GET" "/auth/qrcode" "" "200" "Generate QR code"
test_endpoint "GET" "/auth/status?qrcode_key=test_key" "" "200" "Check login status"
echo ""

# 3.3 Video Endpoints
echo "3.3 Video Management Endpoints"
test_endpoint "GET" "/videos?page=1&page_size=20" "" "200" "Get video list"
test_endpoint "POST" "/videos" '{"bvid":"BV1234567890","title":"Test","description":"Test video","duration":600,"cover":"https://example.com/cover.jpg"}' "201" "Create video"
echo ""

# 3.4 Subtitle Endpoints
echo "3.4 Subtitle Endpoints"
test_endpoint "GET" "/subtitles/search?keyword=test" "" "200" "Search subtitles"
echo ""

# 3.5 Search Endpoints
echo "3.5 Search Endpoints"
test_endpoint "POST" "/search/vector" '{"query":"test","top_k":5,"threshold":0.7}' "200" "Vector search"
test_endpoint "GET" "/search/keyword?q=test&limit=10" "" "200" "Keyword search"
echo ""

# 3.6 Chat Endpoints
echo "3.6 Chat Endpoints"
test_endpoint "POST" "/chat/sessions" '{"title":"Test Session"}' "201" "Create chat session"
echo ""

# 3.7 Task Endpoints
echo "3.7 Task Management Endpoints"
test_endpoint "GET" "/tasks?status=pending" "" "200" "Get task list"
test_endpoint "POST" "/tasks" '{"task_type":"test","params":{}}' "201" "Create task"
echo ""

# 3.8 Error Cases
echo "3.8 Error Handling"
test_endpoint "GET" "/videos/invalid_id" "" "404" "Invalid video ID"
test_endpoint "POST" "/search/vector" '{}' "400" "Missing required parameters"
test_endpoint "GET" "/nonexistent" "" "404" "Nonexistent endpoint"
echo ""

echo "=========================================="
echo "Phase 3 Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "=========================================="

if [ $FAILED -gt 0 ]; then
    exit 1
fi
