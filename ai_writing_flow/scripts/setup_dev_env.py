#!/usr/bin/env python3
"""
Enhanced Development Environment Setup Script - Task 13.1

Provides comprehensive setup validation and configuration for new developers.
"""

import os
import sys
import json
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List, Tuple
import shutil


class DevSetupError(Exception):
    """Custom exception for setup errors"""
    pass


class DeveloperSetup:
    """Automated setup for AI Writing Flow development"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.errors = []
        self.warnings = []
        self.python_min_version = (3, 9)
        
    def run(self):
        """Run the complete setup process"""
        print("🚀 AI Writing Flow - Developer Setup")
        print("=" * 50)
        print()
        
        steps = [
            ("System Check", self.check_system),
            ("Python Environment", self.check_python),
            ("Package Manager", self.setup_package_manager),
            ("Virtual Environment", self.setup_venv),
            ("Dependencies", self.install_dependencies),
            ("Configuration", self.setup_configuration),
            ("Directory Structure", self.create_directories),
            ("Git Hooks", self.setup_git_hooks),
            ("Knowledge Base", self.check_kb_connection),
            ("Validation", self.validate_setup)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            try:
                step_func()
                print(f"✅ {step_name} complete")
            except Exception as e:
                print(f"❌ {step_name} failed: {e}")
                self.errors.append(f"{step_name}: {e}")
                if step_name in ["System Check", "Python Environment"]:
                    # Critical errors - stop setup
                    self.print_summary()
                    return False
        
        self.print_summary()
        return len(self.errors) == 0
    
    def check_system(self):
        """Check system requirements"""
        system = platform.system()
        print(f"  OS: {system}")
        print(f"  Architecture: {platform.machine()}")
        
        # Check required commands
        required_commands = {
            "git": "Git version control",
            "curl": "Download tools",
            "make": "Build automation"
        }
        
        for cmd, desc in required_commands.items():
            if shutil.which(cmd):
                print(f"  ✓ {cmd}: {desc}")
            else:
                self.warnings.append(f"Missing {cmd} ({desc})")
                print(f"  ⚠️  {cmd}: Not found ({desc})")
    
    def check_python(self):
        """Check Python version and environment"""
        version = sys.version_info
        print(f"  Python: {version.major}.{version.minor}.{version.micro}")
        
        if version < self.python_min_version:
            raise DevSetupError(
                f"Python {self.python_min_version[0]}.{self.python_min_version[1]}+ required, "
                f"found {version.major}.{version.minor}"
            )
        
        # Check for common Python tools
        tools = ["pip", "venv"]
        for tool in tools:
            try:
                __import__(tool)
                print(f"  ✓ {tool} module available")
            except ImportError:
                self.warnings.append(f"Python {tool} module not available")
    
    def setup_package_manager(self):
        """Setup uv package manager"""
        if shutil.which("uv"):
            print("  ✓ uv already installed")
            return
        
        print("  Installing uv...")
        try:
            subprocess.run(
                "curl -LsSf https://astral.sh/uv/install.sh | sh",
                shell=True,
                check=True,
                capture_output=True
            )
            print("  ✓ uv installed successfully")
        except subprocess.CalledProcessError:
            # Fallback to pip
            self.warnings.append("Could not install uv, using pip instead")
            print("  ⚠️  Using pip as fallback")
    
    def setup_venv(self):
        """Setup virtual environment"""
        venv_path = self.project_root / ".venv"
        
        if venv_path.exists():
            print("  ✓ Virtual environment exists")
            return
        
        print("  Creating virtual environment...")
        if shutil.which("uv"):
            subprocess.run(["uv", "venv"], check=True)
        else:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        
        print("  ✓ Virtual environment created")
    
    def install_dependencies(self):
        """Install project dependencies"""
        print("  Installing base dependencies...")
        
        if shutil.which("uv"):
            cmd = ["uv", "pip", "install", "-e", "."]
        else:
            cmd = [".venv/bin/pip", "install", "-e", "."]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print("  ✓ Base dependencies installed")
        except subprocess.CalledProcessError as e:
            raise DevSetupError(f"Failed to install dependencies: {e}")
        
        # Install dev dependencies if available
        if (self.project_root / "requirements-dev.txt").exists():
            print("  Installing dev dependencies...")
            if shutil.which("uv"):
                cmd = ["uv", "pip", "install", "-r", "requirements-dev.txt"]
            else:
                cmd = [".venv/bin/pip", "install", "-r", "requirements-dev.txt"]
            
            subprocess.run(cmd, capture_output=True)
            print("  ✓ Dev dependencies installed")
    
    def setup_configuration(self):
        """Setup configuration files"""
        # Environment file
        env_file = self.project_root / ".env"
        if not env_file.exists():
            print("  Creating .env file...")
            env_template = self.project_root / ".env.example"
            
            if env_template.exists():
                shutil.copy(env_template, env_file)
            else:
                # Create default env
                env_content = """# AI Writing Flow Environment
