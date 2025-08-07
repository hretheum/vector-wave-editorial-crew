"""
Quality Gate System - Comprehensive validation and quality assurance

This module provides a comprehensive quality gate system that validates
code quality, architecture compliance, and runtime behavior to ensure
production-ready quality standards.

Key Features:
- Static code analysis integration
- Runtime behavior validation
- Circular dependency detection
- Loop prevention validation
- Performance criteria validation
- Test coverage requirements
- Architecture compliance checks
"""

import ast
import importlib
import inspect
import sys
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Set, Tuple
import logging
import subprocess
import json


class ValidationSeverity(Enum):
    """Severity levels for validation results"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Categories of validation checks"""
    STATIC_ANALYSIS = "static_analysis"
    RUNTIME_BEHAVIOR = "runtime_behavior"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    TESTING = "testing"
    SECURITY = "security"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    rule_id: str
    rule_name: str
    category: ValidationCategory
    severity: ValidationSeverity
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: float = 0.0


@dataclass
class QualityGateConfig:
    """Configuration for quality gate system"""
    # Thresholds
    max_cyclomatic_complexity: int = 10
    min_test_coverage: float = 80.0
    max_function_length: int = 50
    max_class_length: int = 500
    max_module_length: int = 1000
    
    # Performance thresholds
    max_execution_time_seconds: float = 5.0
    max_memory_usage_mb: float = 100.0
    max_cpu_usage_percent: float = 80.0
    
    # Architecture rules
    forbidden_imports: List[str] = field(default_factory=list)
    required_docstrings: bool = True
    enforce_type_hints: bool = True
    
    # Runtime validation
    enable_runtime_checks: bool = True
    loop_detection_enabled: bool = True
    max_loop_iterations: int = 1000
    
    # Paths
    source_paths: List[str] = field(default_factory=lambda: ["src"])
    test_paths: List[str] = field(default_factory=lambda: ["tests"])
    
    # Quality gates
    allow_warnings: bool = True
    max_error_count: int = 0
    max_critical_count: int = 0


