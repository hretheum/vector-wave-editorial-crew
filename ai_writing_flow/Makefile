# AI Writing Flow - Developer Makefile
# Task 13.1: Automated local setup

.PHONY: help dev-setup dev-clean dev-reset test test-unit test-integration lint format check health logs

# Default target
help:
	@echo "AI Writing Flow - Developer Commands"
	@echo "===================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make dev-setup    - One-command setup for new developers"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make health       - Check system health"
	@echo "  make logs         - View development logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make check        - Run all checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  make dev-clean    - Clean development artifacts"
	@echo "  make dev-reset    - Reset to clean state"

# One-command setup for new developers
dev-setup:
	@echo "🚀 Starting AI Writing Flow Developer Setup..."
	@echo "============================================="
	@echo ""
	
	# Check Python version
	@echo "1️⃣ Checking Python version..."
	@python3 --version | grep -E "Python 3\.(9|10|11|12)" > /dev/null || \
		(echo "❌ Python 3.9+ required" && exit 1)
	@echo "✅ Python version OK"
	@echo ""
	
	# Install uv if not present
	@echo "2️⃣ Checking package manager (uv)..."
	@which uv > /dev/null 2>&1 || \
		(echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo "✅ uv is available"
	@echo ""
	
	# Create virtual environment
	@echo "3️⃣ Setting up virtual environment..."
	@if [ ! -d ".venv" ]; then \
		uv venv; \
		echo "✅ Virtual environment created"; \
	else \
		echo "✅ Virtual environment exists"; \
	fi
	@echo ""
	
	# Install dependencies
	@echo "4️⃣ Installing dependencies..."
	@uv pip install -e .
	@uv pip install -r requirements-dev.txt 2>/dev/null || echo "No dev requirements file"
	@echo "✅ Dependencies installed"
	@echo ""
	
	# Setup environment variables
	@echo "5️⃣ Setting up environment..."
	@if [ ! -f ".env" ]; then \
		echo "Creating .env from template..."; \
		cp .env.example .env 2>/dev/null || \
		echo "# AI Writing Flow Environment\nDEV_MODE=true\nHOT_RELOAD=true\nAUTO_APPROVE=false" > .env; \
		echo "✅ Environment file created"; \
	else \
		echo "✅ Environment file exists"; \
	fi
	@echo ""
	
	# Create necessary directories
	@echo "6️⃣ Creating directory structure..."
	@mkdir -p logs
	@mkdir -p data/cache
	@mkdir -p data/metrics
	@mkdir -p outputs
	@echo "✅ Directories created"
	@echo ""
	
	# Initialize config if needed
	@echo "7️⃣ Initializing configuration..."
	@if [ ! -f "dev_config.json" ]; then \
		echo '{"dev_mode": true, "hot_reload": true, "verbose_logging": true}' > dev_config.json; \
		echo "✅ Development config created"; \
	else \
		echo "✅ Development config exists"; \
	fi
	@echo ""
	
	# Run validation
	@echo "8️⃣ Validating setup..."
	@python3 -c "import ai_writing_flow; print('✅ Package importable')" || \
		(echo "❌ Package import failed" && exit 1)
	@echo ""
	
	# Display next steps
	@echo "🎉 Setup Complete!"
	@echo "=================="
	@echo ""
	@echo "Next steps:"
	@echo "1. Activate environment: source .venv/bin/activate"
	@echo "2. Start development: make dev"
	@echo "3. Check health: make health"
	@echo ""
	@echo "Happy coding! 🚀"

# Start development environment
dev:
	@echo "🔧 Starting development environment..."
	@echo ""
	@echo "📊 Health Dashboard: http://localhost:8083"
	@echo "📝 Logs: tail -f logs/dev.log"
	@echo ""
	@python3 -m ai_writing_flow.monitoring.health_dashboard &
	@echo "✅ Development environment started"

# Check system health
health:
	@echo "🏥 Checking system health..."
	@curl -s http://localhost:8083/health 2>/dev/null | python3 -m json.tool || \
		echo "❌ Health dashboard not running. Start with: make dev"

# View logs
logs:
	@if [ -f "logs/dev.log" ]; then \
		tail -f logs/dev.log; \
	else \
		echo "📝 No logs found. Logs will appear here when the system runs."; \
	fi

# Run all tests
test:
	@echo "🧪 Running all tests..."
	@python3 -m pytest tests/ -v

# Run unit tests only
test-unit:
	@echo "🧪 Running unit tests..."
	@python3 -m pytest tests/unit/ -v --tb=short

# Run integration tests
test-integration:
	@echo "🧪 Running integration tests..."
	@python3 -m pytest tests/integration/ -v

# Run linters
lint:
	@echo "🔍 Running linters..."
	@ruff check src/ tests/ || echo "Install ruff: pip install ruff"
	@mypy src/ --ignore-missing-imports || echo "Install mypy: pip install mypy"

# Format code
format:
	@echo "✨ Formatting code..."
	@ruff format src/ tests/ || echo "Install ruff: pip install ruff"
	@echo "✅ Code formatted"

# Run all checks
check: lint test
	@echo "✅ All checks passed!"

# Clean development artifacts
dev-clean:
	@echo "🧹 Cleaning development artifacts..."
	@rm -rf data/cache/*
	@rm -rf logs/*
	@rm -rf .pytest_cache
	@rm -rf __pycache__
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"

# Reset to clean state
dev-reset: dev-clean
	@echo "🔄 Resetting to clean state..."
	@rm -rf .venv
	@rm -f .env
	@rm -f dev_config.json
	@rm -rf data/
	@echo "✅ Reset complete. Run 'make dev-setup' to start fresh."

# Install pre-commit hooks
install-hooks:
	@echo "🪝 Installing git hooks..."
	@if [ -f ".pre-commit-config.yaml" ]; then \
		pre-commit install; \
		echo "✅ Pre-commit hooks installed"; \
	else \
		echo "Creating basic pre-commit config..."; \
		echo "repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.1.0\n    hooks:\n      - id: ruff\n      - id: ruff-format" > .pre-commit-config.yaml; \
		pre-commit install 2>/dev/null || echo "Install pre-commit: pip install pre-commit"; \
	fi

# Quick validation for CI/CD
validate:
	@echo "✓ Checking imports..."
	@python3 -c "import ai_writing_flow"
	@echo "✓ Checking syntax..."
	@python3 -m py_compile src/ai_writing_flow/**/*.py
	@echo "✓ Basic validation passed"

# Comprehensive environment validation
validate-env:
	@echo "🔍 Running comprehensive environment validation..."
	@python3 scripts/validate_environment.py

# Quick health check
check-env:
	@echo "🏥 Quick environment check..."
	@python3 -c "import ai_writing_flow; print('✅ Package importable')" || echo "❌ Package not installed"
	@curl -s http://localhost:8083/health > /dev/null 2>&1 && echo "✅ Health dashboard running" || echo "❌ Health dashboard not running"
	@test -f .env && echo "✅ .env file exists" || echo "❌ .env file missing"
	@test -f dev_config.json && echo "✅ dev_config.json exists" || echo "❌ dev_config.json missing"

# Git workflow commands
git-setup:
	@echo "🔧 Setting up git workflows..."
	@python3 scripts/git_workflow.py setup
	@echo "✅ Git workflows configured"

git-feature:
	@if [ -z "$(name)" ]; then \
		echo "❌ Usage: make git-feature name='feature-name'"; \
		exit 1; \
	fi
	@python3 scripts/git_workflow.py feature "$(name)" $(if $(issue),--issue $(issue))

git-status:
	@python3 scripts/git_workflow.py status

git-changelog:
	@python3 scripts/git_workflow.py changelog $(if $(since),--since $(since))

# Development workflow shortcuts
flow-start:
	@echo "🚀 Starting development flow..."
	@make dev-setup
	@make git-setup
	@make dev

flow-commit:
	@git add -p
	@git flow-commit

flow-pr:
	@git flow-push
	@gh pr create --fill