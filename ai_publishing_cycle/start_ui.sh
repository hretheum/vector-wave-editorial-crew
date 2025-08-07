#!/bin/bash

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
fi

# Install UI dependencies using uv
echo "📦 Installing UI dependencies..."
uv pip install -r requirements-ui.txt

# Start the UI server
echo "🚀 Starting Vector Wave UI on http://localhost:8000"
python src/ai_publishing_cycle/ui_app.py