"""
Linear Draft Generation Execution - replaces @listen("generate_draft")

This module implements draft generation stage execution without circular dependencies,
with human review checkpoint and draft versioning.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.managers.stage_manager import StageManager
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerError
from ai_writing_flow.flow_inputs import FlowPathConfig

logger = logging.getLogger(__name__)


class DraftGenerationResult:
    """Draft generation execution result"""
    
    def __init__(self):
        self.draft_content: str = ""
        self.version_number: int = 1
        self.word_count: int = 0
        self.platform_optimized: bool = False
        self.audience_targeted: bool = False
        self.generation_metadata: Dict[str, Any] = {}
        self.completion_time: Optional[datetime] = None
        self.fallback_used: bool = False
        self.requires_human_review: bool = True


class HumanReviewCheckpoint:
    """Human review checkpoint data"""
    
    def __init__(self):
        self.review_required: bool = True
        self.auto_approve_eligible: bool = False
        self.quality_score: float = 0.0
        self.review_criteria: List[str] = []
        self.checkpoint_time: Optional[datetime] = None


class LinearDraftExecutor:
    """
    Linear draft generation execution replacing @listen("generate_draft")
    
    Features:
    - No circular dependencies or loops
    - Clean retry logic with version tracking
    - Human review checkpoint integration
    - Draft versioning system
    - Circuit breaker protection
    """
    
    def __init__(
        self,
        stage_manager: StageManager,
        circuit_breaker: StageCircuitBreaker,
        config: FlowPathConfig
    ):
        self.stage_manager = stage_manager
        self.circuit_breaker = circuit_breaker
        self.config = config
        self._draft_versions: Dict[str, List[str]] = {}
        self._review_checkpoints: Dict[str, HumanReviewCheckpoint] = {}
    
    def should_execute_draft_generation(self, writing_state) -> bool:
        """
        Determine if draft generation should be executed
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            True if draft generation should be executed
        """
        
        # Always execute if no current draft exists
        if not writing_state.current_draft:
            logger.info("📝 Draft generation will be executed - no existing draft")
            return True
        
        # Check if we need a new version due to changes
        if self._requires_new_draft_version(writing_state):
            logger.info("📝 Draft generation will be executed - new version needed")
            return True
        
        logger.info("⏭️ Draft generation not needed - current draft exists")
        return False
    
    def execute_draft_generation(self, writing_state) -> DraftGenerationResult:
        """
        Execute draft generation with retry logic and versioning
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            DraftGenerationResult with generated content
        """
        
        logger.info("📝 Executing draft generation...")
        
        try:
            # Execute with circuit breaker protection
            result = self.circuit_breaker.call(
                self._execute_draft_core,
                writing_state=writing_state
            )
            
            # Version the draft
            self._version_draft(writing_state, result)
            
            # Update state with results
            self._update_writing_state(writing_state, result)
            
            # Create human review checkpoint
            checkpoint = self._create_review_checkpoint(writing_state, result)
            self._store_review_checkpoint(writing_state, checkpoint)
            
            # Mark completion
            self._mark_draft_completed(writing_state, result)
            
            logger.info("✅ Draft generation completed successfully")
            return result
            
        except CircuitBreakerError as e:
            logger.error(f"🔌 Draft generation circuit breaker open: {e}")
            
            # Use fallback
            fallback_result = self._draft_fallback(writing_state, str(e))
            self._version_draft(writing_state, fallback_result)
            self._update_writing_state(writing_state, fallback_result)
            self._mark_draft_completed(writing_state, fallback_result)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Draft generation failed: {str(e)}", exc_info=True)
            
            # Use fallback
            fallback_result = self._draft_fallback(writing_state, str(e))
            self._version_draft(writing_state, fallback_result)
            self._update_writing_state(writing_state, fallback_result)
            self._mark_draft_completed(writing_state, fallback_result)
            
            return fallback_result
    
    def _execute_draft_core(self, writing_state) -> DraftGenerationResult:
        """
        Core draft generation logic (mocked for now)
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            DraftGenerationResult with generated content
        """
        
        result = DraftGenerationResult()
        
        logger.info(f"📝 Generating draft for: {writing_state.topic_title}")
        logger.info(f"🎯 Platform: {writing_state.platform}")
        logger.info(f"👥 Target depth: {writing_state.target_depth_level}")
        
        # Mock draft generation (replace with actual crew execution)
        
        # Generate content based on platform
        if writing_state.platform == "Twitter":
            result.draft_content = self._generate_twitter_draft(writing_state)
        elif writing_state.platform == "LinkedIn":
            result.draft_content = self._generate_linkedin_draft(writing_state)
        elif writing_state.platform == "Blog":
            result.draft_content = self._generate_blog_draft(writing_state)
        else:
            result.draft_content = self._generate_default_draft(writing_state)
        
        # Calculate metadata
        result.word_count = len(result.draft_content.split())
        result.platform_optimized = True
        result.audience_targeted = bool(writing_state.audience_scores)
        
        result.generation_metadata = {
            "research_sources_used": len(writing_state.research_sources),
            "audience_scores": writing_state.audience_scores,
            "depth_level": writing_state.target_depth_level,
            "platform": writing_state.platform,
            "viral_score": writing_state.viral_score
        }
        
        result.completion_time = datetime.now(timezone.utc)
        result.requires_human_review = self._determine_review_requirement(writing_state, result)
        
        logger.info(f"📊 Draft generated: {result.word_count} words, review required: {result.requires_human_review}")
        
        return result
    
    def _generate_twitter_draft(self, writing_state) -> str:
        """Generate Twitter-optimized draft"""
        
        # Twitter format: concise, thread-friendly
        draft = f"🧵 Thread about {writing_state.topic_title}\n\n"
        draft += f"1/ {writing_state.topic_title} is revolutionizing how we think about [topic area].\n\n"
        
        if writing_state.research_summary:
            draft += f"2/ Key insight: {writing_state.research_summary[:100]}...\n\n"
        
        if writing_state.audience_insights:
            draft += f"3/ Why this matters: {writing_state.audience_insights[:100]}...\n\n"
        
        draft += f"4/ What's your take on {writing_state.topic_title}? Share your thoughts! 👇"
        
        return draft
    
    def _generate_linkedin_draft(self, writing_state) -> str:
        """Generate LinkedIn-optimized draft"""
        
        # LinkedIn format: professional, detailed
        draft = f"# {writing_state.topic_title}: Industry Insights\n\n"
        
        if writing_state.research_summary:
            draft += f"## Research Findings\n{writing_state.research_summary}\n\n"
        
        if writing_state.audience_insights:
            draft += f"## Industry Impact\n{writing_state.audience_insights}\n\n"
        
        draft += f"## Key Takeaways\n"
        draft += f"• Innovation in {writing_state.topic_title} is accelerating\n"
        draft += f"• Market implications are significant\n"
        draft += f"• Leaders should consider strategic adoption\n\n"
        
        draft += f"What's your experience with {writing_state.topic_title}? Let's discuss in the comments.\n\n"
        draft += f"#innovation #technology #business"
        
        return draft
    
    def _generate_blog_draft(self, writing_state) -> str:
        """Generate Blog-optimized draft"""
        
        # Blog format: comprehensive, structured
        draft = f"# {writing_state.topic_title}: A Comprehensive Analysis\n\n"
        draft += f"## Introduction\n\n"
        draft += f"In this article, we'll explore {writing_state.topic_title} and its implications for the industry.\n\n"
        
        if writing_state.research_summary:
            draft += f"## Background Research\n\n{writing_state.research_summary}\n\n"
        
        if writing_state.audience_insights:
            draft += f"## Audience Analysis\n\n{writing_state.audience_insights}\n\n"
        
        draft += f"## Technical Deep Dive\n\n"
        draft += f"[Technical content about {writing_state.topic_title} would go here]\n\n"
        
        draft += f"## Business Implications\n\n"
        draft += f"[Business analysis would go here]\n\n"
        
        draft += f"## Conclusion\n\n"
        draft += f"{writing_state.topic_title} represents a significant opportunity for innovation and growth.\n\n"
        
        return draft
    
    def _generate_default_draft(self, writing_state) -> str:
        """Generate default format draft"""
        
        draft = f"# {writing_state.topic_title}\n\n"
        
        if writing_state.research_summary:
            draft += f"## Overview\n{writing_state.research_summary}\n\n"
        
        if writing_state.audience_insights:
            draft += f"## Analysis\n{writing_state.audience_insights}\n\n"
        
        draft += f"## Summary\n"
        draft += f"This analysis of {writing_state.topic_title} provides valuable insights for stakeholders.\n"
        
        return draft
    
    def _determine_review_requirement(self, writing_state, result: DraftGenerationResult) -> bool:
        """Determine if human review is required"""
        
        # Always require review if configured
        if self.config.require_human_approval:
            return True
        
        # Auto-approve for low-risk content
        if (writing_state.viral_score <= 3.0 and 
            result.word_count < 100 and 
            writing_state.platform == "Twitter"):
            return False
        
        # High viral score always needs review
        if writing_state.viral_score >= 8.0:
            return True
        
        # Series content needs review
        if writing_state.content_type == "SERIES":
            return True
        
        return True
    
    def _create_review_checkpoint(self, writing_state, result: DraftGenerationResult) -> HumanReviewCheckpoint:
        """Create human review checkpoint"""
        
        checkpoint = HumanReviewCheckpoint()
        checkpoint.review_required = result.requires_human_review
        checkpoint.auto_approve_eligible = (
            writing_state.viral_score < self.config.auto_approve_threshold and
            result.word_count < 500
        )
        
        # Mock quality score calculation
        checkpoint.quality_score = min(10.0, 
            (writing_state.viral_score * 0.4) + 
            (len(writing_state.research_sources) * 0.5) +
            (5.0 if result.audience_targeted else 0.0)
        )
        
        checkpoint.review_criteria = [
            "Content accuracy and factual verification",
            "Audience targeting alignment",
            "Platform optimization compliance",
            "Brand voice and tone consistency"
        ]
        
        if writing_state.viral_score >= 8.0:
            checkpoint.review_criteria.append("High viral potential - extra scrutiny required")
        
        checkpoint.checkpoint_time = datetime.now(timezone.utc)
        
        return checkpoint
    
    def _version_draft(self, writing_state, result: DraftGenerationResult) -> None:
        """Add draft to version history"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        
        if cache_key not in self._draft_versions:
            self._draft_versions[cache_key] = []
        
        self._draft_versions[cache_key].append(result.draft_content)
        result.version_number = len(self._draft_versions[cache_key])
        
        # Also update writing state draft versions
        writing_state.draft_versions.append(result.draft_content)
        
        logger.info(f"📝 Draft versioned: v{result.version_number}")
    
    def _store_review_checkpoint(self, writing_state, checkpoint: HumanReviewCheckpoint) -> None:
        """Store human review checkpoint"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        self._review_checkpoints[cache_key] = checkpoint
        
        logger.info(f"🔍 Review checkpoint created: quality_score={checkpoint.quality_score:.1f}")
    
    def _requires_new_draft_version(self, writing_state) -> bool:
        """Check if a new draft version is needed"""
        
        # Need new version if audience or research data changed
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        
        if cache_key not in self._draft_versions:
            return True
        
        # Check if we have feedback requiring new version
        if writing_state.human_feedback_type in ["major", "pivot"]:
            return True
        
        return False
    
    def _draft_fallback(self, writing_state, error: str) -> DraftGenerationResult:
        """Fallback draft when main generation fails"""
        
        logger.info("🔄 Using draft generation fallback strategy")
        
        result = DraftGenerationResult()
        result.fallback_used = True
        result.requires_human_review = True
        
        # Generate minimal fallback content
        result.draft_content = f"# {writing_state.topic_title}\n\n"
        result.draft_content += f"[Draft generation temporarily unavailable - manual content creation required]\n\n"
        result.draft_content += f"Topic: {writing_state.topic_title}\n"
        result.draft_content += f"Platform: {writing_state.platform}\n"
        result.draft_content += f"Fallback reason: {error}\n\n"
        result.draft_content += f"Please create content manually and review before publication."
        
        result.word_count = len(result.draft_content.split())
        result.platform_optimized = False
        result.audience_targeted = False
        result.completion_time = datetime.now(timezone.utc)
        
        return result
    
    def _update_writing_state(self, writing_state, result: DraftGenerationResult) -> None:
        """Update WritingFlowState with draft generation results"""
        
        writing_state.current_draft = result.draft_content
        
        # Add to execution history
        if "writer_agent" not in writing_state.agents_executed:
            writing_state.agents_executed.append("writer_agent")
        
        # Update current stage
        writing_state.current_stage = "draft_generation"
        
        logger.info("📝 WritingFlowState updated with draft generation results")
    
    def _mark_draft_completed(self, writing_state, result: DraftGenerationResult) -> None:
        """Mark draft generation as completed in stage manager"""
        
        self.stage_manager.complete_stage(
            FlowStage.DRAFT_GENERATION,
            success=True,
            result={
                "word_count": result.word_count,
                "version_number": result.version_number,
                "requires_review": result.requires_human_review,
                "completion_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info("✅ Draft generation stage marked as completed")
    
    def get_review_checkpoint(self, writing_state) -> Optional[HumanReviewCheckpoint]:
        """Get human review checkpoint for current draft"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._review_checkpoints.get(cache_key)
    
    def get_draft_versions(self, writing_state) -> List[str]:
        """Get all draft versions for current content"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._draft_versions.get(cache_key, [])
    
    def get_draft_status(self, writing_state) -> Dict[str, Any]:
        """Get comprehensive draft generation status"""
        
        stage_result = self.stage_manager.get_stage_result(FlowStage.DRAFT_GENERATION)
        checkpoint = self.get_review_checkpoint(writing_state)
        
        return {
            "should_execute": self.should_execute_draft_generation(writing_state),
            "current_draft_exists": bool(writing_state.current_draft),
            "draft_word_count": len(writing_state.current_draft.split()) if writing_state.current_draft else 0,
            "version_count": len(self.get_draft_versions(writing_state)),
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "stage_result": stage_result.dict() if stage_result else None,
            "review_checkpoint": {
                "exists": checkpoint is not None,
                "review_required": checkpoint.review_required if checkpoint else True,
                "quality_score": checkpoint.quality_score if checkpoint else 0.0
            } if checkpoint else None
        }


# Export main classes
__all__ = [
    "LinearDraftExecutor",
    "DraftGenerationResult",
    "HumanReviewCheckpoint"
]