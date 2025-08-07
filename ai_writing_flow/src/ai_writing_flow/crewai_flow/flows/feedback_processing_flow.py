"""
Feedback Processing Flow - Task 8.2

Processes human review decisions and implements flow branching
based on approve/edit/revise/redirect decisions.
"""

import time
import structlog
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, start, listen, router

from ...models import WritingFlowState
from ..flows.research_flow import ResearchFlow
from ..flows.technical_content_flow import TechnicalContentFlow
from ..flows.viral_content_flow import ViralContentFlow
from ..flows.standard_content_flow import StandardContentFlow
from ..persistence import get_state_manager
from ..logging import get_decision_logger

# Configure structured logging
logger = structlog.get_logger(__name__)


class FeedbackAction(str, Enum):
    """Actions based on human feedback"""
    CONTINUE = "continue"  # Proceed with current flow
    REVISE = "revise"      # Re-run current stage with feedback
    EDIT = "edit"          # Apply edits and continue
    REDIRECT = "redirect"  # Change to different flow path
    TERMINATE = "terminate" # Stop flow execution


class FeedbackProcessingState(BaseModel):
    """State for feedback processing"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"feedback_flow_{int(time.time())}")
    parent_flow_id: Optional[str] = None
    
    # Feedback processing
    current_stage: str = ""
    feedback_decision: str = ""
    feedback_text: Optional[str] = None
    processing_action: Optional[FeedbackAction] = None
    
    # Revision tracking
    revision_count: int = 0
    max_revisions: int = 3
    revision_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Redirect tracking
    original_flow_path: Optional[str] = None
    redirect_flow_path: Optional[str] = None
    redirect_reason: Optional[str] = None
    
    # Performance metrics
    feedback_processing_time: float = 0.0
    total_revisions_time: float = 0.0


class FeedbackProcessingFlow(Flow[FeedbackProcessingState]):
    """
    Processes human feedback and implements flow branching.
    
    Features:
    - Decision processing (approve/edit/revise/redirect)
    - Revision loop management
    - Flow path redirection
    - Edit application
    - Feedback integration into content
    """
    
    # Decision to action mapping
    DECISION_ACTION_MAP = {
        "approve": FeedbackAction.CONTINUE,
        "edit": FeedbackAction.EDIT,
        "revise": FeedbackAction.REVISE,
        "redirect": FeedbackAction.REDIRECT,
        "skip": FeedbackAction.TERMINATE
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Feedback Processing Flow
        
        Args:
            config: Configuration including max_revisions
        """
        super().__init__()
        self.config = config or {}
        
        # Configuration
        self.state.max_revisions = self.config.get('max_revisions', 3)
        
        # Initialize components
        self.state_manager = get_state_manager()
        self.decision_logger = get_decision_logger()
        
        # Flow instances for redirection
        self.available_flows = {
            "research": ResearchFlow,
            "technical": TechnicalContentFlow,
            "viral": ViralContentFlow,
            "standard": StandardContentFlow
        }
        
        logger.info(
            "FeedbackProcessingFlow initialized",
            flow_id=self.state.flow_id,
            max_revisions=self.state.max_revisions
        )
    
    @start()
    def process_feedback_decision(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point: Process human feedback decision
        
        Args:
            feedback_data: Contains decision, feedback, stage, and content
            
        Returns:
            Processing result with action to take
        """
        start_time = time.time()
        
        # Extract feedback data
        self.state.feedback_decision = feedback_data.get("decision", "approve")
        self.state.feedback_text = feedback_data.get("feedback")
        self.state.current_stage = feedback_data.get("review_point", "unknown")
        
        # Determine action
        self.state.processing_action = self.DECISION_ACTION_MAP.get(
            self.state.feedback_decision,
            FeedbackAction.CONTINUE
        )
        
        logger.info(
            "Processing feedback decision",
            flow_id=self.state.flow_id,
            decision=self.state.feedback_decision,
            action=self.state.processing_action.value,
            stage=self.state.current_stage
        )
        
        # Log feedback processing
        self.decision_logger.log_feedback_processing(
            flow_id=self.state.flow_id,
            stage=self.state.current_stage,
            decision=self.state.feedback_decision,
            action=self.state.processing_action.value,
            has_feedback=self.state.feedback_text is not None
        )
        
        # Save state
        self.state_manager.save_state(
            flow_id=self.state.flow_id,
            state=self.state,
            stage="feedback_processing",
            metadata={
                "decision": self.state.feedback_decision,
                "action": self.state.processing_action.value
            }
        )
        
        self.state.feedback_processing_time = time.time() - start_time
        
        return {
            "action": self.state.processing_action.value,
            "feedback": self.state.feedback_text,
            "stage": self.state.current_stage,
            "revision_count": self.state.revision_count,
            "processing_time": self.state.feedback_processing_time
        }
    
    @router(process_feedback_decision)
    def route_by_action(self, processing_output: Dict[str, Any]) -> str:
        """
        Route based on processing action
        
        Returns:
            Route name: 'continue', 'revise', 'edit', 'redirect', or 'terminate'
        """
        action = processing_output.get("action", "continue")
        
        logger.info(
            "Routing by feedback action",
            flow_id=self.state.flow_id,
            action=action
        )
        
        return action
    
    @listen("continue")
    def handle_continue(self) -> Dict[str, Any]:
        """
        Handle approval - continue with current flow
        
        Returns:
            Instructions to continue
        """
        logger.info(
            "Handling continue action",
            flow_id=self.state.flow_id,
            stage=self.state.current_stage
        )
        
        return {
            "action": "continue",
            "message": "Human approved - continuing with current flow",
            "stage": self.state.current_stage,
            "feedback_applied": False
        }
    
    @listen("revise")
    def handle_revision(self) -> Dict[str, Any]:
        """
        Handle revision request - re-run current stage
        
        Returns:
            Revision instructions
        """
        start_time = time.time()
        
        # Check revision limit
        if self.state.revision_count >= self.state.max_revisions:
            logger.warning(
                "Maximum revisions reached",
                flow_id=self.state.flow_id,
                revision_count=self.state.revision_count,
                max_revisions=self.state.max_revisions
            )
            
            return {
                "action": "terminate",
                "message": f"Maximum revisions ({self.state.max_revisions}) reached",
                "stage": self.state.current_stage,
                "revision_count": self.state.revision_count
            }
        
        # Increment revision count
        self.state.revision_count += 1
        
        # Record revision
        revision_record = {
            "revision_number": self.state.revision_count,
            "stage": self.state.current_stage,
            "feedback": self.state.feedback_text,
            "timestamp": time.time()
        }
        self.state.revision_history.append(revision_record)
        
        logger.info(
            "Handling revision request",
            flow_id=self.state.flow_id,
            stage=self.state.current_stage,
            revision_count=self.state.revision_count,
            has_feedback=self.state.feedback_text is not None
        )
        
        # Prepare revision context
        revision_context = {
            "previous_feedback": self.state.feedback_text,
            "revision_number": self.state.revision_count,
            "revision_history": self.state.revision_history
        }
        
        revision_time = time.time() - start_time
        self.state.total_revisions_time += revision_time
        
        return {
            "action": "revise",
            "message": f"Revision {self.state.revision_count} requested",
            "stage": self.state.current_stage,
            "revision_context": revision_context,
            "feedback_applied": True
        }
    
    @listen("edit")
    def handle_edit(self) -> Dict[str, Any]:
        """
        Handle edit request - apply edits and continue
        
        Returns:
            Edit application result
        """
        logger.info(
            "Handling edit request",
            flow_id=self.state.flow_id,
            stage=self.state.current_stage,
            has_feedback=self.state.feedback_text is not None
        )
        
        # Parse edit instructions from feedback
        edit_instructions = self._parse_edit_instructions(self.state.feedback_text)
        
        # Apply edits (in production, this would modify the actual content)
        edit_result = {
            "action": "edit",
            "message": "Edits applied - continuing with modified content",
            "stage": self.state.current_stage,
            "edit_instructions": edit_instructions,
            "feedback_applied": True,
            "edits_count": len(edit_instructions)
        }
        
        # Record edit application
        self.state.revision_history.append({
            "type": "edit",
            "stage": self.state.current_stage,
            "instructions": edit_instructions,
            "timestamp": time.time()
        })
        
        return edit_result
    
    @listen("redirect")
    def handle_redirect(self) -> Dict[str, Any]:
        """
        Handle redirect request - change flow path
        
        Returns:
            Redirect instructions
        """
        logger.info(
            "Handling redirect request",
            flow_id=self.state.flow_id,
            current_stage=self.state.current_stage
        )
        
        # Parse redirect target from feedback
        redirect_target = self._parse_redirect_target(self.state.feedback_text)
        
        if not redirect_target:
            logger.warning(
                "No valid redirect target found",
                flow_id=self.state.flow_id,
                feedback=self.state.feedback_text
            )
            redirect_target = "standard"  # Default fallback
        
        # Record redirect
        self.state.original_flow_path = self.state.current_stage
        self.state.redirect_flow_path = redirect_target
        self.state.redirect_reason = self.state.feedback_text
        
        # Validate redirect target
        if redirect_target not in self.available_flows:
            logger.error(
                "Invalid redirect target",
                flow_id=self.state.flow_id,
                target=redirect_target,
                available=list(self.available_flows.keys())
            )
            redirect_target = "standard"
        
        return {
            "action": "redirect",
            "message": f"Redirecting to {redirect_target} flow",
            "original_path": self.state.original_flow_path,
            "redirect_path": redirect_target,
            "reason": self.state.redirect_reason,
            "feedback_applied": True
        }
    
    @listen("terminate")
    def handle_termination(self) -> Dict[str, Any]:
        """
        Handle termination request
        
        Returns:
            Termination result
        """
        logger.info(
            "Handling termination request",
            flow_id=self.state.flow_id,
            stage=self.state.current_stage,
            reason=self.state.feedback_text
        )
        
        return {
            "action": "terminate",
            "message": "Flow terminated by human decision",
            "stage": self.state.current_stage,
            "reason": self.state.feedback_text,
            "revision_count": self.state.revision_count
        }
    
    def _parse_edit_instructions(self, feedback: Optional[str]) -> List[Dict[str, str]]:
        """
        Parse edit instructions from feedback text
        
        Returns:
            List of edit instructions
        """
        if not feedback:
            return []
        
        instructions = []
        
        # Simple parsing - in production would use NLP
        lines = feedback.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # Look for common edit patterns
                if 'change' in line.lower() or 'replace' in line.lower():
                    instructions.append({
                        "type": "replace",
                        "instruction": line
                    })
                elif 'add' in line.lower() or 'insert' in line.lower():
                    instructions.append({
                        "type": "add",
                        "instruction": line
                    })
                elif 'remove' in line.lower() or 'delete' in line.lower():
                    instructions.append({
                        "type": "remove",
                        "instruction": line
                    })
                else:
                    instructions.append({
                        "type": "general",
                        "instruction": line
                    })
        
        return instructions
    
    def _parse_redirect_target(self, feedback: Optional[str]) -> Optional[str]:
        """
        Parse redirect target from feedback
        
        Returns:
            Flow name to redirect to
        """
        if not feedback:
            return None
        
        feedback_lower = feedback.lower()
        
        # Look for flow type mentions
        if 'technical' in feedback_lower:
            return 'technical'
        elif 'viral' in feedback_lower:
            return 'viral'
        elif 'research' in feedback_lower:
            return 'research'
        elif 'standard' in feedback_lower:
            return 'standard'
        
        # Look for explicit redirect patterns
        for flow_name in self.available_flows:
            if flow_name in feedback_lower:
                return flow_name
        
        return None
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of feedback processing"""
        return {
            "flow_id": self.state.flow_id,
            "total_revisions": self.state.revision_count,
            "total_revision_time": self.state.total_revisions_time,
            "revision_history": self.state.revision_history,
            "redirect_occurred": self.state.redirect_flow_path is not None,
            "redirect_details": {
                "from": self.state.original_flow_path,
                "to": self.state.redirect_flow_path,
                "reason": self.state.redirect_reason
            } if self.state.redirect_flow_path else None
        }