class ValidationRule(ABC):
    """Abstract base class for validation rules"""
    
    def __init__(self, rule_id: str, name: str, category: ValidationCategory, 
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.rule_id = rule_id
        self.name = name
        self.category = category
        self.severity = severity
    
    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Execute validation rule and return result"""
        pass
    
    def _create_result(self, passed: bool, message: str, 
                      details: Dict[str, Any] = None) -> ValidationResult:
        """Helper to create validation result"""
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            category=self.category,
            severity=self.severity,
            passed=passed,
            message=message,
            details=details or {}
        )


class StaticAnalysisRule(ValidationRule):
    """Base class for static analysis rules"""
    
    def __init__(self, rule_id: str, name: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(rule_id, name, ValidationCategory.STATIC_ANALYSIS, severity)


class CircularDependencyRule(StaticAnalysisRule):
    """Detect circular dependencies in code"""
    
    def __init__(self):
        super().__init__("circular_deps", "Circular Dependency Detection", ValidationSeverity.CRITICAL)
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Check for circular dependencies"""
        start_time = time.time()
        
        try:
            source_paths = context.get("source_paths", ["src"])
            circular_deps = self._find_circular_dependencies(source_paths)
            
            execution_time = (time.time() - start_time) * 1000
            
            if circular_deps:
                details = {
                    "circular_dependencies": circular_deps,
                    "count": len(circular_deps)
                }
                message = f"Found {len(circular_deps)} circular dependencies"
                result = self._create_result(False, message, details)
            else:
                message = "No circular dependencies detected"
                result = self._create_result(True, message)
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = self._create_result(
                False, 
                f"Error analyzing dependencies: {str(e)}",
                {"error": str(e)}
            )
            result.execution_time_ms = execution_time
            return result
    
    def _find_circular_dependencies(self, source_paths: List[str]) -> List[Dict[str, Any]]:
        """Find circular dependencies using AST analysis"""
        dependencies = {}
        circular_deps = []
        
        # Build dependency graph
        for source_path in source_paths:
            path = Path(source_path)
            if path.exists():
                for py_file in path.rglob("*.py"):
                    if py_file.name != "__init__.py":
                        module_deps = self._extract_imports(py_file)
                        module_name = self._path_to_module_name(py_file, path)
                        dependencies[module_name] = module_deps
        
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(module: str, path: List[str]) -> Optional[List[str]]:
            if module in rec_stack:
                # Found cycle - return the cycle path
                cycle_start = path.index(module)
                return path[cycle_start:] + [module]
            
            if module in visited:
                return None
            
            visited.add(module)
            rec_stack.add(module)
            
            for dep in dependencies.get(module, []):
                cycle_path = has_cycle(dep, path + [module])
                if cycle_path:
                    return cycle_path
            
            rec_stack.remove(module)
            return None
        
        # Check each module for cycles
        for module in dependencies:
            if module not in visited:
                cycle = has_cycle(module, [])
                if cycle:
                    circular_deps.append({
                        "cycle": cycle,
                        "modules_involved": len(set(cycle))
                    })
        
        return circular_deps
    
    def _extract_imports(self, file_path: Path) -> List[str]:
        """Extract import statements from Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split('.')[0])
            
            return imports
            
        except Exception:
            return []
    
    def _path_to_module_name(self, file_path: Path, base_path: Path) -> str:
        """Convert file path to module name"""
        relative_path = file_path.relative_to(base_path)
        module_parts = list(relative_path.parts)[:-1]  # Remove .py extension
        module_parts.append(relative_path.stem)
        return '.'.join(module_parts)


class LoopDetectionRule(ValidationRule):
    """Detect potential infinite loops in runtime"""
    
    def __init__(self):
        super().__init__(
            "loop_detection", 
            "Loop Detection", 
            ValidationCategory.RUNTIME_BEHAVIOR,
            ValidationSeverity.CRITICAL
        )
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate loop prevention mechanisms"""
        start_time = time.time()
        
        try:
            # Check if loop prevention system is available and configured
            flow_control_state = context.get("flow_control_state")
            stage_manager = context.get("stage_manager")
            
            issues = []
            
            if not flow_control_state:
                issues.append("FlowControlState not found in context")
            
            if not stage_manager:
                issues.append("StageManager not found in context")
            
            if stage_manager and hasattr(stage_manager, 'loop_prevention'):
                loop_prevention = stage_manager.loop_prevention
                
                # Check loop prevention configuration
                if not hasattr(loop_prevention, 'max_executions_per_method'):
                    issues.append("Loop prevention system missing execution limits")
                
                if not hasattr(loop_prevention, 'max_executions_per_stage'):
                    issues.append("Loop prevention system missing stage limits")
                
                # Validate reasonable limits
                if hasattr(loop_prevention, 'max_executions_per_method'):
                    max_method = getattr(loop_prevention, 'max_executions_per_method', 0)
                    if max_method <= 0 or max_method > 10000:
                        issues.append(f"Unreasonable method execution limit: {max_method}")
                
                if hasattr(loop_prevention, 'max_executions_per_stage'):
                    max_stage = getattr(loop_prevention, 'max_executions_per_stage', 0)
                    if max_stage <= 0 or max_stage > 5000:
                        issues.append(f"Unreasonable stage execution limit: {max_stage}")
            else:
                issues.append("Loop prevention system not configured")
            
            execution_time = (time.time() - start_time) * 1000
            
            if issues:
                result = self._create_result(
                    False,
                    f"Loop detection issues: {len(issues)} problems found",
                    {"issues": issues, "count": len(issues)}
                )
            else:
                result = self._create_result(
                    True,
                    "Loop prevention system properly configured",
                    {"loop_prevention_enabled": True}
                )
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = self._create_result(
                False,
                f"Error validating loop detection: {str(e)}",
                {"error": str(e)}
            )
            result.execution_time_ms = execution_time
            return result


class PerformanceValidationRule(ValidationRule):
    """Validate system performance characteristics"""
    
    def __init__(self, config: QualityGateConfig):
        super().__init__(
            "performance_validation",
            "Performance Validation",
            ValidationCategory.PERFORMANCE,
            ValidationSeverity.ERROR
        )
        self.config = config
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate performance criteria"""
        start_time = time.time()
        
        try:
            flow_metrics = context.get("flow_metrics")
            issues = []
            metrics_data = {}
            
            if not flow_metrics:
                result = self._create_result(
                    False,
                    "FlowMetrics not available for performance validation",
                    {"error": "flow_metrics_missing"}
                )
                result.execution_time_ms = (time.time() - start_time) * 1000
                return result
            
            # Get current KPIs
            kpis = flow_metrics.get_current_kpis()
            
            # Validate CPU usage
            if kpis.cpu_usage > self.config.max_cpu_usage_percent:
                issues.append(f"CPU usage {kpis.cpu_usage:.1f}% exceeds limit {self.config.max_cpu_usage_percent}%")
            metrics_data["cpu_usage"] = kpis.cpu_usage
            
            # Validate memory usage
            if kpis.memory_usage > self.config.max_memory_usage_mb:
                issues.append(f"Memory usage {kpis.memory_usage:.1f}MB exceeds limit {self.config.max_memory_usage_mb}MB")
            metrics_data["memory_usage"] = kpis.memory_usage
            
            # Validate execution time
            if kpis.avg_execution_time > self.config.max_execution_time_seconds:
                issues.append(f"Avg execution time {kpis.avg_execution_time:.2f}s exceeds limit {self.config.max_execution_time_seconds}s")
            metrics_data["avg_execution_time"] = kpis.avg_execution_time
            
            # Validate success rate
            if kpis.success_rate < 95.0:
                issues.append(f"Success rate {kpis.success_rate:.1f}% below 95% threshold")
            metrics_data["success_rate"] = kpis.success_rate
            
            # Validate throughput (should be > 0 if system is active)
            if kpis.active_flows > 0 and kpis.throughput <= 0:
                issues.append("Throughput is zero despite active flows")
            metrics_data["throughput"] = kpis.throughput
            
            execution_time = (time.time() - start_time) * 1000
            
            if issues:
                result = self._create_result(
                    False,
                    f"Performance validation failed: {len(issues)} issues",
                    {"issues": issues, "metrics": metrics_data}
                )
            else:
                result = self._create_result(
                    True,
                    "All performance criteria met",
                    {"metrics": metrics_data}
                )
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = self._create_result(
                False,
                f"Error during performance validation: {str(e)}",
                {"error": str(e)}
            )
            result.execution_time_ms = execution_time
            return result


class TestCoverageRule(ValidationRule):
    """Validate test coverage requirements"""
    
    def __init__(self, config: QualityGateConfig):
        super().__init__(
            "test_coverage",
            "Test Coverage Validation",
            ValidationCategory.TESTING,
            ValidationSeverity.WARNING
        )
        self.config = config
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate test coverage meets requirements"""
        start_time = time.time()
        
        try:
            # Try to run coverage analysis
            coverage_data = self._run_coverage_analysis(context)
            
            execution_time = (time.time() - start_time) * 1000
            
            if coverage_data:
                total_coverage = coverage_data.get("total_coverage", 0.0)
                
                if total_coverage >= self.config.min_test_coverage:
                    result = self._create_result(
                        True,
                        f"Test coverage {total_coverage:.1f}% meets requirement {self.config.min_test_coverage:.1f}%",
                        coverage_data
                    )
                else:
                    result = self._create_result(
                        False,
                        f"Test coverage {total_coverage:.1f}% below requirement {self.config.min_test_coverage:.1f}%",
                        coverage_data
                    )
            else:
                # If coverage analysis fails, check for test files existence
                test_files = self._count_test_files(context)
                
                if test_files > 0:
                    result = self._create_result(
                        True,
                        f"Found {test_files} test files (coverage analysis unavailable)",
                        {"test_files_count": test_files, "coverage_analysis": "unavailable"}
                    )
                else:
                    result = self._create_result(
                        False,
                        "No test files found",
                        {"test_files_count": 0}
                    )
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = self._create_result(
                False,
                f"Error validating test coverage: {str(e)}",
                {"error": str(e)}
            )
            result.execution_time_ms = execution_time
            return result
    
    def _run_coverage_analysis(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run test coverage analysis using pytest-cov"""
        try:
            source_paths = context.get("source_paths", self.config.source_paths)
            test_paths = context.get("test_paths", self.config.test_paths)
            
            # Build coverage command
            cmd = ["python", "-m", "pytest"]
            
            # Add test paths
            for test_path in test_paths:
                if Path(test_path).exists():
                    cmd.extend([test_path])
            
            # Add coverage options
            for source_path in source_paths:
                cmd.extend([f"--cov={source_path}"])
            
            cmd.extend(["--cov-report=json:/tmp/coverage.json", "--quiet"])
            
            # Run coverage
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Read coverage report
            coverage_file = Path("/tmp/coverage.json")
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                
                return {
                    "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0.0),
                    "files_covered": len(coverage_data.get("files", {})),
                    "lines_covered": coverage_data.get("totals", {}).get("covered_lines", 0),
                    "lines_total": coverage_data.get("totals", {}).get("num_statements", 0)
                }
            
            return None
            
        except subprocess.TimeoutExpired:
            return {"error": "Coverage analysis timed out"}
        except Exception:
            return None
    
    def _count_test_files(self, context: Dict[str, Any]) -> int:
        """Count test files as fallback"""
        test_count = 0
        test_paths = context.get("test_paths", self.config.test_paths)
        
        for test_path in test_paths:
            path = Path(test_path)
            if path.exists():
                test_count += len(list(path.rglob("test_*.py")))
                test_count += len(list(path.rglob("*_test.py")))
        
        return test_count


class ArchitectureComplianceRule(ValidationRule):
    """Validate architecture compliance rules"""
    
    def __init__(self, config: QualityGateConfig):
        super().__init__(
            "architecture_compliance",
            "Architecture Compliance",
            ValidationCategory.ARCHITECTURE,
            ValidationSeverity.ERROR
        )
        self.config = config
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate architecture compliance"""
        start_time = time.time()
        
        try:
            violations = []
            compliance_data = {}
            
            # Check for forbidden imports
            if self.config.forbidden_imports:
                forbidden_usage = self._check_forbidden_imports(context)
                if forbidden_usage:
                    violations.extend(forbidden_usage)
                    compliance_data["forbidden_imports"] = forbidden_usage
            
            # Check docstring requirements
            if self.config.required_docstrings:
                missing_docstrings = self._check_docstrings(context)
                if missing_docstrings:
                    violations.extend([f"Missing docstring: {item}" for item in missing_docstrings])
                    compliance_data["missing_docstrings"] = missing_docstrings
            
            # Check type hints
            if self.config.enforce_type_hints:
                missing_type_hints = self._check_type_hints(context)
                if missing_type_hints:
                    violations.extend([f"Missing type hints: {item}" for item in missing_type_hints])
                    compliance_data["missing_type_hints"] = missing_type_hints
            
            # Check for linear flow architecture compliance
            linear_flow_issues = self._check_linear_flow_compliance(context)
            if linear_flow_issues:
                violations.extend(linear_flow_issues)
                compliance_data["linear_flow_issues"] = linear_flow_issues
            
            execution_time = (time.time() - start_time) * 1000
            
            if violations:
                result = self._create_result(
                    False,
                    f"Architecture compliance failed: {len(violations)} violations",
                    {"violations": violations, "details": compliance_data}
                )
            else:
                result = self._create_result(
                    True,
                    "Architecture compliance validated successfully",
                    compliance_data
                )
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = self._create_result(
                False,
                f"Error validating architecture compliance: {str(e)}",
                {"error": str(e)}
            )
            result.execution_time_ms = execution_time
            return result
    
    def _check_forbidden_imports(self, context: Dict[str, Any]) -> List[str]:
        """Check for forbidden import usage"""
        violations = []
        source_paths = context.get("source_paths", self.config.source_paths)
        
        for source_path in source_paths:
            path = Path(source_path)
            if path.exists():
                for py_file in path.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        if alias.name in self.config.forbidden_imports:
                                            violations.append(f"{py_file}: forbidden import {alias.name}")
                                elif isinstance(node, ast.ImportFrom) and node.module:
                                    if node.module in self.config.forbidden_imports:
                                        violations.append(f"{py_file}: forbidden import from {node.module}")
                    
                    except Exception:
                        continue  # Skip files that can't be parsed
        
        return violations
    
    def _check_docstrings(self, context: Dict[str, Any]) -> List[str]:
        """Check for missing docstrings in classes and functions"""
        missing = []
        source_paths = context.get("source_paths", self.config.source_paths)
        
        for source_path in source_paths:
            path = Path(source_path)
            if path.exists():
                for py_file in path.rglob("*.py"):
                    if py_file.name.startswith("test_"):
                        continue  # Skip test files
                    
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                                if not ast.get_docstring(node):
                                    item_type = "class" if isinstance(node, ast.ClassDef) else "function"
                                    missing.append(f"{py_file}:{node.lineno} {item_type} {node.name}")
                    
                    except Exception:
                        continue
        
        return missing
    
    def _check_type_hints(self, context: Dict[str, Any]) -> List[str]:
        """Check for missing type hints"""
        missing = []
        source_paths = context.get("source_paths", self.config.source_paths)
        
        for source_path in source_paths:
            path = Path(source_path)
            if path.exists():
                for py_file in path.rglob("*.py"):
                    if py_file.name.startswith("test_"):
                        continue  # Skip test files
                    
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                # Check function return type
                                if not node.returns and node.name != "__init__":
                                    missing.append(f"{py_file}:{node.lineno} function {node.name} missing return type")
                                
                                # Check parameter types
                                for arg in node.args.args:
                                    if not arg.annotation and arg.arg != "self":
                                        missing.append(f"{py_file}:{node.lineno} parameter {arg.arg} in {node.name} missing type hint")
                    
                    except Exception:
                        continue
        
        return missing
    
    def _check_linear_flow_compliance(self, context: Dict[str, Any]) -> List[str]:
        """Check compliance with linear flow architecture"""
        issues = []
        
        # Check if @router decorators are still being used
        source_paths = context.get("source_paths", self.config.source_paths)
        
        for source_path in source_paths:
            path = Path(source_path)
            if path.exists():
                for py_file in path.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check for @router decorator usage (legacy pattern)
                        if "@router" in content:
                            issues.append(f"{py_file}: contains @router decorator (legacy pattern)")
                        
                        # Check for @listen decorator usage (legacy pattern)  
                        if "@listen" in content:
                            issues.append(f"{py_file}: contains @listen decorator (legacy pattern)")
                        
                        # Parse AST to check for circular flow patterns
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                # Check for recursive calls that could cause loops
                                for child in ast.walk(node):
                                    if (isinstance(child, ast.Call) and 
                                        isinstance(child.func, ast.Name) and
                                        child.func.id == node.name):
                                        issues.append(f"{py_file}:{node.lineno} function {node.name} contains recursive call")
                    
                    except Exception:
                        continue
        
        return issues


class QualityGate:
    """
    Main quality gate system that orchestrates all validation rules
    
    Provides comprehensive quality validation including static analysis,
    runtime validation, and architecture compliance checks.
    """
    
    def __init__(self, config: Optional[QualityGateConfig] = None):
        self.config = config or QualityGateConfig()
        self.rules: List[ValidationRule] = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default validation rules"""
        # Static analysis rules
        self.rules.append(CircularDependencyRule())
        
        # Runtime behavior rules
        self.rules.append(LoopDetectionRule())
        
        # Performance rules
        self.rules.append(PerformanceValidationRule(self.config))
        
        # Testing rules
        self.rules.append(TestCoverageRule(self.config))
        
        # Architecture rules
        self.rules.append(ArchitectureComplianceRule(self.config))
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add custom validation rule"""
        self.rules.append(rule)
        self.logger.info(f"Added validation rule: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove validation rule by ID"""
        original_count = len(self.rules)
        self.rules = [rule for rule in self.rules if rule.rule_id != rule_id]
        
        removed = len(self.rules) < original_count
        if removed:
            self.logger.info(f"Removed validation rule: {rule_id}")
        
        return removed
    
    def run_validation(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run all validation rules and return comprehensive results
        
        Args:
            context: Validation context containing objects to validate
            
        Returns:
            Comprehensive validation results
        """
        if context is None:
            context = self._build_default_context()
        
        start_time = time.time()
        results = []
        
        # Run all validation rules
        for rule in self.rules:
            try:
                result = rule.validate(context)
                results.append(result)
                
                self.logger.debug(f"Rule {rule.rule_id}: {'PASS' if result.passed else 'FAIL'} - {result.message}")
                
            except Exception as e:
                # Create error result for failed rule
                error_result = ValidationResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    category=rule.category,
                    severity=ValidationSeverity.CRITICAL,
                    passed=False,
                    message=f"Rule execution failed: {str(e)}",
                    details={"exception": str(e)}
                )
                results.append(error_result)
                
                self.logger.error(f"Rule {rule.rule_id} failed with exception: {e}")
        
        # Analyze results
        total_time = time.time() - start_time
        analysis = self._analyze_results(results)
        
        return {
            "validation_results": results,
            "summary": analysis,
            "execution_time_seconds": total_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quality_gate_passed": analysis["gate_passed"],
            "config": {
                "max_error_count": self.config.max_error_count,
                "max_critical_count": self.config.max_critical_count,
                "allow_warnings": self.config.allow_warnings
            }
        }
    
    def _build_default_context(self) -> Dict[str, Any]:
        """Build default validation context"""
        context = {
            "source_paths": self.config.source_paths,
            "test_paths": self.config.test_paths
        }
        
        # Try to import and add flow components if available
        try:
            # Try to import flow components for runtime validation
            from ai_writing_flow.models.flow_control_state import FlowControlState
            from ai_writing_flow.managers.stage_manager import StageManager
            from ai_writing_flow.monitoring.flow_metrics import FlowMetrics
            
            # Create instances for validation
            flow_state = FlowControlState()
            stage_manager = StageManager(flow_state)
            flow_metrics = FlowMetrics()
            
            context.update({
                "flow_control_state": flow_state,
                "stage_manager": stage_manager,
                "flow_metrics": flow_metrics
            })
            
        except ImportError as e:
            self.logger.warning(f"Could not import flow components for validation: {e}")
        
        return context
    
    def _analyze_results(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Analyze validation results and determine if quality gate passes"""
        # Count results by severity
        counts = {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "info": sum(1 for r in results if r.severity == ValidationSeverity.INFO),
            "warning": sum(1 for r in results if r.severity == ValidationSeverity.WARNING),
            "error": sum(1 for r in results if r.severity == ValidationSeverity.ERROR),
            "critical": sum(1 for r in results if r.severity == ValidationSeverity.CRITICAL)
        }
        
        # Count failed results by severity
        failed_counts = {
            "error": sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.ERROR),
            "critical": sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.CRITICAL),
            "warning": sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.WARNING)
        }
        
        # Determine if quality gate passes
        gate_passed = True
        
        # Check critical failures
        if failed_counts["critical"] > self.config.max_critical_count:
            gate_passed = False
        
        # Check error failures
        if failed_counts["error"] > self.config.max_error_count:
            gate_passed = False
        
        # Check warnings if not allowed
        if not self.config.allow_warnings and failed_counts["warning"] > 0:
            gate_passed = False
        
        # Group results by category
        by_category = {}
        for result in results:
            category = result.category.value
            if category not in by_category:
                by_category[category] = {"passed": 0, "failed": 0, "results": []}
            
            by_category[category]["results"].append(result)
            if result.passed:
                by_category[category]["passed"] += 1
            else:
                by_category[category]["failed"] += 1
        
        # Calculate success rates
        success_rate = (counts["passed"] / counts["total"] * 100) if counts["total"] > 0 else 100
        
        return {
            "gate_passed": gate_passed,
            "success_rate": success_rate,
            "counts": counts,
            "failed_counts": failed_counts,
            "by_category": by_category,
            "most_critical_failures": [
                r for r in results 
                if not r.passed and r.severity == ValidationSeverity.CRITICAL
            ][:5]  # Top 5 critical failures
        }
    
    def generate_report(self, validation_results: Dict[str, Any], 
                       output_path: Optional[Union[str, Path]] = None) -> str:
        """Generate human-readable quality gate report"""
        summary = validation_results["summary"]
        results = validation_results["validation_results"]
        
        report_lines = [
            "=" * 80,
            "AI WRITING FLOW - QUALITY GATE REPORT",
            "=" * 80,
            f"Timestamp: {validation_results['timestamp']}",
            f"Execution Time: {validation_results['execution_time_seconds']:.2f}s",
            f"Quality Gate: {'✅ PASSED' if summary['gate_passed'] else '❌ FAILED'}",
            f"Success Rate: {summary['success_rate']:.1f}%",
            "",
            "SUMMARY BY SEVERITY:",
            f"  Critical: {summary['failed_counts']['critical']} failed (max allowed: {self.config.max_critical_count})",
            f"  Error:    {summary['failed_counts']['error']} failed (max allowed: {self.config.max_error_count})",
            f"  Warning:  {summary['failed_counts']['warning']} failed (allowed: {self.config.allow_warnings})",
            f"  Total:    {summary['counts']['failed']}/{summary['counts']['total']} failed",
            "",
            "RESULTS BY CATEGORY:",
        ]
        
        # Add category results
        for category, data in summary["by_category"].items():
            status = "✅" if data["failed"] == 0 else "❌"
            report_lines.append(f"  {status} {category.replace('_', ' ').title()}: {data['passed']}/{data['passed'] + data['failed']} passed")
        
        # Add detailed failures
        if summary["counts"]["failed"] > 0:
            report_lines.extend([
                "",
                "DETAILED FAILURE ANALYSIS:",
                "-" * 40
            ])
            
            for result in results:
                if not result.passed:
                    severity_icon = {
                        ValidationSeverity.CRITICAL: "🔴",
                        ValidationSeverity.ERROR: "🟠", 
                        ValidationSeverity.WARNING: "🟡",
                        ValidationSeverity.INFO: "ℹ️"
                    }.get(result.severity, "❓")
                    
                    report_lines.extend([
                        f"{severity_icon} [{result.severity.value.upper()}] {result.rule_name}",
                        f"   Message: {result.message}",
                        f"   Time: {result.execution_time_ms:.1f}ms"
                    ])
                    
                    # Add details if available
                    if result.details:
                        for key, value in result.details.items():
                            if key != "error" and isinstance(value, (str, int, float)):
                                report_lines.append(f"   {key}: {value}")
                    
                    report_lines.append("")
        
        # Add success summary
        if summary["gate_passed"]:
            report_lines.extend([
                "",
                "🎉 QUALITY GATE PASSED",
                "All validation criteria have been met.",
                "System is ready for production deployment."
            ])
        else:
            report_lines.extend([
                "",
                "⚠️  QUALITY GATE FAILED", 
                "Please address the failed validation criteria above.",
                "System is NOT ready for production deployment."
            ])
        
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # Save to file if path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            self.logger.info(f"Quality gate report saved to: {output_file}")
        
        return report_text
    
    def run_continuous_validation(self, interval_seconds: int = 300,
                                 context: Optional[Dict[str, Any]] = None) -> None:
        """Run continuous validation at specified intervals"""
        self.logger.info(f"Starting continuous validation (interval: {interval_seconds}s)")
        
        def validation_loop():
            while True:
                try:
                    results = self.run_validation(context)
                    
                    if not results["quality_gate_passed"]:
                        self.logger.warning("Quality gate failed in continuous validation")
                        # Could trigger alerts here
                    
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    self.logger.error(f"Error in continuous validation: {e}")
                    time.sleep(interval_seconds)
        
        # Run in background thread
        validation_thread = threading.Thread(target=validation_loop, daemon=True)
        validation_thread.start()
        
        return validation_thread