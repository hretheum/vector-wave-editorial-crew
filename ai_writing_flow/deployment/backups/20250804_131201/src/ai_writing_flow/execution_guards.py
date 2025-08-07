"""
Execution Guards Implementation - Task 18.1, 18.2, 18.3

This module implements comprehensive guards for all flow methods including:
- Resource monitoring guards (CPU, memory)
- Execution time limits
- Method execution protection
"""

import logging
import time
import threading
import psutil
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone, timedelta
from functools import wraps

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.utils.loop_prevention import LoopPreventionSystem

logger = logging.getLogger(__name__)


class ResourceLimits:
    """Resource limit definitions"""
    
    def __init__(self):
        # CPU limits (percentage)
        self.max_cpu_percent: float = 80.0
        self.sustained_cpu_duration: int = 30  # seconds
        
        # Memory limits
        self.max_memory_percent: float = 85.0
        self.max_memory_mb: int = 2048
        
        # Execution time limits (seconds)
        self.method_timeout: int = 300  # 5 minutes per method
        self.total_flow_timeout: int = 1800  # 30 minutes total
        
        # Concurrency limits
        self.max_concurrent_methods: int = 1
        self.max_method_executions_per_minute: int = 10


class GuardViolation:
    """Guard violation data"""
    
    def __init__(self, guard_type: str, violation_type: str, message: str):
        self.guard_type = guard_type
        self.violation_type = violation_type
        self.message = message
        self.timestamp = datetime.now(timezone.utc)
        self.severity = "error"  # error, warning, critical


class ResourceMonitor:
    """Resource monitoring for guards - Task 18.2"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._cpu_violations: List[datetime] = []
        self._memory_violations: List[datetime] = []
        self._lock = threading.Lock()
    
    def start_monitoring(self) -> None:
        """Start resource monitoring"""
        with self._lock:
            if self._monitoring_active:
                return
            
            self._monitoring_active = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_resources,
                daemon=True
            )
            self._monitor_thread.start()
            logger.info("📊 Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring"""
        with self._lock:
            self._monitoring_active = False
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)
            logger.info("📊 Resource monitoring stopped")
    
    def _monitor_resources(self) -> None:
        """Monitor system resources continuously"""
        while self._monitoring_active:
            try:
                # Check CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > self.limits.max_cpu_percent:
                    with self._lock:
                        self._cpu_violations.append(datetime.now(timezone.utc))
                        # Keep only recent violations
                        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.limits.sustained_cpu_duration)
                        self._cpu_violations = [v for v in self._cpu_violations if v > cutoff]
                
                # Check memory usage
                memory = psutil.virtual_memory()
                memory_mb = (memory.used / 1024 / 1024)
                
                if (memory.percent > self.limits.max_memory_percent or 
                    memory_mb > self.limits.max_memory_mb):
                    with self._lock:
                        self._memory_violations.append(datetime.now(timezone.utc))
                        # Keep only recent violations
                        cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
                        self._memory_violations = [v for v in self._memory_violations if v > cutoff]
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"❌ Resource monitoring error: {str(e)}")
                time.sleep(5)  # Wait longer on error
    
    def check_cpu_violation(self) -> Optional[GuardViolation]:
        """Check for CPU usage violations"""
        with self._lock:
            if len(self._cpu_violations) >= self.limits.sustained_cpu_duration:
                return GuardViolation(
                    guard_type="resource_monitor",
                    violation_type="cpu_exceeded",
                    message=f"CPU usage exceeded {self.limits.max_cpu_percent}% for {self.limits.sustained_cpu_duration}s"
                )
        return None
    
    def check_memory_violation(self) -> Optional[GuardViolation]:
        """Check for memory usage violations"""
        with self._lock:
            if len(self._memory_violations) >= 3:  # 3 violations in 1 minute
                memory = psutil.virtual_memory()
                return GuardViolation(
                    guard_type="resource_monitor",
                    violation_type="memory_exceeded",
                    message=f"Memory usage exceeded limits: {memory.percent:.1f}%"
                )
        return None
    
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_mb": memory.used / 1024 / 1024,
                "cpu_violations": len(self._cpu_violations),
                "memory_violations": len(self._memory_violations)
            }
        except Exception as e:
            logger.error(f"❌ Failed to get resource usage: {str(e)}")
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_mb": 0.0,
                "cpu_violations": 0,
                "memory_violations": 0
            }


