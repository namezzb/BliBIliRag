#!/bin/bash

# Phase 1: Environment Setup & Verification
# Expected time: 15 minutes
# Verifies: venv, dependencies, database, health check

set -e

echo "=========================================="
echo "Phase 1: Environment Setup & Verification"
echo "=========================================="
echo ""

# Step 1: Check virtual environment
echo "✓ Step 1: Checking virtual environment..."
if [ -z "$VIRTUAL_ENV" ]; then
    echo "  ⚠ Virtual environment not activated"
    echo "  Run: source .venv/bin/activate"
    exit 1
else
    echo "  ✓ Virtual environment: $VIRTUAL_ENV"
fi
echo ""

# Step 2: Verify dependencies
echo "✓ Step 2: Verifying dependencies..."
python -c "import fastapi; print(f'  ✓ FastAPI: {fastapi.__version__}')"
python -c "import uvicorn; print(f'  ✓ Uvicorn: {uvicorn.__version__}')"
python -c "import chromadb; print(f'  ✓ ChromaDB: {chromadb.__version__}')"
python -c "import langchain; print(f'  ✓ LangChain: {langchain.__version__}')"
python -c "import pydantic; print(f'  ✓ Pydantic: {pydantic.__version__}')"
echo ""

# Step 3: Initialize database
echo "✓ Step 3: Initializing database..."
python scripts/init_db.py
echo ""

# Step 4: Check database file
echo "✓ Step 4: Verifying database file..."
if [ -f "data/bilibilirag.db" ]; then
    echo "  ✓ Database file exists: data/bilibilirag.db"
    ls -lh data/bilibilirag.db
else
    echo "  ✗ Database file not found!"
    exit 1
fi
echo ""

# Step 5: Test health endpoint
echo "✓ Step 5: Testing health endpoint..."
echo "  Starting FastAPI server in background..."
uvicorn main:app --host 127.0.0.1 --port 8000 > /tmp/fastapi.log 2>&1 &
SERVER_PID=$!
echo "  Server PID: $SERVER_PID"

# Wait for server to start
sleep 3

# Test health endpoint
echo "  Testing GET /health..."
RESPONSE=$(curl -s http://localhost:8000/health)
echo "  Response: $RESPONSE"

if echo "$RESPONSE" | grep -q "ok"; then
    echo "  ✓ Health check passed"
else
    echo "  ✗ Health check failed"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Cleanup
kill $SERVER_PID 2>/dev/null || true
sleep 1

echo ""
echo "=========================================="
echo "✓ Phase 1 Complete: All checks passed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start the server: uvicorn main:app --reload"
echo "2. Run Phase 2: bash scripts/test_phase_2_units.sh"
