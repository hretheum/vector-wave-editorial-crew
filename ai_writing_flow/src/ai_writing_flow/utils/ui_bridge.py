"""
UI Bridge - Interface between AI Writing Flow and frontend
"""

from typing import Dict, Any, Optional
import json
import asyncio
from datetime import datetime
import logging

from ..models import HumanFeedbackDecision, WritingFlowState

logger = logging.getLogger(__name__)


class UIBridge:
    """Bridge for communication with UI"""
    
    def __init__(self):
        self.pending_feedback = {}
        self.draft_reviews = {}
        self.completion_callbacks = {}
        
    def send_draft_for_review(self, draft: str, metadata: Dict[str, Any]) -> str:
        """Send draft to UI for human review"""
        review_id = f"review_{datetime.now().timestamp()}"
        
        self.draft_reviews[review_id] = {
            "draft": draft,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
            "status": "pending_review"
        }
        
        logger.info(f"📤 Sent draft for review: {review_id}")
        logger.info(f"   Word count: {metadata.get('word_count', 0)}")
        logger.info(f"   Structure: {metadata.get('structure_type', 'unknown')}")
        
        # In production, this would trigger a WebSocket event or API call
        # For now, we'll log the draft
        logger.debug(f"Draft preview: {draft[:200]}...")
        
        return review_id
    
    def get_human_feedback(self, timeout: int = 300) -> Optional[HumanFeedbackDecision]:
        """Wait for human feedback (mock implementation)"""
        logger.info("⏳ Waiting for human feedback...")
        
        # In production, this would wait for actual user input
        # For now, we'll simulate different feedback scenarios
        
        # Simulate waiting
        import time
        time.sleep(2)
        
        # Mock feedback based on random selection
        import random
        feedback_type = random.choice(["minor", "major", "pivot"])
        
        feedback_messages = {
            "minor": "Please adjust the tone to be more technical",
            "major": "Need to restructure around practical examples",
            "pivot": "Let's focus on implementation challenges instead"
        }
        
        feedback = HumanFeedbackDecision(
            feedback_type=feedback_type,
            feedback_text=feedback_messages[feedback_type],
            specific_changes=["Add more code examples"] if feedback_type == "minor" else None,
            continue_to_stage="generate_draft" if feedback_type != "pivot" else "conduct_research"
        )
        
        logger.info(f"📥 Received feedback: {feedback_type} - {feedback.feedback_text}")
        
        return feedback
    
    def escalate_to_human(self, reason: str) -> None:
        """Escalate to human for intervention"""
        logger.warning(f"🚨 ESCALATION: {reason}")
        
        escalation = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "severity": "high",
            "action_required": "manual_review"
        }
        
        # In production, this would notify the user via UI
        logger.info(f"Escalation details: {json.dumps(escalation, indent=2)}")
    
    def request_human_review(self, quality_result: Any) -> None:
        """Request human review for quality issues"""
        logger.info("🔍 Requesting human quality review")
        
        review_request = {
            "timestamp": datetime.now().isoformat(),
            "quality_score": quality_result.quality_score,
            "issues": quality_result.improvement_suggestions,
            "requires_immediate_attention": quality_result.requires_human_review
        }
        
        # In production, this would create a review task in UI
        logger.info(f"Review request: {json.dumps(review_request, indent=2)}")
    
    def send_completion_notice(self, state: WritingFlowState) -> None:
        """Notify UI of flow completion"""
        logger.info("✅ Sending completion notice to UI")
        
        completion_data = {
            "flow_id": f"flow_{datetime.now().timestamp()}",
            "topic": state.topic_title,
            "platform": state.platform,
            "final_draft": state.final_draft,
            "metrics": {
                "quality_score": state.quality_score,
                "style_score": state.style_score,
                "revision_count": state.revision_count,
                "processing_time": state.total_processing_time,
                "agents_executed": len(state.agents_executed)
            },
            "metadata": state.publication_metadata,
            "timestamp": datetime.now().isoformat()
        }
        
        # In production, this would send completion event to UI
        logger.info(f"Flow completed successfully!")
        logger.info(f"  Topic: {state.topic_title}")
        logger.info(f"  Quality Score: {state.quality_score}")
        logger.info(f"  Processing Time: {state.total_processing_time}s")
    
    async def stream_progress(self, stage: str, message: str) -> None:
        """Stream progress updates to UI"""
        progress_update = {
            "type": "progress",
            "stage": stage,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # In production, this would use WebSocket or SSE
        logger.info(f"📊 Progress: [{stage}] {message}")
        
        # Simulate async operation
        await asyncio.sleep(0.1)
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences for content generation"""
        # In production, this would fetch from user settings
        return {
            "preferred_tone": "technical_but_accessible",
            "include_code_examples": True,
            "max_controversy_score": 0.3,
            "require_sources": True,
            "auto_approve_threshold": 85
        }
    
    def save_draft_version(self, draft: str, version: int, stage: str) -> None:
        """Save draft version for history"""
        version_data = {
            "version": version,
            "stage": stage,
            "draft": draft,
            "timestamp": datetime.now().isoformat(),
            "word_count": len(draft.split())
        }
        
        # In production, this would save to database
        logger.debug(f"💾 Saved draft version {version} at stage: {stage}")


# Singleton instance
_ui_bridge_instance = None

def get_ui_bridge() -> UIBridge:
    """Get or create UI Bridge singleton"""
    global _ui_bridge_instance
    if _ui_bridge_instance is None:
        _ui_bridge_instance = UIBridge()
    return _ui_bridge_instance