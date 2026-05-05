#!/bin/bash
# FastAPI development server startup script
# Usage: ./scripts/run_api.sh

set -e

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "============================================"
echo "  FastAPI Development Server"
echo "============================================"
echo "Project root: $PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate
echo "Virtual environment activated: $(which python)"

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "Error: uvicorn not found. Please run: pip install uvicorn[standard]"
    exit 1
fi

# Default configuration
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8002}"

echo "Starting FastAPI server..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Docs: http://localhost:$PORT/docs"
echo "  ReDoc: http://localhost:$PORT/redoc"
echo "============================================"

# Run FastAPI with uvicorn
uvicorn api.main:app --reload --host "$HOST" --port "$PORT"
