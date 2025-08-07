"""
Integrated Approval Flow - Task 8.3

Combines human approval and feedback processing with timeout handling
to create complete approval flow patterns.
"""

import time
import asyncio
import structlog
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, start, listen, router

from .human_approval_flow import HumanApprovalFlow, ReviewDecision, HumanReviewPoint
from .feedback_processing_flow import FeedbackProcessingFlow, FeedbackAction
from ..persistence import get_state_manager
from ..logging import get_decision_logger

# Configure structured logging
logger = structlog.get_logger(__name__)


class ApprovalPattern(BaseModel):
    """Defines an approval pattern configuration"""
    name: str
    description: str
    review_points: List[str]  # Which review points to use
    enable_timeout: bool = True
    timeout_behavior: str = "continue"  # continue, skip, or default
    max_total_time: int = 1800  # 30 minutes max total time
    enable_revisions: bool = True
    max_revisions: int = 3


class IntegratedApprovalState(BaseModel):
    """State for integrated approval flow"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"integrated_approval_{int(time.time())}")
    parent_flow_id: Optional[str] = None
    
    # Pattern tracking
    active_pattern: Optional[str] = None
    pattern_config: Optional[ApprovalPattern] = None
    
    # Timing
    flow_start_time: float = Field(default_factory=time.time)
    total_elapsed_time: float = 0.0
    timeouts_occurred: int = 0
    
    # Review tracking
    reviews_completed: List[str] = Field(default_factory=list)
    reviews_pending: List[str] = Field(default_factory=list)
    current_review_stage: Optional[str] = None
    
    # Subprocess tracking
    approval_flow_id: Optional[str] = None
    feedback_flow_id: Optional[str] = None


class IntegratedApprovalFlow(Flow[IntegratedApprovalState]):
    """
    Integrated approval flow with patterns and timeout handling.
    
    Combines:
    - Human approval points
    - Feedback processing
    - Timeout management
    - Pattern-based workflows
    """
    
    # Pre-defined approval patterns
    APPROVAL_PATTERNS = {
        "quick_review": ApprovalPattern(
            name="quick_review",
            description="Fast approval with short timeouts",
            review_points=["draft_completion"],
            enable_timeout=True,
            timeout_behavior="continue",
            max_total_time=600,  # 10 minutes
            enable_revisions=False
        ),
        "full_review": ApprovalPattern(
            name="full_review",
            description="Complete review cycle with all checkpoints",
            review_points=["draft_completion", "quality_gate"],
            enable_timeout=True,
            timeout_behavior="default",
            max_total_time=3600,  # 1 hour
            enable_revisions=True,
            max_revisions=3
        ),
        "editorial_review": ApprovalPattern(
            name="editorial_review",
            description="Editorial review with revision loops",
            review_points=["draft_completion", "quality_gate"],
            enable_timeout=False,  # No timeout for editorial
            timeout_behavior="continue",
            max_total_time=7200,  # 2 hours
            enable_revisions=True,
            max_revisions=5
        ),
        "auto_approve": ApprovalPattern(
            name="auto_approve",
            description="Automatic approval for trusted flows",
            review_points=[],  # No human review
            enable_timeout=False,
            timeout_behavior="continue",
            max_total_time=60,  # 1 minute
            enable_revisions=False
        )
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Integrated Approval Flow
        
        Args:
            config: Configuration including:
                - pattern: Approval pattern to use
                - ui_bridge: UI Bridge instance
                - custom_patterns: Additional patterns
        """
        super().__init__()
        self.config = config or {}
        
        # Load pattern
        pattern_name = self.config.get('pattern', 'full_review')
        self.state.active_pattern = pattern_name
        
        # Add custom patterns if provided
        custom_patterns = self.config.get('custom_patterns', {})
        self.APPROVAL_PATTERNS.update(custom_patterns)
        
        # Get pattern config
        if pattern_name in self.APPROVAL_PATTERNS:
            self.state.pattern_config = self.APPROVAL_PATTERNS[pattern_name]
        else:
            logger.warning(f"Unknown pattern {pattern_name}, using full_review")
            self.state.pattern_config = self.APPROVAL_PATTERNS['full_review']
        
        # Initialize components
        self.state_manager = get_state_manager()
        self.decision_logger = get_decision_logger()
        
        # Initialize sub-flows
        self.approval_flow = None
        self.feedback_flow = None
        
        logger.info(
            "IntegratedApprovalFlow initialized",
            flow_id=self.state.flow_id,
            pattern=self.state.active_pattern,
            review_points=self.state.pattern_config.review_points
        )
    
    @start()
    def execute_approval_pattern(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the configured approval pattern
        
        Args:
            content_data: Content and context for review
            
        Returns:
            Pattern execution result
        """
        start_time = time.time()
        
        logger.info(
            "Executing approval pattern",
            flow_id=self.state.flow_id,
            pattern=self.state.active_pattern,
            review_points=len(self.state.pattern_config.review_points)
        )
        
        # Check for auto-approve pattern
        if self.state.active_pattern == "auto_approve":
            logger.info("Auto-approve pattern - skipping reviews")
            return {
                "pattern": "auto_approve",
                "approved": True,
                "reviews_completed": [],
                "total_time": time.time() - start_time
            }
        
        # Initialize review tracking
        self.state.reviews_pending = self.state.pattern_config.review_points.copy()
        
        # Save initial state
        self.state_manager.save_state(
            flow_id=self.state.flow_id,
            state=self.state,
            stage="pattern_start",
            metadata={
                "pattern": self.state.active_pattern,
                "total_reviews": len(self.state.reviews_pending)
            }
        )
        
        return {
            "pattern": self.state.active_pattern,
            "reviews_pending": self.state.reviews_pending,
            "timeout_enabled": self.state.pattern_config.enable_timeout,
            "max_time": self.state.pattern_config.max_total_time
        }
    
    @listen(execute_approval_pattern)
    def process_review_sequence(self, pattern_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the sequence of reviews based on pattern
        
        Returns:
            Sequence processing result
        """
        results = {
            "reviews_completed": [],
            "reviews_skipped": [],
            "total_revisions": 0,
            "timeouts": 0,
            "final_status": "completed"
        }
        
        # Check if we have reviews to process
        if not self.state.reviews_pending:
            return results
        
        # Initialize approval flow
        self.approval_flow = HumanApprovalFlow(config={
            'ui_bridge': self.config.get('ui_bridge'),
            'enable_timeouts': self.state.pattern_config.enable_timeout,
            'auto_approve': self.config.get('auto_approve', False)
        })
        self.state.approval_flow_id = self.approval_flow.state.flow_id
        
        # Initialize feedback flow if revisions enabled
        if self.state.pattern_config.enable_revisions:
            self.feedback_flow = FeedbackProcessingFlow(config={
                'max_revisions': self.state.pattern_config.max_revisions
            })
            self.state.feedback_flow_id = self.feedback_flow.state.flow_id
        
        # Process each review point
        for review_point in self.state.reviews_pending:
            # Check total time limit
            elapsed = time.time() - self.state.flow_start_time
            if elapsed > self.state.pattern_config.max_total_time:
                logger.warning(
                    "Max total time exceeded",
                    flow_id=self.state.flow_id,
                    elapsed=elapsed,
                    max_time=self.state.pattern_config.max_total_time
                )
                results["reviews_skipped"].extend(
                    self.state.reviews_pending[self.state.reviews_pending.index(review_point):]
                )
                results["final_status"] = "timeout"
                break
            
            # Process review
            review_result = self._process_single_review(
                review_point,
                pattern_output.get('content_data', {})
            )
            
            results["reviews_completed"].append(review_point)
            
            # Handle review result
            if review_result.get('timeout'):
                results["timeouts"] += 1
                
                if self.state.pattern_config.timeout_behavior == "skip":
                    logger.info(f"Skipping remaining reviews due to timeout")
                    results["reviews_skipped"].extend(
                        self.state.reviews_pending[self.state.reviews_pending.index(review_point)+1:]
                    )
                    break
                elif self.state.pattern_config.timeout_behavior == "default":
                    # Continue with default decision
                    logger.info(f"Continuing with default decision after timeout")
            
            # Handle revisions if needed
            if review_result.get('decision') == 'revise' and self.state.pattern_config.enable_revisions:
                revision_result = self._handle_revision_loop(
                    review_point,
                    review_result
                )
                results["total_revisions"] += revision_result.get('revisions', 0)
            
            # Handle termination
            if review_result.get('decision') == 'skip':
                logger.info(f"Flow terminated at {review_point}")
                results["final_status"] = "terminated"
                break
        
        # Update state
        self.state.reviews_completed = results["reviews_completed"]
        self.state.total_elapsed_time = time.time() - self.state.flow_start_time
        
        # Save final state
        self.state_manager.save_state(
            flow_id=self.state.flow_id,
            state=self.state,
            stage="pattern_complete",
            metadata=results
        )
        
        return results
    
    def _process_single_review(
        self,
        review_point: str,
        content_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single review point with timeout handling
        
        Returns:
            Review result including timeout status
        """
        logger.info(
            "Processing review point",
            flow_id=self.state.flow_id,
            review_point=review_point
        )
        
        # Update current stage
        self.state.current_review_stage = review_point
        
        # Get review method
        review_methods = {
            "draft_completion": self.approval_flow.review_draft_completion,
            "quality_gate": self.approval_flow.review_quality_gate,
            "topic_viability": self.approval_flow.review_topic_viability,
            "routing_override": self.approval_flow.review_routing_decision
        }
        
        review_method = review_methods.get(review_point)
        if not review_method:
            logger.error(f"Unknown review point: {review_point}")
            return {"error": f"Unknown review point: {review_point}"}
        
        # Execute review with timeout monitoring
        start_time = time.time()
        
        try:
            # Set shorter timeout if pattern requires
            if self.state.pattern_config.enable_timeout:
                # Adjust timeout based on pattern
                if self.state.active_pattern == "quick_review":
                    # Override timeout for quick review
                    self.approval_flow.REVIEW_POINTS[review_point].timeout_seconds = 60
            
            # Execute review
            result = review_method(content_data)
            
            # Check if timeout occurred
            elapsed = time.time() - start_time
            timeout_occurred = False
            
            if "Review timed out" in result.get('feedback', ''):
                timeout_occurred = True
                self.state.timeouts_occurred += 1
            
            return {
                **result,
                "timeout": timeout_occurred,
                "elapsed_time": elapsed
            }
            
        except Exception as e:
            logger.error(
                "Review processing failed",
                flow_id=self.state.flow_id,
                review_point=review_point,
                error=str(e)
            )
            return {
                "error": str(e),
                "decision": "continue",  # Safe default
                "timeout": False
            }
    
    def _handle_revision_loop(
        self,
        review_point: str,
        review_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle revision loop with feedback processing
        
        Returns:
            Revision processing result
        """
        logger.info(
            "Handling revision loop",
            flow_id=self.state.flow_id,
            review_point=review_point
        )
        
        if not self.feedback_flow:
            logger.warning("Revisions not enabled for this pattern")
            return {"revisions": 0}
        
        # Process feedback
        feedback_data = {
            "decision": review_result.get('decision'),
            "feedback": review_result.get('feedback'),
            "review_point": review_point
        }
        
        feedback_result = self.feedback_flow.process_feedback_decision(feedback_data)
        
        # Get revision count
        revisions = self.feedback_flow.state.revision_count
        
        return {
            "revisions": revisions,
            "feedback_processed": True,
            "action": feedback_result.get('action')
        }
    
    @router(process_review_sequence)
    def route_final_decision(self, sequence_result: Dict[str, Any]) -> str:
        """
        Route based on final approval status
        
        Returns:
            'approved', 'rejected', or 'timeout'
        """
        final_status = sequence_result.get('final_status', 'completed')
        
        if final_status == 'terminated':
            return 'rejected'
        elif final_status == 'timeout':
            return 'timeout'
        else:
            return 'approved'
    
    @listen("approved")
    def handle_approval(self) -> Dict[str, Any]:
        """Handle approved content"""
        return {
            "status": "approved",
            "message": "Content approved through review pattern",
            "pattern": self.state.active_pattern,
            "reviews_completed": self.state.reviews_completed,
            "total_time": self.state.total_elapsed_time
        }
    
    @listen("rejected")
    def handle_rejection(self) -> Dict[str, Any]:
        """Handle rejected content"""
        return {
            "status": "rejected",
            "message": "Content rejected during review",
            "pattern": self.state.active_pattern,
            "reviews_completed": self.state.reviews_completed,
            "total_time": self.state.total_elapsed_time
        }
    
    @listen("timeout")
    def handle_timeout(self) -> Dict[str, Any]:
        """Handle timeout scenario"""
        return {
            "status": "timeout",
            "message": f"Review process timed out ({self.state.pattern_config.timeout_behavior} behavior)",
            "pattern": self.state.active_pattern,
            "reviews_completed": self.state.reviews_completed,
            "timeouts_occurred": self.state.timeouts_occurred,
            "total_time": self.state.total_elapsed_time
        }
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of pattern execution"""
        return {
            "flow_id": self.state.flow_id,
            "pattern": self.state.active_pattern,
            "pattern_config": self.state.pattern_config.model_dump() if self.state.pattern_config else None,
            "reviews_completed": self.state.reviews_completed,
            "timeouts_occurred": self.state.timeouts_occurred,
            "total_elapsed_time": self.state.total_elapsed_time,
            "sub_flows": {
                "approval_flow_id": self.state.approval_flow_id,
                "feedback_flow_id": self.state.feedback_flow_id
            }
        }