#\!/bin/bash

# Test CrewAI Installation Script
echo "🧪 Testing CrewAI installation..."

# Activate virtual environment
source venv/bin/activate

# Test basic CrewAI import
echo "🐍 Testing Python CrewAI import..."
python -c "
import sys
print(f'Python version: {sys.version}')

try:
    import crewai
    print(f'✅ CrewAI version: {crewai.__version__}')
except ImportError as e:
    print(f'❌ CrewAI import failed: {e}')
    sys.exit(1)

try:
    from crewai import Agent, Task, Crew
    print('✅ CrewAI core classes imported successfully')
except ImportError as e:
    print(f'❌ CrewAI core classes import failed: {e}')
    sys.exit(1)

print('🎉 All CrewAI imports successful\!')
"

# Test CrewAI CLI
echo "🔧 Testing CrewAI CLI..."
crewai --version || echo "❌ CrewAI CLI not available"

# Test projects
echo "📦 Testing project imports..."

# Test ai_kolegium_redakcyjne
cd ai_kolegium_redakcyjne
python -c "
try:
    from ai_kolegium_redakcyjne.crew import AiKolegiumRedakcyjne
    print('✅ AI Kolegium Redakcyjne crew imported successfully')
except ImportError as e:
    print(f'❌ AI Kolegium import failed: {e}')
"
cd ..

# Test ai_publishing_cycle
cd ai_publishing_cycle
python -c "
try:
    from ai_publishing_cycle.main import AIPublishingFlow
    print('✅ AI Publishing Cycle flow imported successfully')
except ImportError as e:
    print(f'❌ AI Publishing Cycle import failed: {e}')
"
cd ..

echo "🏁 CrewAI test completed\!"
EOF < /dev/null