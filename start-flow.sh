#!/bin/bash

# Start script for AI Kolegium with CrewAI Flow

echo "🚀 Starting AI Kolegium Redakcyjne with CrewAI Flow..."
echo ""

# Store the starting directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if port 8001 is already in use
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8001 is already in use. Killing existing process..."
    lsof -ti:8001 | xargs kill -9 2>/dev/null
    sleep 2
fi

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    set -a
    source .env
    set +a
fi

# Function to kill processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    # Also try to kill by port in case PIDs are lost
    lsof -ti:8001 | xargs kill -9 2>/dev/null
    lsof -ti:3000 | xargs kill -9 2>/dev/null
    exit
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Start backend with Flow
echo "📡 Starting backend server with CrewAI Flow..."
# Use ai_writing_flow venv which has CrewAI installed
if [ -d "ai_writing_flow/venv" ]; then
    echo "🐍 Activating ai_writing_flow virtual environment (has CrewAI)..."
    source ai_writing_flow/venv/bin/activate
elif [ -d "ai_publishing_cycle/.venv" ]; then
    echo "🐍 Activating backend virtual environment..."
    source ai_publishing_cycle/.venv/bin/activate
elif [ -d ".venv" ]; then
    echo "🐍 Activating global virtual environment..."
    source .venv/bin/activate
fi

cd ai_publishing_cycle && PYTHONPATH=../ai_writing_flow/src:$PYTHONPATH USE_CREWAI_FLOW=true python src/ai_publishing_cycle/copilot_backend.py &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Wait and check if backend actually started
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start!"
    echo "   Check logs above for errors"
    # Continue anyway - maybe frontend can still be useful
else
    echo "✅ Backend is running on PID $BACKEND_PID"
fi

# Start frontend
echo "🎨 Starting frontend..."
# Return to script directory
cd "$SCRIPT_DIR"
if [ -d "vector-wave-ui" ]; then
    cd vector-wave-ui
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        npm install
    fi
    npm run dev &
    FRONTEND_PID=$!
    cd ..
else
    echo "❌ Frontend directory not found!"
    echo "   Script directory: $SCRIPT_DIR"
    echo "   Current directory: $(pwd)"
    echo "   Looking for: ./vector-wave-ui"
    # Don't exit - backend might still work
fi

echo ""
echo "✅ Services started!"
echo "   Backend (Flow): http://localhost:8001"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait