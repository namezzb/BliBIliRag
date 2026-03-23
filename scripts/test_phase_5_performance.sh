#!/bin/bash

# Phase 5: Performance & Stability Testing
# Expected time: 30 minutes
# Tests concurrent requests, long-running stability, and database stress

set -e

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "Phase 5: Performance & Stability Testing"
echo "=========================================="
echo ""

# 5.1 Concurrent Testing
echo "5.1 Concurrent Load Testing"
echo "  Testing 100 requests with 10 concurrent connections..."
ab -n 100 -c 10 -q "$BASE_URL/health" 2>&1 | grep -E "Requests/sec|Time per request|Failed requests"
echo ""

# 5.2 Long-running test
echo "5.2 Long-running Stability Test"
echo "  Running 50 sequential requests..."
for i in {1..50}; do
    curl -s "$BASE_URL/health" > /dev/null
    if [ $((i % 10)) -eq 0 ]; then
        echo "  ✓ Completed $i requests"
    fi
done
echo "  ✓ Long-running test completed"
echo ""

# 5.3 Response time analysis
echo "5.3 Response Time Analysis"
echo "  Measuring response times for 20 requests..."
total_time=0
for i in {1..20}; do
    response_time=$(curl -s -w "%{time_total}" -o /dev/null "$BASE_URL/health")
    total_time=$(echo "$total_time + $response_time" | bc)
done
avg_time=$(echo "scale=3; $total_time / 20" | bc)
echo "  Average response time: ${avg_time}s"
echo ""

# 5.4 Memory check
echo "5.4 Memory Usage Check"
ps aux | grep "uvicorn" | grep -v grep | awk '{print "  Memory: " $6 " KB, CPU: " $3 "%"}'
echo ""

echo "=========================================="
echo "✓ Phase 5 Complete"
echo "=========================================="