DEV_MODE=true
HOT_RELOAD=true
AUTO_APPROVE=false
VERBOSE_LOGGING=true
LOG_LEVEL=DEBUG

# Performance Settings
ENABLE_CACHING=true
CACHE_TTL=3600
PERFORMANCE_WARNINGS=true

# Resource Limits
MAX_MEMORY_MB=2048
MAX_CPU_PERCENT=80
"""
                env_file.write_text(env_content)
            
            print("  ✓ .env file created")
        
        # Development config
        dev_config = self.project_root / "dev_config.json"
        if not dev_config.exists():
            print("  Creating dev_config.json...")
            config = {
                "dev_mode": True,
                "hot_reload": True,
                "auto_approve_human_review": False,
                "verbose_logging": True,
                "caching_enabled": True,
                "cache_ttl": 3600,
                "performance_tracking": True,
                "health_dashboard_port": 8083
            }
            dev_config.write_text(json.dumps(config, indent=2))
            print("  ✓ dev_config.json created")
    
    def create_directories(self):
        """Create necessary directory structure"""
        directories = [
            "logs",
            "data/cache",
            "data/metrics",
            "outputs",
            "outputs/drafts",
            "outputs/final",
            ".tmp"
        ]
        
        for dir_path in directories:
            path = self.project_root / dir_path
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ {dir_path}/")
        
        # Create .gitkeep files to preserve empty directories
        for dir_path in directories:
            gitkeep = self.project_root / dir_path / ".gitkeep"
            gitkeep.touch(exist_ok=True)
    
    def setup_git_hooks(self):
        """Setup git hooks for code quality"""
        pre_commit_config = self.project_root / ".pre-commit-config.yaml"
        
        if not pre_commit_config.exists():
            print("  Creating pre-commit configuration...")
            config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
"""
            pre_commit_config.write_text(config_content)
            print("  ✓ Pre-commit config created")
        
        # Try to install hooks
        if shutil.which("pre-commit"):
            try:
                subprocess.run(["pre-commit", "install"], check=True, capture_output=True)
                print("  ✓ Git hooks installed")
            except subprocess.CalledProcessError:
                self.warnings.append("Could not install git hooks")
        else:
            self.warnings.append("pre-commit not installed, skipping hooks")
    
    def check_kb_connection(self):
        """Check Knowledge Base connectivity"""
        print("  Testing KB connection...")
        
        try:
            # Try to import and test KB
            sys.path.insert(0, str(self.project_root / "src"))
            from ai_writing_flow.tools.enhanced_knowledge_tools import test_kb_connection
            
            if test_kb_connection():
                print("  ✓ Knowledge Base connection OK")
            else:
                self.warnings.append("Knowledge Base connection failed")
                print("  ⚠️  Knowledge Base not accessible")
        except ImportError:
            print("  ⚠️  KB test skipped (will test after setup)")
            self.warnings.append("KB connection test postponed")
    
    def validate_setup(self):
        """Validate the complete setup"""
        print("  Running validation checks...")
        
        # Check imports
        try:
            import ai_writing_flow
            print("  ✓ Package imports successfully")
        except ImportError as e:
            raise DevSetupError(f"Package import failed: {e}")
        
        # Check key components
        components = [
            "ai_writing_flow.config.dev_config",
            "ai_writing_flow.monitoring.local_metrics",
            "ai_writing_flow.optimization.dev_cache"
        ]
        
        for component in components:
            try:
                __import__(component)
                print(f"  ✓ {component.split('.')[-1]} module OK")
            except ImportError as e:
                self.warnings.append(f"Component {component} import failed: {e}")
    
    def print_summary(self):
        """Print setup summary"""
        print("\n" + "=" * 50)
        print("📊 Setup Summary")
        print("=" * 50)
        
        if not self.errors:
            print("✅ Setup completed successfully!")
        else:
            print("❌ Setup completed with errors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        print("\n📚 Next Steps:")
        print("1. Activate environment: source .venv/bin/activate")
        print("2. Start health dashboard: make dev")
        print("3. Run tests: make test")
        print("4. Check system health: make health")
        
        if not self.errors:
            print("\n🎉 Happy coding!")


def main():
    """Main entry point"""
    setup = DeveloperSetup()
    success = setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()