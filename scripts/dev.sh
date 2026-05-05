#!/bin/bash
# Full development environment startup script
# Runs both FastAPI (API) and Next.js (Web) servers
# Usage: ./scripts/dev.sh

set -e

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "============================================"
echo "  Quant Investment - Development Environment"
echo "============================================"
echo ""
echo "Starting development servers..."
echo ""
echo "  API:  http://localhost:8002"
echo "  Docs: http://localhost:8002/docs"
echo "  Web:  http://localhost:3002"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "============================================"

# Store PIDs for cleanup
API_PID=""
WEB_PID=""

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down servers..."

    if [ -n "$API_PID" ] && kill -0 "$API_PID" 2>/dev/null; then
        echo "Stopping API server (PID: $API_PID)..."
        kill "$API_PID" 2>/dev/null || true
    fi

    if [ -n "$WEB_PID" ] && kill -0 "$WEB_PID" 2>/dev/null; then
        echo "Stopping Web server (PID: $WEB_PID)..."
        kill "$WEB_PID" 2>/dev/null || true
    fi

    # Wait for processes to terminate
    wait 2>/dev/null || true

    echo "All servers stopped."
    exit 0
}

# Set up trap for cleanup on interrupt
trap cleanup INT TERM

# Check if required directories exist
if [ ! -f "$PROJECT_ROOT/api/main.py" ]; then
    echo "Error: API not found at $PROJECT_ROOT/api/main.py"
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/web" ]; then
    echo "Error: Web directory not found at $PROJECT_ROOT/web"
    exit 1
fi

# Start API server in background
echo "[API] Starting FastAPI server..."
"$PROJECT_ROOT/scripts/run_api.sh" &
API_PID=$!
echo "[API] Started with PID: $API_PID"

# Give API server time to start
sleep 2

# Start Web server in background
echo "[Web] Starting Next.js server..."
"$PROJECT_ROOT/scripts/run_web.sh" &
WEB_PID=$!
echo "[Web] Started with PID: $WEB_PID"

echo ""
echo "============================================"
echo "Both servers are running. Press Ctrl+C to stop."
echo "============================================"

# Wait for both processes
wait
