#!/usr/bin/env python3
"""
Local Environment Validation - Task 13.3

Comprehensive validation of the development environment to ensure
everything is properly configured and working.
"""

import sys
import os
import subprocess
import json
import time
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Any
import psutil
import requests


class EnvironmentValidator:
    """Validates the local development environment"""
    
    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []
        self.project_root = Path.cwd()
    
    def run_all_checks(self) -> bool:
        """Run all validation checks"""
        print("🔍 AI Writing Flow - Environment Validation")
        print("=" * 50)
        print()
        
        check_groups = [
            ("System Requirements", self.check_system_requirements),
            ("Python Environment", self.check_python_environment),
            ("Project Structure", self.check_project_structure),
            ("Dependencies", self.check_dependencies),
            ("Configuration", self.check_configuration),
            ("Services", self.check_services),
            ("Performance", self.check_performance),
            ("Integration", self.check_integration)
        ]
        
        total_checks = 0
        passed_checks = 0
        
        for group_name, check_func in check_groups:
            print(f"\n📋 {group_name}")
            print("-" * 40)
            
            group_passed, group_total = check_func()
            passed_checks += group_passed
            total_checks += group_total
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Validation Summary")
        print("=" * 50)
        print(f"Total checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed: {total_checks - passed_checks}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        success = len(self.errors) == 0
        
        if success:
            print("\n✅ Environment validation PASSED!")
            print("Your development environment is properly configured.")
        else:
            print("\n❌ Environment validation FAILED!")
            print("Please fix the errors above before proceeding.")
        
        return success
    
    def check_system_requirements(self) -> Tuple[int, int]:
        """Check system requirements"""
        checks = []
        
        # Python version
        py_version = sys.version_info
        if py_version >= (3, 9):
            checks.append((True, f"Python {py_version.major}.{py_version.minor} ✓"))
        else:
            checks.append((False, f"Python {py_version.major}.{py_version.minor} (3.9+ required)"))
            self.errors.append("Python 3.9 or higher is required")
        
        # Memory
        memory_gb = psutil.virtual_memory().total / (1024**3)
        if memory_gb >= 4:
            checks.append((True, f"Memory: {memory_gb:.1f}GB ✓"))
        else:
            checks.append((False, f"Memory: {memory_gb:.1f}GB (4GB+ recommended)"))
            self.warnings.append(f"Low memory: {memory_gb:.1f}GB")
        
        # Disk space
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        if free_gb >= 2:
            checks.append((True, f"Free disk: {free_gb:.1f}GB ✓"))
        else:
            checks.append((False, f"Free disk: {free_gb:.1f}GB (2GB+ recommended)"))
            self.warnings.append(f"Low disk space: {free_gb:.1f}GB")
        
        # Required commands
        commands = {
            "git": "Version control",
            "make": "Build automation",
            "curl": "HTTP client"
        }
        
        for cmd, desc in commands.items():
            if self._command_exists(cmd):
                checks.append((True, f"{cmd}: {desc} ✓"))
            else:
                checks.append((False, f"{cmd}: {desc} ✗"))
                self.warnings.append(f"Missing command: {cmd} ({desc})")
        
        return self._print_checks(checks)
    
    def check_python_environment(self) -> Tuple[int, int]:
        """Check Python environment setup"""
        checks = []
        
        # Virtual environment
        if sys.prefix != sys.base_prefix:
            checks.append((True, "Virtual environment active ✓"))
        else:
            checks.append((False, "Virtual environment not active"))
            self.warnings.append("Virtual environment not activated")
        
        # Package manager
        if self._command_exists("uv"):
            checks.append((True, "UV package manager installed ✓"))
        elif self._command_exists("pip"):
            checks.append((True, "pip available (uv recommended) ✓"))
        else:
            checks.append((False, "No package manager found"))
            self.errors.append("No Python package manager available")
        
        # Key Python packages
        packages = ["setuptools", "pip", "wheel"]
        for pkg in packages:
            try:
                importlib.import_module(pkg)
                checks.append((True, f"{pkg} installed ✓"))
            except ImportError:
                checks.append((False, f"{pkg} not installed"))
                self.warnings.append(f"Missing package: {pkg}")
        
        return self._print_checks(checks)
    
    def check_project_structure(self) -> Tuple[int, int]:
        """Check project directory structure"""
        checks = []
        
        # Required directories
        required_dirs = [
            "src/ai_writing_flow",
            "tests",
            "docs",
            "scripts",
            ".github"
        ]
        
        for dir_path in required_dirs:
            path = self.project_root / dir_path
            if path.exists():
                checks.append((True, f"{dir_path}/ exists ✓"))
            else:
                checks.append((False, f"{dir_path}/ missing"))
                self.errors.append(f"Missing directory: {dir_path}")
        
        # Required files
        required_files = [
            "pyproject.toml",
            "Makefile",
            ".env.example",
            ".gitmessage"
        ]
        
        for file_path in required_files:
            path = self.project_root / file_path
            if path.exists():
                checks.append((True, f"{file_path} exists ✓"))
            else:
                checks.append((False, f"{file_path} missing"))
                if file_path == ".env.example":
                    self.warnings.append(f"Missing file: {file_path}")
                else:
                    self.errors.append(f"Missing file: {file_path}")
        
        return self._print_checks(checks)
    
    def check_dependencies(self) -> Tuple[int, int]:
        """Check project dependencies"""
        checks = []
        
        # Core package
        try:
            import ai_writing_flow
            checks.append((True, "ai_writing_flow package importable ✓"))
        except ImportError:
            checks.append((False, "ai_writing_flow package not installed"))
            self.errors.append("Core package not installed. Run: pip install -e .")
        
        # Key dependencies
        dependencies = {
            "crewai": "Agent framework",
            "structlog": "Logging",
            "psutil": "System monitoring",
            "pydantic": "Data validation"
        }
        
        for pkg, desc in dependencies.items():
            try:
                importlib.import_module(pkg)
                checks.append((True, f"{pkg}: {desc} ✓"))
            except ImportError:
                checks.append((False, f"{pkg}: {desc} ✗"))
                self.errors.append(f"Missing dependency: {pkg} ({desc})")
        
        return self._print_checks(checks)
    
    def check_configuration(self) -> Tuple[int, int]:
        """Check configuration files"""
        checks = []
        
        # Environment file
        env_file = self.project_root / ".env"
        if env_file.exists():
            checks.append((True, ".env file exists ✓"))
            
            # Check key variables
            env_content = env_file.read_text()
            required_vars = ["DEV_MODE", "HOT_RELOAD", "AUTO_APPROVE"]
            
            for var in required_vars:
                if f"{var}=" in env_content:
                    checks.append((True, f"{var} configured ✓"))
                else:
                    checks.append((False, f"{var} not set"))
                    self.warnings.append(f"Missing env var: {var}")
        else:
            checks.append((False, ".env file missing"))
            self.warnings.append("No .env file. Copy from .env.example")
        
        # Dev config
        dev_config = self.project_root / "dev_config.json"
        if dev_config.exists():
            try:
                config = json.loads(dev_config.read_text())
                checks.append((True, "dev_config.json valid ✓"))
                
                # Check key settings
                if config.get("dev_mode"):
                    checks.append((True, "Development mode enabled ✓"))
                else:
                    checks.append((False, "Development mode disabled"))
                    self.warnings.append("Development mode not enabled")
                    
            except json.JSONDecodeError:
                checks.append((False, "dev_config.json invalid"))
                self.errors.append("Invalid JSON in dev_config.json")
        else:
            checks.append((False, "dev_config.json missing"))
            self.warnings.append("No dev_config.json file")
        
        return self._print_checks(checks)
    
    def check_services(self) -> Tuple[int, int]:
        """Check required services"""
        checks = []
        
        # Health dashboard
        try:
            response = requests.get("http://localhost:8083/health", timeout=2)
            if response.status_code == 200:
                checks.append((True, "Health dashboard running ✓"))
                
                # Check health status
                health_data = response.json()
                if health_data.get("overall_status") == "healthy":
                    checks.append((True, "System health: healthy ✓"))
                else:
                    checks.append((False, f"System health: {health_data.get('overall_status')}"))
                    self.warnings.append("System health not optimal")
            else:
                checks.append((False, f"Health dashboard error: {response.status_code}"))
                self.warnings.append("Health dashboard not responding correctly")
                
        except requests.exceptions.ConnectionError:
            checks.append((False, "Health dashboard not running"))
            self.warnings.append("Health dashboard not accessible. Run: make dev")
        except Exception as e:
            checks.append((False, f"Health dashboard error: {e}"))
            self.warnings.append(f"Health dashboard error: {e}")
        
        # Knowledge Base (if configured)
        kb_url = os.environ.get("KB_URL", "http://localhost:8000")
        try:
            response = requests.get(f"{kb_url}/health", timeout=2)
            if response.status_code == 200:
                checks.append((True, "Knowledge Base accessible ✓"))
            else:
                checks.append((False, f"Knowledge Base error: {response.status_code}"))
                self.warnings.append("Knowledge Base not healthy")
        except:
            checks.append((False, "Knowledge Base not accessible"))
            self.warnings.append(f"Knowledge Base not running at {kb_url}")
        
        return self._print_checks(checks)
    
    def check_performance(self) -> Tuple[int, int]:
        """Check performance settings"""
        checks = []
        
        # Cache directory
        cache_dir = self.project_root / "data" / "cache"
        if cache_dir.exists():
            checks.append((True, "Cache directory exists ✓"))
            
            # Check cache is writable
            test_file = cache_dir / ".test"
            try:
                test_file.touch()
                test_file.unlink()
                checks.append((True, "Cache directory writable ✓"))
            except:
                checks.append((False, "Cache directory not writable"))
                self.errors.append("Cannot write to cache directory")
        else:
            checks.append((False, "Cache directory missing"))
            self.warnings.append("Cache directory not found")
        
        # Check resource limits
        try:
            from ai_writing_flow.optimization.resource_manager import get_resource_manager
            rm = get_resource_manager()
            tier = rm.resource_tier
            
            if tier in ["medium", "high"]:
                checks.append((True, f"Resource tier: {tier} ✓"))
            else:
                checks.append((True, f"Resource tier: {tier} (low resources)"))
                self.warnings.append("System has limited resources")
                
        except:
            checks.append((False, "Resource manager not available"))
        
        return self._print_checks(checks)
    
    def check_integration(self) -> Tuple[int, int]:
        """Check integrations"""
        checks = []
        
        # Git setup
        if (self.project_root / ".git").exists():
            checks.append((True, "Git repository initialized ✓"))
            
            # Check git hooks
            hooks_dir = self.project_root / ".git" / "hooks"
            if (hooks_dir / "pre-commit").exists() or (hooks_dir / "pre-push").exists():
                checks.append((True, "Git hooks configured ✓"))
            else:
                checks.append((False, "Git hooks not configured"))
                self.warnings.append("Git hooks not set up. Run: make git-setup")
        else:
            checks.append((False, "Not a git repository"))
            self.warnings.append("Not in a git repository")
        
        # Pre-commit
        if (self.project_root / ".pre-commit-config.yaml").exists():
            checks.append((True, "Pre-commit configured ✓"))
        else:
            checks.append((False, "Pre-commit not configured"))
            self.warnings.append("Pre-commit not configured")
        
        # GitHub CLI (optional)
        if self._command_exists("gh"):
            checks.append((True, "GitHub CLI available ✓"))
        else:
            checks.append((True, "GitHub CLI not installed (optional)"))
        
        return self._print_checks(checks)
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True
            )
            return True
        except:
            return False
    
    def _print_checks(self, checks: List[Tuple[bool, str]]) -> Tuple[int, int]:
        """Print check results and return counts"""
        passed = 0
        for success, message in checks:
            if success:
                print(f"  ✅ {message}")
                passed += 1
            else:
                print(f"  ❌ {message}")
        
        return passed, len(checks)


def main():
    """Main entry point"""
    validator = EnvironmentValidator()
    success = validator.run_all_checks()
    
    # Generate validation report
    report_path = Path("validation_report.txt")
    with open(report_path, 'w') as f:
        f.write(f"Environment Validation Report\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'=' * 50}\n\n")
        
        if success:
            f.write("✅ VALIDATION PASSED\n")
        else:
            f.write("❌ VALIDATION FAILED\n")
        
        if validator.errors:
            f.write(f"\nErrors ({len(validator.errors)}):\n")
            for error in validator.errors:
                f.write(f"- {error}\n")
        
        if validator.warnings:
            f.write(f"\nWarnings ({len(validator.warnings)}):\n")
            for warning in validator.warnings:
                f.write(f"- {warning}\n")
    
    print(f"\n📄 Validation report saved to: {report_path}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()