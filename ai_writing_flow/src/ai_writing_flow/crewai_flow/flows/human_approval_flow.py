"""
Human Approval Flow - Task 8.1

Implements human review integration at key decision points
with listen decorators for approval workflows.
"""

import time
import asyncio
import uuid
import json
import structlog
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
try:
    from crewai.flow import Flow as _CrewFlow
    BaseFlow = _CrewFlow
except Exception:
    BaseFlow = object

from ...models import (
    HumanFeedbackDecision,
    WritingFlowState
)
from ...utils.ui_bridge_v2 import UIBridgeV2
from ..persistence import get_state_manager
from ..logging import get_decision_logger

# Configure structured logging
logger = structlog.get_logger(__name__)


class ReviewDecision(str, Enum):
    """Human review decision types"""
    APPROVE = "approve"
    EDIT = "edit"
    REVISE = "revise"
    REDIRECT = "redirect"
    SKIP = "skip"


class HumanReviewPoint(BaseModel):
    """Human review point configuration"""
    stage: str
    title: str
    description: str
    options: List[ReviewDecision] = Field(
        default=[ReviewDecision.APPROVE, ReviewDecision.EDIT, ReviewDecision.REVISE]
    )
    timeout_seconds: int = 300  # 5 minutes default
    default_decision: ReviewDecision = ReviewDecision.APPROVE
    required_fields: List[str] = Field(default_factory=list)


