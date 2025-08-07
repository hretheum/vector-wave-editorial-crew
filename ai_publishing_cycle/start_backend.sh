#!/bin/bash

cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "✅ Loaded environment variables"
fi

echo "🚀 Starting Vector Wave CrewAI Backend..."
uv run python src/ai_publishing_cycle/copilot_backend.py