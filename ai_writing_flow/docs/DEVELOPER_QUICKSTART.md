# AI Writing Flow - Developer Quick Start Guide

## 🚀 Quick Start (30 seconds)

```bash
# Clone the repository
git clone <repository-url>
cd ai_writing_flow

# One-command setup
make dev-setup

# Activate environment
source .venv/bin/activate

# Start development
make dev
```

That's it! You're ready to develop. 🎉

## 📋 What Gets Set Up?

The `make dev-setup` command automatically:

1. **Checks System Requirements**
   - Python 3.9+ ✓
   - Git, curl, make ✓
   - Operating system compatibility ✓

2. **Installs Package Manager**
   - UV (ultrafast Python package manager) ✓
   - Falls back to pip if needed ✓

3. **Creates Virtual Environment**
   - Isolated Python environment ✓
   - All dependencies contained ✓

4. **Installs Dependencies**
   - Core package with `pip install -e .` ✓
   - Development tools ✓
   - Testing frameworks ✓

5. **Sets Up Configuration**
   - `.env` file with development settings ✓
   - `dev_config.json` for runtime config ✓
   - Optimized for local development ✓

6. **Creates Directory Structure**
   ```
   ai_writing_flow/
   ├── logs/          # Development logs
   ├── data/
   │   ├── cache/     # Local cache storage
   │   └── metrics/   # Performance metrics
   ├── outputs/       # Generated content
   └── .tmp/          # Temporary files
   ```

7. **Configures Git Hooks**
   - Auto-formatting with Ruff ✓
   - Linting on commit ✓
   - Large file prevention ✓

## 🛠️ Development Commands

### Essential Commands

```bash
# Start development environment with health dashboard
make dev

# Check system health
make health

# View logs
make logs

# Run tests
make test
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Run all checks (lint + test)
make check
```

### Maintenance

```bash
# Clean temporary files
make dev-clean

# Reset to fresh state
make dev-reset
```

## 🏥 Health Dashboard

Once you run `make dev`, access the health dashboard at:
**http://localhost:8083**

The dashboard shows:
- System health status
- Component status (Flow Engine, KB, Cache, UI)
- Performance metrics
- Resource usage
- Recent events

## 🧪 Running Tests

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_specific.py

# Run with coverage
python -m pytest --cov=ai_writing_flow tests/
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Core settings
DEV_MODE=true              # Enable development features
HOT_RELOAD=true            # Auto-reload on changes
AUTO_APPROVE=false         # Require approval for outputs
VERBOSE_LOGGING=true       # Detailed logging

# Performance
ENABLE_CACHING=true        # Enable caching
CACHE_TTL=3600            # Cache timeout (seconds)
PERFORMANCE_WARNINGS=true  # Warn on slow operations
```

### Development Config (dev_config.json)

```json
{
  "dev_mode": true,
  "hot_reload": true,
  "verbose_logging": true,
  "health_dashboard_port": 8083
}
```

## 📝 Project Structure

```
src/ai_writing_flow/
├── agents/           # CrewAI agents
├── crewai_flow/     # Flow orchestration
├── tools/           # Agent tools & KB integration
├── monitoring/      # Metrics & logging
├── optimization/    # Caching & performance
├── config/          # Configuration management
└── ui/             # UI Bridge components
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Error: ai_writing_flow not found**
   ```bash
   # Reinstall in development mode
   pip install -e .
   ```

2. **Health dashboard not accessible**
   ```bash
   # Check if running
   ps aux | grep health_dashboard
   
   # Restart
   make dev
   ```

3. **Cache permission errors**
   ```bash
   # Fix permissions
   chmod -R 755 data/cache
   ```

4. **Knowledge Base connection failed**
   ```bash
   # Check docker is running
   docker ps
   
   # Check KB service
   curl http://localhost:8000/health
   ```

## 🎯 Development Workflow

1. **Start your day**
   ```bash
   cd ai_writing_flow
   source .venv/bin/activate
   make dev
   ```

2. **Make changes**
   - Edit code in your favorite IDE
   - Changes auto-reload if hot reload is enabled
   - Check health dashboard for issues

3. **Test your changes**
   ```bash
   make test
   make lint
   ```

4. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: your feature"
   # Pre-commit hooks run automatically
   ```

## 📚 Additional Resources

- [Architecture Documentation](./ARCHITECTURE.md)
- [API Reference](./API.md)
- [Testing Guide](./TESTING.md)
- [Performance Tuning](./PERFORMANCE.md)

## 💡 Tips

1. **Use the health dashboard** - It's your best friend for debugging
2. **Enable verbose logging** during development
3. **Run tests frequently** - Especially before commits
4. **Check performance warnings** - They help identify bottlenecks
5. **Use caching** - It makes development much faster

## 🆘 Getting Help

- Check the [Troubleshooting](#troubleshooting) section
- Look at test files for usage examples
- Check the health dashboard for system status
- Review logs in `logs/dev.log`

---

Happy coding! 🚀 If you can read this, you're all set up and ready to build amazing AI writing flows!