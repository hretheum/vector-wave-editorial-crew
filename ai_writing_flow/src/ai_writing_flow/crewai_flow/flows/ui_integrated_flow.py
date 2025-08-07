"""
UI Integrated Flow - Task 9.1

Integrates CrewAI Flow with existing UIBridge V2 for human review
and real-time status updates.
"""

import time
import asyncio
import structlog
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, start, listen

from ...utils.ui_bridge_v2 import UIBridgeV2, create_ui_bridge_v2
from ...models import WritingFlowState, HumanFeedbackDecision
from .human_approval_flow import HumanApprovalFlow, ReviewDecision
from .integrated_approval_flow import IntegratedApprovalFlow
from ..persistence import get_state_manager
from ..logging import get_decision_logger

# Configure structured logging
logger = structlog.get_logger(__name__)


class UIIntegratedFlowState(BaseModel):
    """State for UI integrated flow"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"ui_flow_{int(time.time())}")
    session_id: Optional[str] = None
    
    # UI Bridge tracking
    ui_bridge_initialized: bool = False
    active_review_ids: List[str] = Field(default_factory=list)
    progress_updates_sent: int = 0
    
    # Content state
    topic_title: str = ""
    platform: str = ""
    current_draft: Optional[str] = None
    final_draft: Optional[str] = None
    
    # Flow execution state
    current_stage: str = "initialization"
    stages_completed: List[str] = Field(default_factory=list)
    
    # Metrics
    start_time: float = Field(default_factory=time.time)
    total_execution_time: float = 0.0
    ui_response_times: List[float] = Field(default_factory=list)


class UIIntegratedFlow(Flow[UIIntegratedFlowState]):
    """
    CrewAI Flow integrated with UIBridge V2.
    
    Features:
    - Seamless integration with existing UIBridge
    - Real-time progress updates to UI
    - Human review request handling
    - Session tracking and management
    - Compatibility with existing Kolegium interface
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize UI Integrated Flow
        
        Args:
            config: Configuration including:
                - ui_bridge: Existing UIBridge instance
                - enable_monitoring: Enable monitoring integration
                - auto_mode: Auto-approve for testing
        """
        super().__init__()
        self.config = config or {}
        
        # Initialize or use provided UI Bridge
        self.ui_bridge = self.config.get('ui_bridge')
        if not self.ui_bridge:
            # Create new UI Bridge with monitoring if enabled
            flow_metrics = self.config.get('flow_metrics')
            alert_manager = self.config.get('alert_manager')
            dashboard_api = self.config.get('dashboard_api')
            
            self.ui_bridge = create_ui_bridge_v2(
                flow_metrics=flow_metrics,
                alert_manager=alert_manager,
                dashboard_api=dashboard_api
            )
        
        self.state.ui_bridge_initialized = True
        
        # Initialize sub-flows
        self.approval_flow = None
        self.integrated_approval = None
        
        # Auto mode for testing
        self.auto_mode = self.config.get('auto_mode', False)
        
        # Initialize components
        self.state_manager = get_state_manager()
        self.decision_logger = get_decision_logger()
        
        logger.info(
            "UIIntegratedFlow initialized",
            flow_id=self.state.flow_id,
            ui_bridge_initialized=self.state.ui_bridge_initialized,
            auto_mode=self.auto_mode
        )
    
    @start()
    def start_ui_flow(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start flow with UI session tracking
        
        Args:
            inputs: Flow inputs including topic, platform, etc.
            
        Returns:
            Session initialization result
        """
        # Extract inputs
        self.state.topic_title = inputs.get('topic_title', '')
        self.state.platform = inputs.get('platform', 'General')
        
        # Start UI session
        self.state.session_id = self.ui_bridge.start_flow_session(inputs)
        
        logger.info(
            "UI flow session started",
            flow_id=self.state.flow_id,
            session_id=self.state.session_id,
            topic=self.state.topic_title,
            platform=self.state.platform
        )
        
        # Send initial progress update
        asyncio.run(self._send_progress_update(
            stage="initialization",
            message=f"Starting AI writing flow for: {self.state.topic_title}",
            progress_percent=5.0
        ))
        
        return {
            "session_id": self.state.session_id,
            "topic": self.state.topic_title,
            "platform": self.state.platform,
            "ui_ready": True
        }
    
    @listen(start_ui_flow)
    def process_with_ui_updates(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process flow with UI progress updates
        
        Returns:
            Processing result
        """
        try:
            # Stage 1: Content Analysis
            self.state.current_stage = "content_analysis"
            asyncio.run(self._send_progress_update(
                stage="content_analysis",
                message="Analyzing content requirements...",
                progress_percent=15.0
            ))
            
            # Simulate content analysis
            time.sleep(1)  # In production, actual analysis would happen here
            
            # Stage 2: Draft Generation
            self.state.current_stage = "draft_generation"
            asyncio.run(self._send_progress_update(
                stage="draft_generation",
                message="Generating initial draft...",
                progress_percent=40.0,
                metadata={"expected_time": "30 seconds"}
            ))
            
            # Generate draft (mock for testing)
            draft_content = self._generate_mock_draft()
            self.state.current_draft = draft_content
            
            # Stage 3: Send for Review
            self.state.current_stage = "human_review"
            review_metadata = {
                "word_count": len(draft_content.split()),
                "structure_type": "standard",
                "platform": self.state.platform,
                "estimated_reading_time": 2
            }
            
            review_id = self.ui_bridge.send_draft_for_review(
                draft=draft_content,
                metadata=review_metadata,
                session_id=self.state.session_id
            )
            self.state.active_review_ids.append(review_id)
            
            asyncio.run(self._send_progress_update(
                stage="human_review",
                message="Draft sent for human review...",
                progress_percent=60.0,
                metadata={"review_id": review_id}
            ))
            
            # Get human feedback
            feedback = self._get_human_feedback_with_ui(review_id)
            
            # Stage 4: Process Feedback
            if feedback:
                self.state.current_stage = "feedback_processing"
                asyncio.run(self._send_progress_update(
                    stage="feedback_processing",
                    message=f"Processing feedback: {feedback.feedback_type}",
                    progress_percent=75.0
                ))
                
                # Process feedback (in production, would route to appropriate flow)
                final_draft = self._process_feedback(feedback)
            else:
                # No feedback means approval
                final_draft = draft_content
            
            self.state.final_draft = final_draft
            
            # Stage 5: Finalization
            self.state.current_stage = "finalization"
            asyncio.run(self._send_progress_update(
                stage="finalization",
                message="Finalizing content...",
                progress_percent=90.0
            ))
            
            # Send completion notice
            flow_state = WritingFlowState(
                topic_title=self.state.topic_title,
                platform=self.state.platform,
                final_draft=self.state.final_draft,
                quality_score=0.85,
                style_score=0.9,
                revision_count=1 if feedback else 0,
                total_processing_time=time.time() - self.state.start_time
            )
            
            self.ui_bridge.send_completion_notice(
                state=flow_state,
                session_id=self.state.session_id
            )
            
            # Final progress update
            asyncio.run(self._send_progress_update(
                stage="completed",
                message="Flow completed successfully!",
                progress_percent=100.0
            ))
            
            return {
                "success": True,
                "session_id": self.state.session_id,
                "final_draft": self.state.final_draft,
                "execution_time": time.time() - self.state.start_time
            }
            
        except Exception as e:
            logger.error(
                "Flow processing failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Escalate to human
            self.ui_bridge.escalate_to_human(
                reason=f"Flow processing error: {str(e)}",
                severity="high",
                session_id=self.state.session_id,
                context={
                    "stage": self.state.current_stage,
                    "error_type": type(e).__name__
                }
            )
            
            raise
    
    async def _send_progress_update(
        self,
        stage: str,
        message: str,
        progress_percent: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Send progress update to UI"""
        await self.ui_bridge.stream_progress(
            stage=stage,
            message=message,
            session_id=self.state.session_id,
            progress_percent=progress_percent,
            metadata=metadata
        )
        self.state.progress_updates_sent += 1
    
    def _generate_mock_draft(self) -> str:
        """Generate mock draft for testing"""
        return f"""# {self.state.topic_title}

## Introduction
This is a comprehensive guide about {self.state.topic_title}, designed specifically for the {self.state.platform} platform.

## Key Points
1. Understanding the fundamentals
2. Practical implementation strategies
3. Best practices and recommendations

## Detailed Analysis
[Content would be generated here based on research and analysis]

## Conclusion
This article has explored the key aspects of {self.state.topic_title}, providing actionable insights for readers.

## Next Steps
- Apply these concepts in your projects
- Share your experiences
- Continue learning and improving

---
*Generated by AI Writing Flow*
"""
    
    def _get_human_feedback_with_ui(self, review_id: str) -> Optional[HumanFeedbackDecision]:
        """Get human feedback through UI Bridge"""
        start_time = time.time()
        
        if self.auto_mode:
            logger.info("Auto-mode: Simulating human approval")
            time.sleep(0.5)  # Simulate processing time
            return None  # None means approval
        
        # Get feedback from UI Bridge
        feedback = self.ui_bridge.get_human_feedback(
            review_id=review_id,
            timeout=300  # 5 minute timeout
        )
        
        # Record response time
        response_time = time.time() - start_time
        self.state.ui_response_times.append(response_time)
        
        return feedback
    
    def _process_feedback(self, feedback: HumanFeedbackDecision) -> str:
        """Process human feedback and modify draft"""
        logger.info(
            "Processing human feedback",
            feedback_type=feedback.feedback_type,
            feedback_text=feedback.feedback_text
        )
        
        # In production, this would route to appropriate flow for processing
        # For now, simulate feedback processing
        draft = self.state.current_draft
        
        if feedback.feedback_type == "minor":
            # Minor adjustments
            draft = (draft or "") + "\n\n*[Minor revisions applied based on feedback]*"
        elif feedback.feedback_type == "major":
            # Major restructuring
            draft = f"*[Restructured based on feedback: {feedback.feedback_text}]*\n\n" + (draft or "")
        elif feedback.feedback_type == "pivot":
            # Complete rewrite with new direction
            draft = f"""# {self.state.topic_title} - Revised Approach

Based on feedback, this content has been completely rewritten to focus on: {feedback.feedback_text}

{draft or ""}
"""
        
        return draft
    
    def get_ui_metrics(self) -> Dict[str, Any]:
        """Get UI integration metrics"""
        avg_response_time = (
            sum(self.state.ui_response_times) / len(self.state.ui_response_times)
            if self.state.ui_response_times else 0
        )
        
        return {
            "flow_id": self.state.flow_id,
            "session_id": self.state.session_id,
            "ui_bridge_initialized": self.state.ui_bridge_initialized,
            "progress_updates_sent": self.state.progress_updates_sent,
            "active_reviews": len(self.state.active_review_ids),
            "avg_ui_response_time": avg_response_time,
            "total_execution_time": time.time() - self.state.start_time,
            "stages_completed": self.state.stages_completed,
            "current_stage": self.state.current_stage
        }
    
    def cleanup(self):
        """Cleanup UI session"""
        if self.state.session_id:
            self.ui_bridge.cleanup_session(self.state.session_id)
            logger.info(
                "UI session cleaned up",
                flow_id=self.state.flow_id,
                session_id=self.state.session_id
            )