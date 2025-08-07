#\!/bin/bash

# Vector Wave Backend Setup Script
echo "🚀 Setting up Vector Wave Backend with CrewAI..."

# Check if we're in the right directory
if [ \! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Make sure you're in the kolegium directory."
    exit 1
fi

# Check if venv exists, create if not
if [ \! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📋 Installing Python dependencies..."
pip install -r requirements.txt

# Install individual CrewAI projects
echo "🛠️  Setting up CrewAI projects..."

# Setup ai_kolegium_redakcyjne
if [ -d "ai_kolegium_redakcyjne" ]; then
    echo "📰 Installing AI Kolegium Redakcyjne..."
    cd ai_kolegium_redakcyjne
    pip install -e .
    cd ..
fi

# Setup ai_publishing_cycle
if [ -d "ai_publishing_cycle" ]; then
    echo "🔄 Installing AI Publishing Cycle..."
    cd ai_publishing_cycle
    pip install -e .
    cd ..
fi

# Verify CrewAI installation
echo "✅ Verifying CrewAI installation..."
python -c "import crewai; print(f'CrewAI version: {crewai.__version__}')" || {
    echo "❌ CrewAI import failed. Trying to fix..."
    pip install --upgrade crewai
}

echo "🎉 Backend setup completed\!"
echo ""
echo "📝 Available commands:"
echo "  npm run backend:dev  - Run AI Kolegium crew"
echo "  npm run crew:run     - Run crew directly"
echo "  npm run crew:train   - Train the crew"
echo "  npm run crew:test    - Test the crew"
echo "  npm run flow:run     - Run publishing flow"
echo ""
echo "🔥 Ready to run: npm run dev"
EOF < /dev/null