class ExecutionTimeGuard:
    """Execution time limit guard - Task 18.3"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self._method_start_times: Dict[str, datetime] = {}
        self._flow_start_time: Optional[datetime] = None
        self._lock = threading.Lock()
    
    def start_flow_timer(self) -> None:
        """Start flow execution timer"""
        with self._lock:
            self._flow_start_time = datetime.now(timezone.utc)
            logger.info("⏱️ Flow execution timer started")
    
    def start_method_timer(self, method_name: str) -> None:
        """Start method execution timer"""
        with self._lock:
            self._method_start_times[method_name] = datetime.now(timezone.utc)
            logger.debug(f"⏱️ Method timer started: {method_name}")
    
    def check_method_timeout(self, method_name: str) -> Optional[GuardViolation]:
        """Check if method execution has timed out"""
        with self._lock:
            start_time = self._method_start_times.get(method_name)
            if not start_time:
                return None
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed > self.limits.method_timeout:
                return GuardViolation(
                    guard_type="execution_time",
                    violation_type="method_timeout",
                    message=f"Method {method_name} exceeded {self.limits.method_timeout}s timeout"
                )
        return None
    
    def check_flow_timeout(self) -> Optional[GuardViolation]:
        """Check if total flow execution has timed out"""
        with self._lock:
            if not self._flow_start_time:
                return None
            
            elapsed = (datetime.now(timezone.utc) - self._flow_start_time).total_seconds()
            if elapsed > self.limits.total_flow_timeout:
                return GuardViolation(
                    guard_type="execution_time",
                    violation_type="flow_timeout",
                    message=f"Flow execution exceeded {self.limits.total_flow_timeout}s timeout"
                )
        return None
    
    def end_method_timer(self, method_name: str) -> float:
        """End method timer and return execution time"""
        with self._lock:
            start_time = self._method_start_times.pop(method_name, None)
            if start_time:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.debug(f"⏱️ Method {method_name} completed in {elapsed:.2f}s")
                return elapsed
        return 0.0
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get execution time status"""
        with self._lock:
            current_time = datetime.now(timezone.utc)
            
            flow_elapsed = 0.0
            if self._flow_start_time:
                flow_elapsed = (current_time - self._flow_start_time).total_seconds()
            
            method_times = {}
            for method_name, start_time in self._method_start_times.items():
                method_times[method_name] = (current_time - start_time).total_seconds()
            
            return {
                "flow_elapsed_seconds": flow_elapsed,
                "flow_timeout_seconds": self.limits.total_flow_timeout,
                "active_methods": method_times,
                "method_timeout_seconds": self.limits.method_timeout
            }


