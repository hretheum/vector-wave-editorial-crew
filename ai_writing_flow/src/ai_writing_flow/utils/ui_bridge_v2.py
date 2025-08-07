"""
UI Bridge V2 - Enhanced interface for AI Writing Flow V2 with monitoring integration

This module provides the V2 UI bridge that integrates with:
- Phase 3 monitoring stack (FlowMetrics, AlertManager)
- Real-time progress streaming
- Quality gate notifications
- Dashboard metrics integration
"""

from typing import Dict, Any, Optional, List, Callable
import json
import asyncio
import uuid
from datetime import datetime, timezone
import logging

from ..models import HumanFeedbackDecision, WritingFlowState

# Phase 3 monitoring integration
try:
    from ..monitoring.flow_metrics import FlowMetrics
    from ..monitoring.alerting import AlertManager, Alert, AlertSeverity
    from ..monitoring.dashboard_api import DashboardAPI
except ImportError:
    # Fallback for environments without monitoring
    FlowMetrics = None
    AlertManager = None
    DashboardAPI = None

logger = logging.getLogger(__name__)


class UIBridgeV2:
    """
    Enhanced UI Bridge for AI Writing Flow V2 with monitoring integration
    
    Features:
    - Real-time progress streaming with correlation IDs
    - Integration with FlowMetrics for performance data
    - Quality gate notifications to UI
    - Alert forwarding from AlertManager
    - Dashboard metrics exposure via API
    - Enhanced error reporting and escalation
    """
    
    def __init__(
        self, 
        flow_metrics: Optional[FlowMetrics] = None,
        alert_manager: Optional[AlertManager] = None,
        dashboard_api: Optional[DashboardAPI] = None
    ):
        """
        Initialize UI Bridge V2 with monitoring integration
        
        Args:
            flow_metrics: FlowMetrics instance for performance data
            alert_manager: AlertManager for alert notifications
            dashboard_api: DashboardAPI for metrics exposure
        """
        
        # Core UI bridge functionality
        self.pending_feedback = {}
        self.draft_reviews = {}
        self.completion_callbacks = {}
        self.progress_callbacks: List[Callable] = []
        
        # Phase 3 monitoring integration
        self.flow_metrics = flow_metrics
        self.alert_manager = alert_manager
        self.dashboard_api = dashboard_api
        
        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # UI notification queue
        self.notification_queue = []
        
        logger.info("🌉 UI Bridge V2 initialized with monitoring integration")
    
    def start_flow_session(self, inputs: Dict[str, Any]) -> str:
        """
        Start a new flow session with tracking
        
        Args:
            inputs: Flow input parameters
            
        Returns:
            str: Session ID for tracking
        """
        
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "inputs": inputs,
            "start_time": datetime.now(timezone.utc),
            "status": "active",
            "current_stage": "initialization",
            "progress_updates": [],
            "draft_versions": [],
            "alerts": [],
            "metrics": {}
        }
        
        self.active_sessions[session_id] = session_data
        
        # Record session start in metrics
        if self.flow_metrics:
            self.flow_metrics.record_flow_start(session_id, "session_start", inputs)
        
        logger.info(f"🚀 Started flow session: {session_id}")
        return session_id
    
    def send_draft_for_review(
        self, 
        draft: str, 
        metadata: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """
        Send draft to UI for human review with enhanced tracking
        
        Args:
            draft: Generated draft content
            metadata: Draft metadata (word count, structure, etc.)
            session_id: Optional session ID for tracking
            
        Returns:
            str: Review ID for tracking
        """
        
        review_id = f"review_{datetime.now().timestamp()}"
        
        review_data = {
            "review_id": review_id,
            "session_id": session_id,
            "draft": draft,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending_review",
            "word_count": len(draft.split()),
            "character_count": len(draft),
            "estimated_reading_time": self._calculate_reading_time(draft)
        }
        
        self.draft_reviews[review_id] = review_data
        
        # Update session if provided
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["draft_versions"].append(review_data)
            session["current_stage"] = "human_review"
        
        # Record metrics
        if self.flow_metrics:
            self.flow_metrics.record_stage_completion(
                session_id or "unknown",
                "draft_generated", 
                1.0,  # execution_time placeholder
                True  # success
            )
        
        # Notify UI via callback system
        self._notify_ui("draft_ready", {
            "review_id": review_id,
            "session_id": session_id,
            "metadata": metadata,
            "preview": draft[:200] + "..." if len(draft) > 200 else draft
        })
        
        logger.info(f"📤 Sent draft for review: {review_id}")
        logger.info(f"   Session: {session_id}")
        logger.info(f"   Word count: {metadata.get('word_count', 0)}")
        logger.info(f"   Structure: {metadata.get('structure_type', 'unknown')}")
        
        return review_id
    
    def get_human_feedback(
        self, 
        review_id: Optional[str] = None,
        timeout: int = 300
    ) -> Optional[HumanFeedbackDecision]:
        """
        Get human feedback with enhanced tracking
        
        Args:
            review_id: Optional review ID to get feedback for
            timeout: Timeout in seconds
            
        Returns:
            HumanFeedbackDecision or None if timeout
        """
        
        logger.info(f"⏳ Waiting for human feedback (review: {review_id})")
        
        # In production, this would wait for actual WebSocket/API callback
        # For now, simulate realistic feedback scenarios
        
        import time
        import random
        
        # Simulate variable response time (2-10 seconds)
        response_time = random.uniform(2, 10)
        time.sleep(response_time)
        
        # Simulate different feedback types with realistic distribution
        feedback_scenarios = {
            "approve": 0.6,    # 60% approval
            "minor": 0.25,     # 25% minor changes
            "major": 0.10,     # 10% major changes
            "pivot": 0.05      # 5% direction change
        }
        
        feedback_type = random.choices(
            list(feedback_scenarios.keys()),
            weights=list(feedback_scenarios.values())
        )[0]
        
        if feedback_type == "approve":
            # No feedback needed, proceed to next stage
            logger.info("✅ Human approved - proceeding to next stage")
            return None
        
        feedback_messages = {
            "minor": [
                "Please adjust the tone to be more technical",
                "Add more concrete examples",
                "Simplify the language for broader audience",
                "Include more specific metrics"
            ],
            "major": [
                "Need to restructure around practical examples",
                "Change the focus to implementation challenges",
                "Add more detailed technical analysis",
                "Restructure to follow problem-solution format"
            ],
            "pivot": [
                "Let's focus on implementation challenges instead",
                "Change direction to cover security aspects",
                "Pivot to discuss performance implications",
                "Switch focus to cost optimization"
            ]
        }
        
        selected_message = random.choice(feedback_messages[feedback_type])
        
        feedback = HumanFeedbackDecision(
            feedback_type=feedback_type,
            feedback_text=selected_message,
            specific_changes=self._generate_specific_changes(feedback_type),
            continue_to_stage=self._determine_next_stage(feedback_type),
            reviewer_confidence=random.uniform(0.7, 1.0),
            estimated_impact=feedback_type
        )
        
        # Record feedback metrics
        if self.flow_metrics:
            self.flow_metrics.record_stage_completion(
                review_id or "unknown",
                f"human_feedback_{feedback_type}",
                response_time,
                True
            )
        
        logger.info(f"📥 Received feedback: {feedback_type} - {selected_message}")
        logger.info(f"   Response time: {response_time:.1f}s")
        
        return feedback
    
    def escalate_to_human(
        self, 
        reason: str, 
        severity: str = "high",
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Enhanced escalation with monitoring integration
        
        Args:
            reason: Escalation reason
            severity: Escalation severity (low, medium, high, critical)
            session_id: Optional session ID for tracking
            context: Additional context data
        """
        
        escalation_id = str(uuid.uuid4())
        
        escalation_data = {
            "escalation_id": escalation_id,
            "session_id": session_id,
            "reason": reason,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": context or {},
            "status": "pending",
            "auto_generated": True
        }
        
        # Add to notification queue
        self.notification_queue.append({
            "type": "escalation",
            "data": escalation_data
        })
        
        # Create alert if alert manager available
        if self.alert_manager:
            alert_severity = {
                "low": AlertSeverity.LOW,
                "medium": AlertSeverity.MEDIUM, 
                "high": AlertSeverity.HIGH,
                "critical": AlertSeverity.CRITICAL
            }.get(severity, AlertSeverity.HIGH)
            
            # This would typically trigger an alert rule
            logger.warning(f"🚨 ESCALATION: {reason} (severity: {severity})")
        
        # Update session
        if session_id and session_id in self.active_sessions:
            self.active_sessions[session_id]["alerts"].append(escalation_data)
        
        # Notify UI
        self._notify_ui("escalation", escalation_data)
        
        logger.warning(f"🚨 ESCALATION [{escalation_id}]: {reason}")
        logger.info(f"   Session: {session_id}")
        logger.info(f"   Severity: {severity}")
        logger.info(f"   Context: {json.dumps(context or {}, indent=2)}")
    
    def send_quality_gate_notification(
        self,
        validation_results: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:
        """Send quality gate results to UI"""
        
        notification_data = {
            "type": "quality_gate",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": validation_results,
            "overall_status": validation_results.get("overall_status", {}),
            "failed_rules": [
                rule for rule, result in validation_results.get("rule_results", {}).items()
                if not result.get("passed", True)
            ]
        }
        
        # Notify UI
        self._notify_ui("quality_gate", notification_data)
        
        status = "✅ PASSED" if validation_results.get("overall_status", {}).get("passed", False) else "❌ FAILED"
        logger.info(f"🔒 Quality Gate {status}")
        
        if notification_data["failed_rules"]:
            logger.warning(f"   Failed rules: {notification_data['failed_rules']}")
    
    def send_completion_notice(
        self, 
        state: WritingFlowState,
        session_id: Optional[str] = None
    ) -> None:
        """
        Enhanced completion notice with comprehensive metrics
        
        Args:
            state: Final flow state
            session_id: Optional session ID for tracking
        """
        
        completion_data = {
            "flow_id": session_id or f"flow_{datetime.now().timestamp()}",
            "session_id": session_id,
            "topic": state.topic_title,
            "platform": state.platform,
            "final_draft": state.final_draft,
            "completion_time": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "quality_score": getattr(state, 'quality_score', 0),
                "style_score": getattr(state, 'style_score', 0),
                "revision_count": getattr(state, 'revision_count', 0),
                "processing_time": getattr(state, 'total_processing_time', 0),
                "agents_executed": len(getattr(state, 'agents_executed', [])),
                "word_count": len(state.final_draft.split()) if state.final_draft else 0
            },
            "metadata": getattr(state, 'publication_metadata', {}),
            "dashboard_url": self._get_dashboard_url(session_id) if self.dashboard_api else None
        }
        
        # Update session
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["status"] = "completed"
            session["completion_data"] = completion_data
            session["end_time"] = datetime.now(timezone.utc)
        
        # Record completion metrics
        if self.flow_metrics:
            self.flow_metrics.record_flow_completion(
                session_id or "unknown",
                True,  # success
                "flow_completed"  # final_stage
            )
        
        # Notify UI
        self._notify_ui("flow_completed", completion_data)
        
        logger.info("✅ Flow completed successfully!")
        logger.info(f"  Session: {session_id}")
        logger.info(f"  Topic: {state.topic_title}")
        logger.info(f"  Quality Score: {completion_data['metrics']['quality_score']}")
        logger.info(f"  Processing Time: {completion_data['metrics']['processing_time']:.1f}s")
        logger.info(f"  Word Count: {completion_data['metrics']['word_count']}")
    
    async def stream_progress(
        self, 
        stage: str, 
        message: str,
        session_id: Optional[str] = None,
        progress_percent: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Enhanced progress streaming with metadata
        
        Args:
            stage: Current stage name
            message: Progress message
            session_id: Optional session ID
            progress_percent: Optional progress percentage (0-100)
            metadata: Additional metadata
        """
        
        progress_update = {
            "type": "progress",
            "session_id": session_id,
            "stage": stage,
            "message": message,
            "progress_percent": progress_percent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        # Update session
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["current_stage"] = stage
            session["progress_updates"].append(progress_update)
        
        # Call registered progress callbacks
        for callback in self.progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress_update)
                else:
                    callback(progress_update)
            except Exception as e:
                logger.error(f"❌ Progress callback failed: {e}")
        
        # Log progress
        progress_str = f" ({progress_percent:.1f}%)" if progress_percent else ""
        logger.info(f"📊 Progress{progress_str}: [{stage}] {message}")
        
        # Simulate async streaming
        await asyncio.sleep(0.1)
    
    def get_dashboard_metrics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get dashboard metrics for UI display
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Dict containing dashboard metrics
        """
        
        if not self.dashboard_api:
            return {"error": "Dashboard API not available"}
        
        try:
            # Get overall dashboard metrics
            dashboard_metrics = self.dashboard_api.get_dashboard_overview()
            
            # Add session-specific data if available
            session_data = None
            if session_id and session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
            
            return {
                "dashboard_metrics": dashboard_metrics.dict() if hasattr(dashboard_metrics, 'dict') else dashboard_metrics,
                "session_data": session_data,
                "active_sessions": len(self.active_sessions),
                "notification_count": len(self.notification_queue)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard metrics: {e}")
            return {"error": str(e)}
    
    def register_progress_callback(self, callback: Callable) -> None:
        """Register callback for progress updates"""
        self.progress_callbacks.append(callback)
        logger.info(f"📞 Registered progress callback: {callback.__name__}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        return self.active_sessions.get(session_id)
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions.keys())
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up completed session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"🧹 Cleaned up session: {session_id}")
    
    # Private helper methods
    
    def _calculate_reading_time(self, text: str) -> int:
        """Calculate estimated reading time in minutes"""
        words = len(text.split())
        # Average reading speed: 200 words per minute
        return max(1, round(words / 200))
    
    def _generate_specific_changes(self, feedback_type: str) -> List[str]:
        """Generate specific change suggestions based on feedback type"""
        
        changes_map = {
            "minor": [
                "Adjust tone for target audience",
                "Add specific examples",
                "Clarify technical terms",
                "Improve readability"
            ],
            "major": [
                "Restructure content organization",
                "Add comprehensive examples",
                "Expand technical analysis",
                "Revise main arguments"
            ],
            "pivot": [
                "Change content focus",
                "Research different angle",
                "Update target audience",
                "Revise content strategy"
            ]
        }
        
        import random
        available_changes = changes_map.get(feedback_type, [])
        return random.sample(available_changes, min(2, len(available_changes)))
    
    def _determine_next_stage(self, feedback_type: str) -> str:
        """Determine next stage based on feedback type"""
        
        stage_map = {
            "minor": "validate_style",
            "major": "generate_draft",
            "pivot": "conduct_research"
        }
        
        return stage_map.get(feedback_type, "validate_style")
    
    def _notify_ui(self, notification_type: str, data: Dict[str, Any]) -> None:
        """Send notification to UI (placeholder for actual implementation)"""
        
        notification = {
            "id": str(uuid.uuid4()),
            "type": notification_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        # In production, this would use WebSocket, SSE, or message queue
        logger.debug(f"🔔 UI Notification [{notification_type}]: {notification['id']}")
    
    def _get_dashboard_url(self, session_id: Optional[str] = None) -> str:
        """Get dashboard URL for session"""
        base_url = "/dashboard"
        if session_id:
            return f"{base_url}?session={session_id}"
        return base_url


# Factory function for backward compatibility
def create_ui_bridge_v2(
    flow_metrics: Optional[FlowMetrics] = None,
    alert_manager: Optional[AlertManager] = None,
    dashboard_api: Optional[DashboardAPI] = None
) -> UIBridgeV2:
    """
    Factory function to create UI Bridge V2 with monitoring integration
    
    Args:
        flow_metrics: FlowMetrics instance
        alert_manager: AlertManager instance  
        dashboard_api: DashboardAPI instance
        
    Returns:
        UIBridgeV2: Configured UI bridge instance
    """
    
    return UIBridgeV2(
        flow_metrics=flow_metrics,
        alert_manager=alert_manager,
        dashboard_api=dashboard_api
    )


# Export main class
__all__ = ["UIBridgeV2", "create_ui_bridge_v2"]