class HumanApprovalState(BaseModel):
    """State management for Human Approval Flow"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"approval_flow_{int(time.time())}")
    parent_flow_id: Optional[str] = None
    
    # Review state
    current_review_point: Optional[str] = None
    pending_review: bool = False
    review_request_id: Optional[str] = None
    
    # Content being reviewed
    content_type: str = ""
    content_preview: str = ""
    full_content: Dict[str, Any] = Field(default_factory=dict)
    
    # Review results
    review_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    latest_decision: Optional[ReviewDecision] = None
    human_feedback: Optional[str] = None
    
    # Metrics
    review_start_time: Optional[float] = None
    total_review_time: float = 0.0
    review_count: int = 0
    timeout_count: int = 0


class HumanApprovalFlow(BaseFlow):
    """
    Human Approval Flow with review integration points.
    
    Features:
    - Multiple review trigger points
    - Configurable review options per stage
    - Timeout handling with defaults
    - UI Bridge integration
    - Decision persistence and logging
    """
    
    # Define review points
    REVIEW_POINTS = {
        "draft_completion": HumanReviewPoint(
            stage="draft_completion",
            title="Draft Review",
            description="Review the generated draft content",
            options=[ReviewDecision.APPROVE, ReviewDecision.EDIT, ReviewDecision.REVISE],
            timeout_seconds=300,
            default_decision=ReviewDecision.APPROVE
        ),
        "quality_gate": HumanReviewPoint(
            stage="quality_gate",
            title="Quality Gate Review",
            description="Final quality check before publication",
            options=[ReviewDecision.APPROVE, ReviewDecision.REVISE, ReviewDecision.REDIRECT],
            timeout_seconds=600,
            default_decision=ReviewDecision.REVISE,
            required_fields=["quality_score", "checklist_status"]
        ),
        "topic_viability": HumanReviewPoint(
            stage="topic_viability",
            title="Topic Viability Review",
            description="Review low-viability topic for manual override",
            options=[ReviewDecision.APPROVE, ReviewDecision.SKIP, ReviewDecision.REDIRECT],
            timeout_seconds=180,
            default_decision=ReviewDecision.SKIP
        ),
        "routing_override": HumanReviewPoint(
            stage="routing_override",
            title="Routing Override",
            description="Override automatic content routing decision",
            options=[ReviewDecision.APPROVE, ReviewDecision.REDIRECT],
            timeout_seconds=120,
            default_decision=ReviewDecision.APPROVE
        )
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Human Approval Flow
        
        Args:
            config: Flow configuration including:
                - ui_bridge: UIBridgeV2 instance
                - enable_timeouts: Enable timeout handling
                - auto_approve: Auto-approve if True (testing)
        """
        super().__init__()
        # Ensure state exists without CrewAI runtime
        try:
            self.state  # type: ignore[attr-defined]
        except Exception:
            self.state = HumanApprovalState()
        self.config = config or {}
        
        # UI Bridge for human interaction
        self.ui_bridge = self.config.get('ui_bridge') or UIBridgeV2()
        
        # Configuration
        self.enable_timeouts = self.config.get('enable_timeouts', True)
        self.auto_approve = self.config.get('auto_approve', False)
        
        # Initialize components
        self.decision_logger = get_decision_logger()
        self.state_manager = get_state_manager()
        
        logger.info(
            "HumanApprovalFlow initialized",
            flow_id=self.state.flow_id,
            config=self.config
        )
    
    def review_draft_completion(self, draft_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Human review point after draft generation
        
        Args:
            draft_output: Generated draft content
            
        Returns:
            Review decision and feedback
        """
        return self._execute_review(
            review_point="draft_completion",
            content=draft_output,
            context={
                "word_count": draft_output.get("word_count", 0),
                "platform": draft_output.get("platform", "Unknown"),
                "content_type": draft_output.get("content_type", "general")
            }
        )
    
    def review_quality_gate(self, quality_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Human review at final quality gate
        
        Args:
            quality_output: Quality check results
            
        Returns:
            Review decision for publication
        """
        # Validate required fields
        review_point = self.REVIEW_POINTS["quality_gate"]
        missing_fields = [
            field for field in review_point.required_fields
            if field not in quality_output
        ]
        
        if missing_fields:
            logger.warning(
                "Missing required fields for quality gate",
                missing_fields=missing_fields
            )
            quality_output.update({
                field: "Not Available" for field in missing_fields
            })
        
        return self._execute_review(
            review_point="quality_gate",
            content=quality_output,
            context={
                "quality_score": quality_output.get("quality_score", 0),
                "issues_found": quality_output.get("issues", []),
                "recommendations": quality_output.get("recommendations", [])
            }
        )
    
    def review_topic_viability(self, viability_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Human review for low-viability topics
        
        Args:
            viability_output: Topic analysis results
            
        Returns:
            Decision to proceed or skip
        """
        return self._execute_review(
            review_point="topic_viability",
            content=viability_output,
            context={
                "viability_score": viability_output.get("viability_score", 0),
                "reasons": viability_output.get("low_score_reasons", []),
                "alternatives": viability_output.get("alternative_topics", [])
            }
        )
    
    def review_routing_decision(self, routing_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Human override for routing decisions
        
        Args:
            routing_output: Automatic routing decision
            
        Returns:
            Final routing decision
        """
        return self._execute_review(
            review_point="routing_override",
            content=routing_output,
            context={
                "auto_routing": routing_output.get("routing_decision", "unknown"),
                "confidence": routing_output.get("confidence", 0),
                "reasoning": routing_output.get("reasoning", "")
            }
        )
    
    def _execute_review(
        self,
        review_point: str,
        content: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute human review process
        
        Args:
            review_point: Review point identifier
            content: Content to review
            context: Additional context for review
            
        Returns:
            Review results including decision and feedback
        """
        start_time = time.time()
        
        # Get review configuration
        review_config = self.REVIEW_POINTS.get(review_point)
        if not review_config:
            logger.error(f"Unknown review point: {review_point}")
            return {
                "decision": ReviewDecision.SKIP,
                "error": f"Unknown review point: {review_point}"
            }
        
        # Update state
        self.state.current_review_point = review_point
        self.state.pending_review = True
        self.state.review_start_time = start_time
        self.state.full_content = content
        self.state.content_preview = self._generate_preview(content)
        
        logger.info(
            "Initiating human review",
            flow_id=self.state.flow_id,
            review_point=review_point,
            title=review_config.title
        )
        
        # Save checkpoint before review
        self.state_manager.save_state(
            flow_id=self.state.flow_id,
            state=self.state,
            stage=f"pre_review_{review_point}",
            metadata={"context": context}
        )
        
        try:
            # Auto-approve for testing
            if self.auto_approve:
                logger.info("Auto-approving review (test mode)")
                decision = review_config.default_decision
                feedback = "Auto-approved (test mode)"
            else:
                # Request human review via UI Bridge
                decision, feedback = self._request_human_review(
                    review_config,
                    content,
                    context
                )
            
            # Process decision
            review_result = self._process_review_decision(
                review_point=review_point,
                decision=decision,
                feedback=feedback,
                execution_time=time.time() - start_time
            )
            
            # Save checkpoint after review
            self.state_manager.save_state(
                flow_id=self.state.flow_id,
                state=self.state,
                stage=f"post_review_{review_point}",
                metadata={"decision": decision, "feedback": feedback}
            )
            
            return review_result
            
        except Exception as e:
            logger.error(
                "Review execution failed",
                flow_id=self.state.flow_id,
                review_point=review_point,
                error=str(e)
            )
            
            # Return default decision on error
            return {
                "decision": review_config.default_decision,
                "feedback": None,
                "error": str(e),
                "review_point": review_point
            }
    
    def _request_human_review(
        self,
        review_config: HumanReviewPoint,
        content: Dict[str, Any],
        context: Dict[str, Any]
    ) -> tuple[ReviewDecision, Optional[str]]:
        """
        Request human review via UI Bridge
        
        Returns:
            Tuple of (decision, feedback)
        """
        # Generate review request
        review_request_id = str(uuid.uuid4())
        self.state.review_request_id = review_request_id
        
        review_request = {
            "request_id": review_request_id,
            "flow_id": self.state.flow_id,
            "review_point": review_config.stage,
            "title": review_config.title,
            "description": review_config.description,
            "content": content,
            "context": context,
            "options": [opt.value for opt in review_config.options],
            "timeout_seconds": review_config.timeout_seconds
        }
        
        # Send to UI Bridge
        logger.info(
            "Sending review request to UI",
            request_id=review_request_id,
            timeout=review_config.timeout_seconds
        )
        
        # Use async event loop for UI Bridge interaction
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create review task with timeout
            review_task = loop.create_task(
                self._async_review_request(review_request)
            )
            
            if self.enable_timeouts:
                # Wait with timeout
                done, pending = loop.run_until_complete(
                    asyncio.wait(
                        [review_task],
                        timeout=review_config.timeout_seconds
                    )
                )
                
                if review_task in pending:
                    # Timeout occurred
                    logger.warning(
                        "Review request timed out",
                        request_id=review_request_id,
                        timeout=review_config.timeout_seconds
                    )
                    review_task.cancel()
                    self.state.timeout_count += 1
                    
                    return review_config.default_decision, "Review timed out"
                else:
                    # Got response
                    decision, feedback = review_task.result()
                    return decision, feedback
            else:
                # No timeout
                decision, feedback = loop.run_until_complete(review_task)
                return decision, feedback
                
        except Exception as e:
            logger.error(
                "UI Bridge communication failed",
                error=str(e)
            )
            return review_config.default_decision, f"UI error: {str(e)}"
        finally:
            loop.close()
    
    async def _async_review_request(
        self,
        review_request: Dict[str, Any]
    ) -> tuple[ReviewDecision, Optional[str]]:
        """
        Async wrapper for UI Bridge review request
        """
        # In production, this would call UIBridge methods
        # For now, simulate async review
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Mock response for testing
        # In production: response = await self.ui_bridge.request_review(review_request)
        mock_response = {
            "decision": ReviewDecision.APPROVE,
            "feedback": "Looks good to proceed"
        }
        
        return (
            ReviewDecision(mock_response["decision"]),
            mock_response.get("feedback")
        )
    
    def _process_review_decision(
        self,
        review_point: str,
        decision: ReviewDecision,
        feedback: Optional[str],
        execution_time: float
    ) -> Dict[str, Any]:
        """
        Process and log review decision
        """
        # Update state
        self.state.pending_review = False
        self.state.latest_decision = decision
        self.state.human_feedback = feedback
        self.state.total_review_time += execution_time
        self.state.review_count += 1
        
        # Record decision
        decision_record = {
            "review_point": review_point,
            "decision": decision.value,
            "feedback": feedback,
            "execution_time": execution_time,
            "timestamp": time.time()
        }
        self.state.review_decisions.append(decision_record)
        
        # Log decision
        self.decision_logger.log_human_review(
            flow_id=self.state.flow_id,
            review_point=review_point,
            decision=decision.value,
            feedback=feedback,
            execution_time_ms=execution_time * 1000,
            context={
                "content_type": self.state.content_type,
                "timeout_count": self.state.timeout_count,
                "review_count": self.state.review_count
            }
        )
        
        logger.info(
            "Review decision processed",
            flow_id=self.state.flow_id,
            review_point=review_point,
            decision=decision.value,
            execution_time=execution_time
        )
        
        return {
            "decision": decision.value,
            "feedback": feedback,
            "review_point": review_point,
            "execution_time": execution_time,
            "timestamp": decision_record["timestamp"]
        }
    
    def _generate_preview(self, content: Dict[str, Any]) -> str:
        """Generate content preview for UI display"""
        # Extract main content
        if "content" in content:
            preview = str(content["content"])[:500]
        elif "text" in content:
            preview = str(content["text"])[:500]
        elif "draft" in content:
            preview = str(content["draft"])[:500]
        else:
            # JSON preview
            preview = json.dumps(content, indent=2)[:500]
        
        if len(preview) == 500:
            preview += "..."
        
        return preview
    
    def get_review_summary(self) -> Dict[str, Any]:
        """Get summary of all reviews in this flow"""
        return {
            "flow_id": self.state.flow_id,
            "total_reviews": self.state.review_count,
            "total_review_time": self.state.total_review_time,
            "timeout_count": self.state.timeout_count,
            "decisions": self.state.review_decisions,
            "latest_decision": self.state.latest_decision.value if self.state.latest_decision else None,
            "avg_review_time": (
                self.state.total_review_time / self.state.review_count
                if self.state.review_count > 0 else 0
            )
        }