class FlowExecutionGuards:
    """
    Comprehensive execution guards for all flow methods - Task 18.1
    
    Features:
    - Resource monitoring (CPU, memory) - Task 18.2
    - Execution time limits - Task 18.3
    - Method execution protection
    - Integration with loop prevention
    """
    
    def __init__(self, loop_prevention: LoopPreventionSystem):
        self.limits = ResourceLimits()
        self.resource_monitor = ResourceMonitor(self.limits)
        self.time_guard = ExecutionTimeGuard(self.limits)
        self.loop_prevention = loop_prevention
        
        # Guard state
        self._active_methods: Dict[str, datetime] = {}
        self._execution_counts: Dict[str, int] = {}
        self._violations: List[GuardViolation] = []
        self._lock = threading.Lock()
        
        # Start monitoring
        self.resource_monitor.start_monitoring()
        logger.info("🛡️ Flow execution guards initialized")
    
    def method_guard(self, method_name: str):
        """
        Decorator for protecting method execution - Task 18.1
        
        Args:
            method_name: Name of the method being protected
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self._execute_with_guards(method_name, func, *args, **kwargs)
            return wrapper
        return decorator
    
    def _execute_with_guards(self, method_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute method with all guards active - Task 18.1
        
        Args:
            method_name: Name of the method
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            RuntimeError: If guard violations prevent execution
        """
        
        logger.debug(f"🛡️ Executing {method_name} with guards")
        
        # Pre-execution checks
        violations = self._check_all_guards(method_name)
        if violations:
            self._handle_violations(violations)
            raise RuntimeError(f"Guard violations prevent execution of {method_name}: {[v.message for v in violations]}")
        
        # Start execution tracking
        self._start_method_execution(method_name)
        
        try:
            # Execute with timeout monitoring
            result = self._execute_with_timeout_monitoring(method_name, func, *args, **kwargs)
            
            # Post-execution success
            self._end_method_execution(method_name, success=True)
            return result
            
        except Exception as e:
            # Post-execution failure
            self._end_method_execution(method_name, success=False, error=str(e))
            raise
    
    def _execute_with_timeout_monitoring(self, method_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout monitoring"""
        
        # Start method timer
        self.time_guard.start_method_timer(method_name)
        
        try:
            # Execute in thread to allow timeout checking
            result_container = {}
            exception_container = {}
            
            def target():
                try:
                    result_container['result'] = func(*args, **kwargs)
                except Exception as e:
                    exception_container['exception'] = e
            
            thread = threading.Thread(target=target)
            thread.start()
            
            # Monitor execution
            while thread.is_alive():
                thread.join(timeout=1.0)  # Check every second
                
                # Check for timeouts
                timeout_violation = self.time_guard.check_method_timeout(method_name)
                if timeout_violation:
                    self._record_violation(timeout_violation)
                    # Try to interrupt (thread may not be interruptible)
                    logger.error(f"🚨 Method {method_name} timed out")
                    raise RuntimeError(f"Method {method_name} exceeded timeout")
                
                # Check resource violations during execution
                resource_violations = [
                    self.resource_monitor.check_cpu_violation(),
                    self.resource_monitor.check_memory_violation()
                ]
                resource_violations = [v for v in resource_violations if v is not None]
                
                if resource_violations:
                    for violation in resource_violations:
                        self._record_violation(violation)
                    logger.error(f"🚨 Resource violations during {method_name}: {[v.message for v in resource_violations]}")
                    raise RuntimeError(f"Resource violations during {method_name}")
            
            # Get result or exception
            if 'exception' in exception_container:
                raise exception_container['exception']
            
            return result_container.get('result')
            
        finally:
            execution_time = self.time_guard.end_method_timer(method_name)
            logger.debug(f"🛡️ Method {method_name} guarded execution completed in {execution_time:.2f}s")
    
    def _check_all_guards(self, method_name: str) -> List[GuardViolation]:
        """Check all guard conditions before execution"""
        violations = []
        
        # Check concurrency limits
        with self._lock:
            if len(self._active_methods) >= self.limits.max_concurrent_methods:
                violations.append(GuardViolation(
                    guard_type="concurrency",
                    violation_type="max_concurrent_exceeded",
                    message=f"Max concurrent methods ({self.limits.max_concurrent_methods}) exceeded"
                ))
            
            # Check execution frequency
            current_count = self._execution_counts.get(method_name, 0)
            if current_count >= self.limits.max_method_executions_per_minute:
                violations.append(GuardViolation(
                    guard_type="frequency",
                    violation_type="execution_rate_exceeded", 
                    message=f"Method {method_name} executed too frequently"
                ))
        
        # Check resource violations
        cpu_violation = self.resource_monitor.check_cpu_violation()
        if cpu_violation:
            violations.append(cpu_violation)
        
        memory_violation = self.resource_monitor.check_memory_violation()
        if memory_violation:
            violations.append(memory_violation)
        
        # Check execution time violations
        flow_timeout = self.time_guard.check_flow_timeout()
        if flow_timeout:
            violations.append(flow_timeout)
        
        # Check loop prevention
        if self.loop_prevention.should_stop_execution():
            violations.append(GuardViolation(
                guard_type="loop_prevention", 
                violation_type="infinite_loop_detected",
                message="Infinite loop or excessive execution detected"
            ))
        
        return violations
    
    def _start_method_execution(self, method_name: str) -> None:
        """Start tracking method execution"""
        with self._lock:
            self._active_methods[method_name] = datetime.now(timezone.utc)
            self._execution_counts[method_name] = self._execution_counts.get(method_name, 0) + 1
            
            # Clean old execution counts (sliding window)
            # This is simplified - in production, use proper sliding window
            if self._execution_counts[method_name] > self.limits.max_method_executions_per_minute * 2:
                self._execution_counts[method_name] = self.limits.max_method_executions_per_minute
        
        # Track in loop prevention system
        self.loop_prevention.track_execution(method_name)
    
    def _end_method_execution(self, method_name: str, success: bool, error: Optional[str] = None) -> None:
        """End tracking method execution"""
        with self._lock:
            if method_name in self._active_methods:
                execution_time = (datetime.now(timezone.utc) - self._active_methods[method_name]).total_seconds()
                del self._active_methods[method_name]
                logger.debug(f"🛡️ Method {method_name} execution ended: success={success}, time={execution_time:.2f}s")
    
    def _record_violation(self, violation: GuardViolation) -> None:
        """Record guard violation"""
        with self._lock:
            self._violations.append(violation)
            # Keep only recent violations
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            self._violations = [v for v in self._violations if v.timestamp > cutoff]
        
        logger.warning(f"⚠️ Guard violation recorded: {violation.violation_type} - {violation.message}")
    
    def _handle_violations(self, violations: List[GuardViolation]) -> None:
        """Handle guard violations"""
        for violation in violations:
            self._record_violation(violation)
            
            # Log based on severity
            if violation.severity == "critical":
                logger.critical(f"🚨 CRITICAL guard violation: {violation.violation_type} - {violation.message}")
            elif violation.severity == "error":
                logger.error(f"❌ Guard violation: {violation.violation_type} - {violation.message}")
            else:
                logger.warning(f"⚠️ Guard warning: {violation.violation_type} - {violation.message}")
    
    def start_flow_execution(self) -> None:
        """Start flow execution with guards"""
        self.time_guard.start_flow_timer()
        logger.info("🛡️ Flow execution started with guards active")
    
    def stop_flow_execution(self) -> None:
        """Stop flow execution and cleanup guards"""
        self.resource_monitor.stop_monitoring()
        logger.info("🛡️ Flow execution stopped, guards deactivated")
    
    def get_guard_status(self) -> Dict[str, Any]:
        """Get comprehensive guard status"""
        with self._lock:
            resource_usage = self.resource_monitor.get_current_usage()
            time_status = self.time_guard.get_execution_status()
            
            return {
                "resource_usage": resource_usage,
                "execution_times": time_status,
                "active_methods": list(self._active_methods.keys()),
                "execution_counts": self._execution_counts.copy(),
                "recent_violations": [
                    {
                        "guard_type": v.guard_type,
                        "violation_type": v.violation_type,
                        "message": v.message,
                        "timestamp": v.timestamp.isoformat(),
                        "severity": v.severity
                    }
                    for v in self._violations[-10:]  # Last 10 violations
                ],
                "limits": {
                    "max_cpu_percent": self.limits.max_cpu_percent,
                    "max_memory_percent": self.limits.max_memory_percent,
                    "method_timeout": self.limits.method_timeout,
                    "total_flow_timeout": self.limits.total_flow_timeout,
                    "max_concurrent_methods": self.limits.max_concurrent_methods
                }
            }
    
    def emergency_stop(self) -> None:
        """Emergency stop all guarded operations"""
        logger.critical("🚨 EMERGENCY STOP: All guarded operations terminated")
        
        with self._lock:
            self._active_methods.clear()
            self._execution_counts.clear()
        
        self.resource_monitor.stop_monitoring()
        
        # Record emergency stop
        violation = GuardViolation(
            guard_type="emergency", 
            violation_type="emergency_stop",
            message="Emergency stop activated"
        )
        violation.severity = "critical"
        self._record_violation(violation)
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.resource_monitor.stop_monitoring()
        except:
            pass


# Export main classes
__all__ = [
    "FlowExecutionGuards",
    "ResourceLimits",
    "GuardViolation",
    "ResourceMonitor",
    "ExecutionTimeGuard"
]