"""
Developer-Friendly Logging - Task 12.2

Enhanced logging for debugging and development with:
- Color-coded output
- Structured context
- Log filtering
- Performance warnings
"""

import sys
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from pathlib import Path
import json
from contextlib import contextmanager
from functools import wraps

import structlog
from structlog.processors import CallsiteParameter
from structlog.dev import ConsoleRenderer
from structlog.contextvars import merge_contextvars

from ..config.dev_config import get_dev_config


# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    # Levels
    DEBUG = '\033[90m'      # Gray
    INFO = '\033[92m'       # Green
    WARNING = '\033[93m'    # Yellow
    ERROR = '\033[91m'      # Red
    CRITICAL = '\033[95m'   # Magenta
    # Components
    FLOW = '\033[94m'       # Blue
    KB = '\033[96m'         # Cyan
    AGENT = '\033[35m'      # Purple
    METRIC = '\033[33m'     # Orange
    # Special
    BOLD = '\033[1m'
    DIM = '\033[2m'


class DevLogFormatter:
    """Custom formatter for developer-friendly output"""
    
    def __init__(self, show_timestamp: bool = True, show_caller: bool = True):
        self.show_timestamp = show_timestamp
        self.show_caller = show_caller
    
    def __call__(self, _, __, event_dict: Dict[str, Any]) -> str:
        """Format log entry for console output"""
        # Extract components
        level = event_dict.get("level", "info").upper()
        msg = event_dict.get("event", "")
        timestamp = event_dict.get("timestamp")
        
        # Handle timestamp formatting
        if isinstance(timestamp, str):
            # Parse ISO format timestamp from structlog
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        elif not timestamp:
            timestamp = datetime.now()
        
        # Color based on level
        level_colors = {
            "DEBUG": Colors.DEBUG,
            "INFO": Colors.INFO,
            "WARNING": Colors.WARNING,
            "ERROR": Colors.ERROR,
            "CRITICAL": Colors.CRITICAL
        }
        color = level_colors.get(level, Colors.RESET)
        
        # Build output
        parts = []
        
        # Timestamp
        if self.show_timestamp:
            time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
            parts.append(f"{Colors.DIM}{time_str}{Colors.RESET}")
        
        # Level with icon
        level_icons = {
            "DEBUG": "🔍",
            "INFO": "ℹ️ ",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
            "CRITICAL": "🔥"
        }
        icon = level_icons.get(level, "")
        parts.append(f"{color}{icon} {level:8}{Colors.RESET}")
        
        # Component tag
        component = event_dict.get("component", "")
        if component:
            comp_colors = {
                "flow": Colors.FLOW,
                "kb": Colors.KB,
                "agent": Colors.AGENT,
                "metric": Colors.METRIC
            }
            comp_color = comp_colors.get(component.lower(), Colors.DIM)
            parts.append(f"{comp_color}[{component}]{Colors.RESET}")
        
        # Caller info
        if self.show_caller:
            if "pathname" in event_dict and "lineno" in event_dict:
                file_path = Path(event_dict["pathname"]).name
                line_no = event_dict["lineno"]
                parts.append(f"{Colors.DIM}{file_path}:{line_no}{Colors.RESET}")
        
        # Main message
        parts.append(f"{Colors.BOLD}{msg}{Colors.RESET}")
        
        # Context data
        context_keys = [
            "flow_id", "stage", "duration", "cache_hit",
            "query", "agent", "task", "error_type"
        ]
        
        context_parts = []
        for key in context_keys:
            if key in event_dict:
                value = event_dict[key]
                if key == "duration" and isinstance(value, (int, float)):
                    value = f"{value:.3f}s"
                context_parts.append(f"{Colors.DIM}{key}={value}{Colors.RESET}")
        
        if context_parts:
            parts.append("| " + " ".join(context_parts))
        
        # Additional data
        extra_data = {
            k: v for k, v in event_dict.items()
            if k not in ["event", "level", "timestamp", "component", 
                        "pathname", "lineno", "func_name"] + context_keys
        }
        
        if extra_data and level in ["ERROR", "WARNING", "DEBUG"]:
            parts.append(f"\n    {Colors.DIM}{json.dumps(extra_data, indent=2)}{Colors.RESET}")
        
        return " ".join(parts)


class PerformanceWarningProcessor:
    """Processor that adds warnings for slow operations"""
    
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or {
            "kb_query": 1.0,
            "content_generation": 5.0,
            "validation": 2.0,
            "flow_execution": 10.0
        }
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add performance warnings"""
        duration = event_dict.get("duration")
        operation = event_dict.get("operation", "")
        
        if duration and operation in self.thresholds:
            threshold = self.thresholds[operation]
            if duration > threshold:
                event_dict["performance_warning"] = f"Slow {operation}: {duration:.2f}s (threshold: {threshold}s)"
                # Upgrade level if needed
                if event_dict.get("level") == "info":
                    event_dict["level"] = "warning"
        
        return event_dict


class FlowContextProcessor:
    """Processor that adds flow context"""
    
    def __call__(self, logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add flow context if available"""
        # This would be populated by flow execution
        flow_context = event_dict.get("_flow_context", {})
        if flow_context:
            event_dict.update({
                "flow_id": flow_context.get("flow_id"),
                "flow_type": flow_context.get("flow_type"),
                "stage": flow_context.get("current_stage")
            })
        
        return event_dict


