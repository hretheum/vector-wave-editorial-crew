#!/bin/bash

# Run FastAPI backend for Vector Wave UI

cd /Users/hretheum/dev/bezrobocie/vector-wave/kolegium

# Activate virtual environment
source ./venv/bin/activate

# Run the FastAPI backend
echo "🚀 Starting FastAPI backend on http://localhost:8001"
cd ai_publishing_cycle
python src/ai_publishing_cycle/copilot_backend.py