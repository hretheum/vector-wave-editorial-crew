#!/bin/bash

# Script to activate CrewAI environment

echo "🤖 Activating CrewAI environment..."

# Prefer ai_kolegium_redakcyjne venv as it's the main one
if [ -f "ai_kolegium_redakcyjne/.venv/bin/activate" ]; then
    echo "✅ Activating ai_kolegium_redakcyjne virtual environment"
    echo ""
    echo "Run this command in your shell:"
    echo "source ai_kolegium_redakcyjne/.venv/bin/activate"
    echo ""
    echo "Then you can use CrewAI commands directly:"
    echo "  crewai --help"
    echo "  crewai flow plot"
    echo "  crewai flow run"
    echo ""
    echo "To deactivate later, run: deactivate"
else
    echo "❌ Virtual environment not found!"
    echo "Please run from the kolegium directory"
fi