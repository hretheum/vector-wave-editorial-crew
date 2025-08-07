#!/bin/bash

# Helper script to run CrewAI commands

# Store current directory
CURRENT_DIR=$(pwd)

# Check in current directory first
if [ -f ".venv/bin/crewai" ]; then
    echo "🐍 Using CrewAI from local .venv"
    source .venv/bin/activate
elif [ -f "venv/bin/crewai" ]; then
    echo "🐍 Using CrewAI from local venv"
    source venv/bin/activate
# Check in current directory subfolders
elif [ -f "ai_kolegium_redakcyjne/.venv/bin/crewai" ]; then
    echo "🐍 Using CrewAI from ai_kolegium_redakcyjne venv"
    source ai_kolegium_redakcyjne/.venv/bin/activate
elif [ -f "ai_publishing_cycle/.venv/bin/crewai" ]; then
    echo "🐍 Using CrewAI from ai_publishing_cycle venv"
    source ai_publishing_cycle/.venv/bin/activate
# Check in kolegium directory (fallback)
elif [ -f "/Users/hretheum/dev/bezrobocie/vector-wave/kolegium/ai_kolegium_redakcyjne/.venv/bin/crewai" ]; then
    echo "🐍 Using CrewAI from kolegium project"
    source /Users/hretheum/dev/bezrobocie/vector-wave/kolegium/ai_kolegium_redakcyjne/.venv/bin/activate
else
    echo "❌ CrewAI not found in any virtual environment!"
    echo "   Current directory: $CURRENT_DIR"
    echo "   Please install it first: pip install crewai"
    echo "   Or activate a venv that has crewai installed"
    exit 1
fi

# Run crewai with all arguments
crewai "$@"