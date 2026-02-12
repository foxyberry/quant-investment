#!/bin/bash
# Next.js development server startup script
# Usage: ./scripts/run_web.sh

set -e

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)
WEB_DIR="$PROJECT_ROOT/web"

echo "============================================"
echo "  Next.js Development Server"
echo "============================================"
echo "Project root: $PROJECT_ROOT"
echo "Web directory: $WEB_DIR"

# Check if web directory exists
if [ ! -d "$WEB_DIR" ]; then
    echo "Error: web directory not found at $WEB_DIR"
    exit 1
fi

cd "$WEB_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Default configuration
PORT="${WEB_PORT:-3000}"

echo "Starting Next.js development server..."
echo "  Port: $PORT"
echo "  URL: http://localhost:$PORT"
echo "============================================"

# Run Next.js dev server
npm run dev