def setup_dev_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    show_timestamp: bool = True,
    show_caller: bool = True,
    enable_performance_warnings: bool = True
):
    """
    Setup developer-friendly logging configuration.
    
    Args:
        log_level: Minimum log level
        log_file: Optional file to write logs to
        show_timestamp: Show timestamps in console
        show_caller: Show caller information
        enable_performance_warnings: Enable slow operation warnings
    """
    config = get_dev_config()
    
    # Processors
    processors = [
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    # Add caller info if requested
    if show_caller:
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    CallsiteParameter.PATHNAME,
                    CallsiteParameter.LINENO,
                    CallsiteParameter.FUNC_NAME,
                ]
            )
        )
    
    # Add custom processors
    processors.append(FlowContextProcessor())
    
    if enable_performance_warnings:
        processors.append(PerformanceWarningProcessor())
    
    # Console output processor
    if config.verbose_logging:
        # Use custom formatter for verbose mode
        processors.append(DevLogFormatter(show_timestamp, show_caller))
    else:
        # Use structlog's console renderer
        processors.append(
            ConsoleRenderer(colors=True, exception_formatter=structlog.dev.plain_traceback)
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Setup file logging if requested
    if log_file:
        import logging
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level))
        logging.root.addHandler(file_handler)
    
    # Set log level
    import logging
    logging.root.setLevel(getattr(logging, log_level))


# Context managers for enhanced logging
@contextmanager
def log_context(**kwargs):
    """Add context to all logs within the block"""
    logger = structlog.get_logger()
    bound_logger = logger.bind(**kwargs)
    
    # Store previous logger
    previous = structlog.contextvars.get_contextvars()
    
    try:
        # Set bound logger as current
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**kwargs)
        yield bound_logger
    finally:
        # Restore previous
        structlog.contextvars.clear_contextvars()
        if previous:
            structlog.contextvars.bind_contextvars(**previous)


@contextmanager
def log_performance(operation: str, warn_threshold: Optional[float] = None):
    """Log performance of an operation"""
    logger = structlog.get_logger()
    start = time.time()
    
    logger.debug(f"Starting {operation}")
    
    try:
        yield
    finally:
        duration = time.time() - start
        
        # Log with appropriate level
        if warn_threshold and duration > warn_threshold:
            logger.warning(
                f"Slow {operation}",
                operation=operation,
                duration=duration,
                threshold=warn_threshold
            )
        else:
            logger.info(
                f"Completed {operation}",
                operation=operation,
                duration=duration
            )


# Decorators for common logging patterns
def log_method(component: str = ""):
    """Decorator to log method entry/exit"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = structlog.get_logger()
            func_name = func.__name__
            
            # Log entry
            logger.debug(
                f"→ {func_name}",
                component=component,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
            
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                
                # Log exit
                logger.debug(
                    f"← {func_name}",
                    component=component,
                    duration=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start
                logger.error(
                    f"✗ {func_name} failed",
                    component=component,
                    duration=duration,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator


def log_slow_operations(threshold: float = 1.0):
    """Decorator to warn about slow operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with log_performance(func.__name__, warn_threshold=threshold):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Specialized loggers for different components
def get_flow_logger(flow_id: str, flow_type: str) -> Any:
    """Get logger for flow execution"""
    return structlog.get_logger().bind(
        component="flow",
        flow_id=flow_id,
        flow_type=flow_type
    )


def get_agent_logger(agent_name: str) -> Any:
    """Get logger for agent execution"""
    return structlog.get_logger().bind(
        component="agent",
        agent=agent_name
    )


def get_kb_logger() -> Any:
    """Get logger for knowledge base operations"""
    return structlog.get_logger().bind(component="kb")


def get_metrics_logger() -> Any:
    """Get logger for metrics collection"""
    return structlog.get_logger().bind(component="metric")


# Helper functions for common logging scenarios
def log_flow_stage(flow_id: str, stage: str, message: str, **kwargs):
    """Log flow stage transition"""
    logger = get_flow_logger(flow_id, kwargs.get("flow_type", "unknown"))
    logger.info(
        message,
        stage=stage,
        **kwargs
    )


def log_kb_query(query: str, cache_hit: bool, duration: float, **kwargs):
    """Log KB query with standard format"""
    logger = get_kb_logger()
    
    if cache_hit:
        logger.info(
            "KB cache hit",
            query=query[:50] + "..." if len(query) > 50 else query,
            cache_hit=True,
            duration=duration,
            **kwargs
        )
    else:
        logger.info(
            "KB query executed",
            query=query[:50] + "..." if len(query) > 50 else query,
            cache_hit=False,
            duration=duration,
            **kwargs
        )


def log_agent_action(agent_name: str, action: str, **kwargs):
    """Log agent action"""
    logger = get_agent_logger(agent_name)
    logger.info(
        f"Agent {action}",
        action=action,
        **kwargs
    )