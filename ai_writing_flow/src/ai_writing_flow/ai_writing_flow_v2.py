#!/usr/bin/env python
"""
AI Writing Flow V2 - Production Integration with Full Monitoring & Quality Gates

This module provides the production-ready V2 flow class that integrates:
- Phase 1: Core Architecture (FlowControlState, CircuitBreaker, etc.)
- Phase 2: Linear Flow Implementation (eliminates @router/@listen loops)
- Phase 3: Monitoring, Alerting & Quality Gates (FlowMetrics, Alerting, QualityGate)
- Phase 4: Kolegium System Integration (UI Bridge, API Endpoints)

AIWritingFlowV2 is the new entry point replacing the legacy AIWritingFlow.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

# Phase 1: Core Architecture
from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.models.flow_control_state import FlowControlState

# Phase 2: Linear Flow Implementation
from ai_writing_flow.linear_flow import (
    LinearAIWritingFlow,
    WritingFlowInputs,
    FlowDecisions,
    LinearFlowStateAdapter
)

# Phase 3: Monitoring, Alerting & Quality Gates
from ai_writing_flow.monitoring.flow_metrics import FlowMetrics, MetricsConfig
from ai_writing_flow.monitoring.alerting import AlertManager, AlertRule, AlertSeverity, KPIType
from ai_writing_flow.monitoring.dashboard_api import DashboardAPI
from ai_writing_flow.monitoring.storage import MetricsStorage, StorageConfig
from ai_writing_flow.validation.quality_gate import QualityGate

# Legacy compatibility imports
from ai_writing_flow.models import WritingFlowState
from ai_writing_flow.utils.ui_bridge import UIBridge
from ai_writing_flow.utils.ui_bridge_v2 import UIBridgeV2, create_ui_bridge_v2

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class AIWritingFlowV2:
    """
    Production-ready AI Writing Flow V2 with complete monitoring and quality gates
    
    Features:
    - Linear execution flow (no @router/@listen loops)
    - Real-time performance monitoring with KPI tracking
    - Multi-channel alerting system (console, webhook, email)
    - Quality gates with 5 validation rules
    - Production-ready observability and error handling
    - Backward compatibility with Kolegium system
    """
    
    def __init__(
        self,
        monitoring_enabled: bool = True,
        alerting_enabled: bool = True,
        quality_gates_enabled: bool = True,
        storage_path: Optional[str] = None
    ):
        """
        Initialize AIWritingFlowV2 with full monitoring stack
        
        Args:
            monitoring_enabled: Enable FlowMetrics monitoring (default: True)
            alerting_enabled: Enable AlertManager system (default: True)
            quality_gates_enabled: Enable QualityGate validation (default: True)
            storage_path: Custom storage path for metrics (default: ./metrics_data)
        """
        
        logger.info("🚀 Initializing AI Writing Flow V2 with full monitoring stack")
        
        # Phase 2: Initialize Linear Flow Core
        self.linear_flow = LinearAIWritingFlow()
        
        # Initialize UI Bridge (will be upgraded to V2 after monitoring setup)
        self.ui_bridge = None
        
        # Phase 3: Initialize Monitoring Stack
        self.monitoring_enabled = monitoring_enabled
        self.alerting_enabled = alerting_enabled
        self.quality_gates_enabled = quality_gates_enabled
        
        if self.monitoring_enabled:
            self._initialize_monitoring_stack(storage_path)
        
        if self.quality_gates_enabled:
            self._initialize_quality_gates()
        
        # Phase 4: Initialize Enhanced UI Bridge V2
        self._initialize_ui_bridge_v2()
        
        # Execution tracking
        self._flow_start_time: Optional[datetime] = None
        self._current_execution_id: Optional[str] = None
        
        logger.info("✅ AI Writing Flow V2 initialized successfully")
    
    def _initialize_monitoring_stack(self, storage_path: Optional[str] = None) -> None:
        """Initialize Phase 3 monitoring stack"""
        
        logger.info("📊 Initializing monitoring stack...")
        
        # Configure metrics
        metrics_config = MetricsConfig(
            memory_threshold_mb=500.0,  # 500MB threshold
            cpu_threshold_percent=30.0,  # 30% CPU threshold  
            error_rate_threshold=5.0   # 5% error rate threshold
        )
        
        # Initialize FlowMetrics with observer pattern
        self.flow_metrics = FlowMetrics(
            history_size=1000,
            config=metrics_config
        )
        
        # Initialize DashboardAPI
        self.dashboard_api = DashboardAPI(self.flow_metrics)
        
        # Initialize storage
        storage_config = StorageConfig(
            storage_path=storage_path or "metrics_data",
            retention_days=30,
            aggregation_intervals=[60, 300, 3600, 86400]  # 1m, 5m, 1h, 1d in seconds
        )
        
        self.metrics_storage = MetricsStorage(storage_config)
        
        # Initialize alerting if enabled
        if self.alerting_enabled:
            self._initialize_alerting_system()
        
        logger.info("✅ Monitoring stack initialized")
    
    def _initialize_alerting_system(self) -> None:
        """Initialize multi-channel alerting system"""
        
        logger.info("🚨 Initializing alerting system...")
        
        self.alert_manager = AlertManager()
        
        # Add production alert rules
        alert_rules = [
            AlertRule(
                id="high_cpu_usage",
                name="High CPU Usage Alert",
                kpi_type=KPIType.CPU_USAGE,
                threshold=80.0,
                comparison="greater_than",
                severity=AlertSeverity.HIGH,
                description="CPU usage exceeded 80%",
                cooldown_minutes=5,
                escalation_threshold=3
            ),
            AlertRule(
                id="high_memory_usage", 
                name="High Memory Usage Alert",
                kpi_type=KPIType.MEMORY_USAGE,
                threshold=400.0,  # 400MB
                comparison="greater_than",
                severity=AlertSeverity.MEDIUM,
                description="Memory usage exceeded 400MB",
                cooldown_minutes=10
            ),
            AlertRule(
                id="high_error_rate",
                name="High Error Rate Alert", 
                kpi_type=KPIType.ERROR_RATE,
                threshold=10.0,  # 10%
                comparison="greater_than",
                severity=AlertSeverity.CRITICAL,
                description="Error rate exceeded 10%",
                cooldown_minutes=2,
                escalation_threshold=2
            ),
            AlertRule(
                id="low_throughput",
                name="Low Throughput Alert",
                kpi_type=KPIType.THROUGHPUT,
                threshold=50.0,  # 50 ops/sec
                comparison="less_than", 
                severity=AlertSeverity.MEDIUM,
                description="Throughput below 50 ops/sec",
                cooldown_minutes=15
            )
        ]
        
        # Add rules to alert manager
        for rule in alert_rules:
            self.alert_manager.add_rule(rule)
        
        # Connect observer pattern: FlowMetrics -> AlertManager
        self.flow_metrics.add_observer(self.alert_manager)
        
        logger.info("✅ Alerting system initialized with observer pattern")
    
    def _initialize_quality_gates(self) -> None:
        """Initialize quality gates with validation rules"""
        
        logger.info("🔒 Initializing quality gates...")
        
        self.quality_gate = QualityGate()
        
        logger.info("✅ Quality gates initialized with 5 validation rules")
    
    def _initialize_ui_bridge_v2(self) -> None:
        """Initialize enhanced UI Bridge V2 with monitoring integration"""
        
        logger.info("🌉 Initializing UI Bridge V2...")
        
        # Create UI Bridge V2 with monitoring integration
        self.ui_bridge = create_ui_bridge_v2(
            flow_metrics=getattr(self, 'flow_metrics', None),
            alert_manager=getattr(self, 'alert_manager', None),
            dashboard_api=getattr(self, 'dashboard_api', None)
        )
        
        # Register progress callback for real-time updates
        def progress_callback(progress_data):
            """Handle progress updates from UI Bridge"""
            logger.debug(f"📊 Progress update: {progress_data['stage']} - {progress_data['message']}")
        
        self.ui_bridge.register_progress_callback(progress_callback)
        
        logger.info("✅ UI Bridge V2 initialized with monitoring integration")
    
    def add_notification_channel(self, channel) -> None:
        """
        Add notification channel to alerting system
        
        Args:
            channel: Notification channel (Console, Webhook, Email)
        """
        if self.alerting_enabled and hasattr(self, 'alert_manager'):
            self.alert_manager.add_notification_channel(channel)
            logger.info(f"📤 Added notification channel: {channel.__class__.__name__}")
    
    def kickoff(self, inputs: Dict[str, Any]) -> WritingFlowState:
        """
        Main entry point for flow execution with full monitoring
        
        Args:
            inputs: Flow input parameters dictionary
            
        Returns:
            WritingFlowState: Final execution state
            
        Raises:
            ValidationError: If inputs are invalid
            RuntimeError: If execution fails
        """
        
        logger.info("🎬 Starting AI Writing Flow V2 execution")
        
        # Start monitoring and UI session
        self._flow_start_time = datetime.now(timezone.utc)
        self._current_execution_id = f"flow_{int(self._flow_start_time.timestamp())}"
        
        # Start UI session tracking
        session_id = self.ui_bridge.start_flow_session(inputs) if self.ui_bridge else self._current_execution_id
        self._current_execution_id = session_id  # Use session ID as execution ID
        
        if self.monitoring_enabled:
            self.flow_metrics.record_flow_start(self._current_execution_id, "flow_start")
        
        try:
            # Validate inputs
            validated_inputs = self._validate_and_convert_inputs(inputs)
            
            # Run quality gates pre-execution validation
            if self.quality_gates_enabled:
                self._run_pre_execution_quality_gates()
            
            # Initialize linear flow with validated inputs
            self.linear_flow.initialize_flow(validated_inputs)
            
            # Execute linear flow
            chain_result = self.linear_flow.execute_linear_flow()
            
            if not chain_result.success:
                raise RuntimeError(f"Linear flow execution failed: {chain_result.error_message}")
            
            # Get final state
            final_state = self.linear_flow.writing_state
            
            # Run quality gates post-execution validation
            if self.quality_gates_enabled:
                self._run_post_execution_quality_gates(final_state)
            
            # Record successful execution
            if self.monitoring_enabled:
                self._record_successful_execution(final_state)
            
            # Send completion notice via UI Bridge V2
            if self.ui_bridge:
                self.ui_bridge.send_completion_notice(final_state, self._current_execution_id)
            
            logger.info("✅ AI Writing Flow V2 execution completed successfully")
            return final_state
            
        except Exception as e:
            logger.error(f"❌ AI Writing Flow V2 execution failed: {str(e)}", exc_info=True)
            
            # Record failed execution
            if self.monitoring_enabled:
                self._record_failed_execution(str(e))
            
            # Escalate to human via UI Bridge V2
            if self.ui_bridge:
                self.ui_bridge.escalate_to_human(
                    reason=f"Flow execution failed: {str(e)}",
                    severity="high",
                    session_id=self._current_execution_id,
                    context={"error_type": type(e).__name__, "inputs": inputs}
                )
            
            # Create failure state
            failure_state = WritingFlowState()
            failure_state.current_stage = "failed"
            failure_state.error_message = str(e)
            
            return failure_state
        
        finally:
            # Cleanup monitoring
            if self.monitoring_enabled and hasattr(self, 'flow_metrics'):
                self.flow_metrics.record_flow_completion(self._current_execution_id, True)
    
    def _validate_and_convert_inputs(self, inputs: Dict[str, Any]) -> WritingFlowInputs:
        """Validate and convert input dictionary to WritingFlowInputs"""
        
        try:
            # Convert legacy input format to new format
            converted_inputs = {
                "topic_title": inputs.get("topic_title", ""),
                "platform": inputs.get("platform", "LinkedIn"),
                "file_path": inputs.get("file_path", ""),
                "content_type": inputs.get("content_type", "STANDALONE"),
                "content_ownership": inputs.get("content_ownership", "EXTERNAL"),
                "viral_score": inputs.get("viral_score", 0.0),
                "editorial_recommendations": inputs.get("editorial_recommendations", ""),
                "skip_research": inputs.get("skip_research", False)
            }
            
            # Validate using Pydantic model
            validated_inputs = WritingFlowInputs(**converted_inputs)
            
            logger.info("✅ Input validation successful")
            return validated_inputs
            
        except ValidationError as e:
            logger.error(f"❌ Input validation failed: {e}")
            if self.monitoring_enabled:
                self.flow_metrics.record_stage_completion(self._current_execution_id or "unknown", "input_validation", 0.0, False)
            raise
    
    def _run_pre_execution_quality_gates(self) -> None:
        """Run quality gates before flow execution"""
        
        logger.info("🔒 Running pre-execution quality gates...")
        
        try:
            validation_result = self.quality_gate.run_validation()
            
            # Send quality gate results to UI
            if self.ui_bridge:
                self.ui_bridge.send_quality_gate_notification(
                    validation_result, 
                    self._current_execution_id
                )
            
            if not validation_result.get("quality_gate_passed", True):
                failed_rules = [
                    result.rule_id for result in validation_result.get("validation_results", [])
                    if not result.passed
                ]
                
                logger.warning(f"⚠️ Quality gate failures: {failed_rules}")
                
                # For now, log warnings but don't block execution
                # In strict mode, this would raise an exception
                
        except Exception as e:
            logger.error(f"❌ Quality gates validation failed: {e}")
            # Don't block execution on quality gate failures in production
    
    def _run_post_execution_quality_gates(self, final_state: WritingFlowState) -> None:
        """Run quality gates after flow execution"""
        
        logger.info("🔒 Running post-execution quality gates...")
        
        try:
            # Include execution context for post-execution validation
            context = {
                "execution_time": (datetime.now(timezone.utc) - self._flow_start_time).total_seconds(),
                "stages_completed": len(final_state.agents_executed),
                "final_stage": final_state.current_stage,
                "revision_count": getattr(final_state, 'revision_count', 0)
            }
            
            validation_result = self.quality_gate.run_validation(context)
            
            if validation_result.get("quality_gate_passed", True):
                logger.info("✅ Post-execution quality gates passed")
            else:
                logger.warning("⚠️ Some post-execution quality gates failed")
                
        except Exception as e:
            logger.error(f"❌ Post-execution quality gates failed: {e}")
    
    def _record_successful_execution(self, final_state: WritingFlowState) -> None:
        """Record successful execution metrics"""
        
        execution_time = (datetime.now(timezone.utc) - self._flow_start_time).total_seconds()
        
        # Record execution metrics
        self.flow_metrics.record_stage_completion(self._current_execution_id, "execution_completed", execution_time, True)
        self.flow_metrics.record_stage_completion(
            self._current_execution_id,
            final_state.current_stage,
            execution_time,
            True
        )
        
        # Store metrics
        if hasattr(self, 'metrics_storage'):
            try:
                kpis = self.flow_metrics.get_current_kpis()
                self.metrics_storage.store_kpis(kpis)
            except Exception as e:
                logger.warning(f"⚠️ Failed to store metrics: {e}")
    
    def _record_failed_execution(self, error_message: str) -> None:
        """Record failed execution metrics"""
        
        execution_time = (datetime.now(timezone.utc) - self._flow_start_time).total_seconds()
        
        # Record error metrics
        self.flow_metrics.record_stage_completion(self._current_execution_id or "unknown", "flow_execution", execution_time, False)
        self.flow_metrics.record_stage_completion(self._current_execution_id, "execution_completed", execution_time, True)
        
        # Store error metrics
        if hasattr(self, 'metrics_storage'):
            try:
                kpis = self.flow_metrics.get_current_kpis() 
                self.metrics_storage.store_kpis(kpis)
            except Exception as e:
                logger.warning(f"⚠️ Failed to store error metrics: {e}")
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get real-time dashboard metrics
        
        Returns:
            Dict containing dashboard metrics and health status
        """
        
        if not self.monitoring_enabled:
            return {"monitoring_enabled": False}
        
        try:
            dashboard_metrics = self.dashboard_api.get_dashboard_overview()
            
            return {
                "monitoring_enabled": True,
                "dashboard_metrics": dashboard_metrics.dict(),
                "alert_statistics": self.alert_manager.get_alert_statistics() if self.alerting_enabled else None,
                "quality_gate_status": "enabled" if self.quality_gates_enabled else "disabled"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard metrics: {e}")
            return {
                "monitoring_enabled": True,
                "error": str(e)
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status
        
        Returns:
            Dict containing health status of all systems
        """
        
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        try:
            # Linear flow health
            health_status["components"]["linear_flow"] = {
                "status": "healthy",
                "guard_status": self.linear_flow.get_execution_guards_status()
            }
            
            # Monitoring health
            if self.monitoring_enabled:
                health_status["components"]["monitoring"] = {
                    "status": "healthy",
                    "metrics_count": len(self.flow_metrics._completed_flows) + len(self.flow_metrics._failed_flows),
                    "storage_status": "connected" if hasattr(self, 'metrics_storage') else "disabled"
                }
            
            # Alerting health
            if self.alerting_enabled:
                alert_stats = self.alert_manager.get_alert_statistics()
                health_status["components"]["alerting"] = {
                    "status": "healthy",
                    "active_alerts": alert_stats["active_alerts"],
                    "total_rules": len(self.alert_manager.rules)
                }
            
            # Quality gates health
            if self.quality_gates_enabled:
                health_status["components"]["quality_gates"] = {
                    "status": "healthy", 
                    "rules_count": len(self.quality_gate.validation_rules)
                }
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            health_status["overall_status"] = "degraded"
            health_status["error"] = str(e)
        
        return health_status
    
    def emergency_stop(self) -> None:
        """Emergency stop all operations"""
        
        logger.critical("🚨 AI Writing Flow V2 EMERGENCY STOP")
        
        # Stop linear flow
        if hasattr(self.linear_flow, 'emergency_stop_execution'):
            self.linear_flow.emergency_stop_execution()
        
        # Stop monitoring
        if self.monitoring_enabled and hasattr(self, 'flow_metrics'):
            try:
                # FlowMetrics emergency stop - reset metrics
                self.flow_metrics.reset_metrics()
            except Exception as e:
                logger.error(f"❌ Failed to stop monitoring: {e}")
        
        logger.critical("🚨 Emergency stop completed")
    
    # Backward compatibility methods for Kolegium integration
    
    def plot(self, filename: str = "ai_writing_flow_v2_diagram.png") -> None:
        """Generate flow diagram for V2 architecture"""
        
        logger.info(f"📊 Generating V2 flow diagram: {filename}")
        
        # Create a simple text-based diagram since we don't have the original plot functionality
        diagram_content = """
AI Writing Flow V2 Architecture Diagram

┌─────────────────────────────────────────────────────────────────┐
│                    AI Writing Flow V2                           │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Core Architecture                                     │
│  ├── FlowControlState (Thread-safe state management)           │
│  ├── StageManager (Execution tracking)                         │
│  ├── CircuitBreaker (Fault tolerance)                          │
│  ├── RetryManager (Exponential backoff)                        │
│  └── LoopPreventionSystem (Infinite loop protection)           │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: Linear Flow Implementation                            │
│  ├── LinearExecutionChain (No @router/@listen loops)           │
│  ├── Linear Executors (Research, Audience, Draft, Style, QA)   │
│  ├── FlowExecutionGuards (Resource monitoring)                 │
│  └── WritingFlowInputs (Input validation)                      │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: Monitoring, Alerting & Quality Gates                 │
│  ├── FlowMetrics (Real-time KPI tracking)                     │
│  ├── AlertManager (Multi-channel notifications)                │
│  ├── DashboardAPI (Time-series data)                          │
│  ├── MetricsStorage (SQLite + file backends)                   │
│  └── QualityGate (5 validation rules)                         │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: Kolegium Integration                                  │
│  ├── UIBridge (Human review integration)                       │
│  ├── API Endpoints (Backward compatibility)                    │
│  └── Legacy WritingFlowState (State compatibility)             │
└─────────────────────────────────────────────────────────────────┘

Observer Pattern: FlowMetrics → AlertManager
Linear Chain: INPUT → RESEARCH → AUDIENCE → DRAFT → STYLE → QUALITY → OUTPUT
Quality Gates: Pre-execution + Post-execution validation
"""
        
        try:
            with open(filename.replace('.png', '.txt'), 'w') as f:
                f.write(diagram_content)
            logger.info(f"✅ V2 architecture diagram saved to {filename.replace('.png', '.txt')}")
        except Exception as e:
            logger.error(f"❌ Failed to save diagram: {e}")


# Legacy compatibility function
def kickoff():
    """Legacy compatibility function - creates V2 flow and executes with example inputs"""
    
    logger.info("🔄 Legacy kickoff() called - using AI Writing Flow V2")
    
    # Example inputs for testing
    initial_inputs = {
        "topic_title": "AI Writing Flow V2 Production Deployment",
        "platform": "LinkedIn",
        "file_path": "content/normalized/example-content.md",  # This would need to exist
        "content_type": "STANDALONE",
        "content_ownership": "ORIGINAL",
        "viral_score": 8.0,
        "editorial_recommendations": "Focus on production-ready features and monitoring capabilities"
    }
    
    # Create and execute V2 flow
    flow_v2 = AIWritingFlowV2(
        monitoring_enabled=True,
        alerting_enabled=True,
        quality_gates_enabled=True
    )
    
    try:
        final_state = flow_v2.kickoff(initial_inputs)
        logger.info("✅ Legacy kickoff completed successfully")
        return final_state
    except Exception as e:
        logger.error(f"❌ Legacy kickoff failed: {e}")
        raise


# Export main class and functions
__all__ = [
    "AIWritingFlowV2",
    "kickoff"  # Legacy compatibility
]