"""
Linear Audience Alignment Execution - replaces @listen("align_audience")

This module implements audience alignment stage execution without circular dependencies,
with error handling and state integration.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.managers.stage_manager import StageManager
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerError
from ai_writing_flow.flow_inputs import FlowPathConfig

logger = logging.getLogger(__name__)


class AudienceAlignmentResult:
    """Audience alignment execution result"""
    
    def __init__(self):
        self.technical_founder_score: float = 0.0
        self.startup_ecosystem_score: float = 0.0
        self.investor_score: float = 0.0
        self.general_business_score: float = 0.0
        self.recommended_depth_level: int = 1
        self.audience_insights: str = ""
        self.target_adjustments: List[str] = []
        self.completion_time: Optional[datetime] = None
        self.fallback_used: bool = False


class LinearAudienceExecutor:
    """
    Linear audience alignment execution replacing @listen("align_audience")
    
    Features:
    - Always executes (no skip logic)
    - Graceful error handling with fallback
    - State integration and updates
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
        self._completion_cache: Dict[str, AudienceAlignmentResult] = {}
    
    def should_execute_audience_alignment(self, writing_state) -> bool:
        """
        Determine if audience alignment should be executed
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            True if audience alignment should be executed
        """
        
        # Skip if configured to skip
        if self.config.skip_audience_alignment:
            logger.info("⏭️ Skipping audience alignment - configured to skip")
            return False
        
        # Check if already completed
        if self._is_audience_completed(writing_state):
            logger.info("⏭️ Audience alignment already completed")
            return False
        
        logger.info("👥 Audience alignment will be executed")
        return True
    
    def execute_audience_alignment(self, writing_state) -> AudienceAlignmentResult:
        """
        Execute audience alignment with error handling
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            AudienceAlignmentResult with alignment data
        """
        
        logger.info("👥 Executing audience alignment...")
        
        # Check if already completed
        if self._is_audience_completed(writing_state):
            cached_result = self._get_cached_result(writing_state)
            if cached_result:
                logger.info("✅ Using cached audience alignment result")
                return cached_result
        
        try:
            # Execute with circuit breaker protection
            result = self.circuit_breaker.call(
                self._execute_audience_core,
                writing_state=writing_state
            )
            
            # Update state with results
            self._update_writing_state(writing_state, result)
            
            # Cache result
            self._cache_result(writing_state, result)
            
            # Mark completion
            self._mark_audience_completed(writing_state)
            
            logger.info("✅ Audience alignment completed successfully")
            return result
            
        except CircuitBreakerError as e:
            logger.error(f"🔌 Audience alignment circuit breaker open: {e}")
            
            # Use fallback
            fallback_result = self._audience_fallback(writing_state, str(e))
            self._update_writing_state(writing_state, fallback_result)
            self._mark_audience_completed(writing_state)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Audience alignment failed: {str(e)}", exc_info=True)
            
            # Graceful failure - use fallback
            fallback_result = self._audience_fallback(writing_state, str(e))
            self._update_writing_state(writing_state, fallback_result)
            self._mark_audience_completed(writing_state)
            
            logger.warning("⚠️ Using fallback audience alignment due to error")
            return fallback_result
    
    def _execute_audience_core(self, writing_state) -> AudienceAlignmentResult:
        """
        Core audience alignment logic (mocked for now)
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            AudienceAlignmentResult with alignment scores
        """
        
        result = AudienceAlignmentResult()
        
        logger.info(f"👥 Analyzing audience for: {writing_state.topic_title}")
        logger.info(f"🎯 Platform: {writing_state.platform}")
        logger.info(f"📊 Viral score: {writing_state.viral_score}")
        
        # Mock audience analysis (replace with actual crew execution)
        
        # Platform-specific scoring
        if writing_state.platform == "LinkedIn":
            result.technical_founder_score = 0.8
            result.startup_ecosystem_score = 0.9
            result.investor_score = 0.7
            result.general_business_score = 0.6
            result.recommended_depth_level = 2
            
        elif writing_state.platform == "Twitter":
            result.technical_founder_score = 0.7
            result.startup_ecosystem_score = 0.6
            result.investor_score = 0.5
            result.general_business_score = 0.8
            result.recommended_depth_level = 1
            
        elif writing_state.platform == "Blog":
            result.technical_founder_score = 0.9
            result.startup_ecosystem_score = 0.8
            result.investor_score = 0.8
            result.general_business_score = 0.7
            result.recommended_depth_level = 3
            
        else:
            # Default scoring
            result.technical_founder_score = 0.6
            result.startup_ecosystem_score = 0.6
            result.investor_score = 0.5
            result.general_business_score = 0.7
            result.recommended_depth_level = 2
        
        # Viral score adjustments
        if writing_state.viral_score >= 8.0:
            # High viral potential - broaden appeal
            result.general_business_score += 0.2
            result.recommended_depth_level = min(result.recommended_depth_level, 2)
            
        elif writing_state.viral_score <= 3.0:
            # Low viral potential - focus on technical audience
            result.technical_founder_score += 0.2
            result.recommended_depth_level = max(result.recommended_depth_level, 2)
        
        # Content type adjustments
        if writing_state.content_type == "SERIES":
            result.recommended_depth_level += 1  # Series can be more detailed
        
        # Generate insights
        result.audience_insights = self._generate_insights(result, writing_state)
        result.target_adjustments = self._generate_adjustments(result, writing_state)
        result.completion_time = datetime.now(timezone.utc)
        
        logger.info(f"👥 Audience scores calculated: TF={result.technical_founder_score:.2f}, SE={result.startup_ecosystem_score:.2f}")
        
        return result
    
    def _generate_insights(self, result: AudienceAlignmentResult, writing_state) -> str:
        """Generate audience insights based on scores"""
        
        insights = []
        
        # Primary audience identification
        scores = {
            "Technical Founders": result.technical_founder_score,
            "Startup Ecosystem": result.startup_ecosystem_score,
            "Investors": result.investor_score,
            "General Business": result.general_business_score
        }
        
        primary_audience = max(scores, key=scores.get)
        insights.append(f"Primary audience: {primary_audience} (score: {scores[primary_audience]:.2f})")
        
        # Depth level reasoning
        depth_map = {1: "Introductory", 2: "Moderate", 3: "Advanced"}
        depth_desc = depth_map.get(result.recommended_depth_level, "Custom")
        insights.append(f"Recommended depth: {depth_desc} (level {result.recommended_depth_level})")
        
        # Platform-specific insights
        insights.append(f"Platform optimization: Content tailored for {writing_state.platform} audience")
        
        # Viral potential insights
        if writing_state.viral_score >= 8.0:
            insights.append("High viral potential - content should appeal to broader audience")
        elif writing_state.viral_score <= 3.0:
            insights.append("Low viral potential - focus on niche technical audience")
        
        return " | ".join(insights)
    
    def _generate_adjustments(self, result: AudienceAlignmentResult, writing_state) -> List[str]:
        """Generate target adjustments based on analysis"""
        
        adjustments = []
        
        # Depth adjustments
        if result.recommended_depth_level >= 3:
            adjustments.append("Include technical details and implementation specifics")
        elif result.recommended_depth_level <= 1:
            adjustments.append("Keep explanations simple and avoid technical jargon")
        
        # Audience-specific adjustments
        if result.technical_founder_score > 0.8:
            adjustments.append("Include coding examples and technical architecture insights")
        
        if result.investor_score > 0.7:
            adjustments.append("Emphasize business metrics and market opportunities")
        
        if result.general_business_score > 0.8:
            adjustments.append("Focus on business impact and practical applications")
        
        # Platform adjustments
        if writing_state.platform == "Twitter":
            adjustments.append("Use concise language and thread-friendly format")
        elif writing_state.platform == "LinkedIn":
            adjustments.append("Professional tone with industry insights")
        elif writing_state.platform == "Blog":
            adjustments.append("Comprehensive coverage with detailed examples")
        
        return adjustments
    
    def _audience_fallback(self, writing_state, error: str) -> AudienceAlignmentResult:
        """
        Fallback audience alignment when main alignment fails
        
        Args:
            writing_state: Current WritingFlowState
            error: Error that triggered fallback
            
        Returns:
            AudienceAlignmentResult with fallback data
        """
        
        logger.info("🔄 Using audience alignment fallback strategy")
        
        result = AudienceAlignmentResult()
        result.fallback_used = True
        
        # Default balanced scoring
        result.technical_founder_score = 0.6
        result.startup_ecosystem_score = 0.6
        result.investor_score = 0.5
        result.general_business_score = 0.7
        result.recommended_depth_level = 2
        
        result.audience_insights = f"Fallback audience alignment used due to: {error}"
        result.target_adjustments = [
            "Manual audience review recommended",
            "Verify content targeting before publication"
        ]
        result.completion_time = datetime.now(timezone.utc)
        
        return result
    
    def _is_audience_completed(self, writing_state) -> bool:
        """Check if audience alignment is already completed"""
        
        # Check stage manager completion
        stage_result = self.stage_manager.get_stage_result(FlowStage.AUDIENCE_ALIGN)
        if stage_result and stage_result.status.value == "SUCCESS":
            return True
        
        # Check writing state
        return (
            writing_state.current_stage == "audience_alignment_completed" or
            bool(writing_state.audience_scores) or
            bool(writing_state.audience_insights)
        )
    
    def _get_cached_result(self, writing_state) -> Optional[AudienceAlignmentResult]:
        """Get cached audience result if available"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}_{writing_state.viral_score}"
        return self._completion_cache.get(cache_key)
    
    def _cache_result(self, writing_state, result: AudienceAlignmentResult) -> None:
        """Cache audience result for potential reuse"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}_{writing_state.viral_score}"
        self._completion_cache[cache_key] = result
    
    def _update_writing_state(self, writing_state, result: AudienceAlignmentResult) -> None:
        """Update WritingFlowState with audience alignment results"""
        
        writing_state.audience_scores = {
            "technical_founder": result.technical_founder_score,
            "startup_ecosystem": result.startup_ecosystem_score,
            "investor": result.investor_score,
            "general_business": result.general_business_score
        }
        
        writing_state.audience_insights = result.audience_insights
        writing_state.target_depth_level = result.recommended_depth_level
        
        # Add to execution history
        if "audience_agent" not in writing_state.agents_executed:
            writing_state.agents_executed.append("audience_agent")
        
        # Update current stage
        writing_state.current_stage = "audience_alignment_completed"
        
        logger.info("👥 WritingFlowState updated with audience alignment results")
    
    def _mark_audience_completed(self, writing_state) -> None:
        """Mark audience alignment as completed in stage manager"""
        
        self.stage_manager.complete_stage(
            FlowStage.AUDIENCE_ALIGN,
            success=True,
            result={
                "primary_audience": max(writing_state.audience_scores, key=writing_state.audience_scores.get),
                "depth_level": writing_state.target_depth_level,
                "completion_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info("✅ Audience alignment stage marked as completed")
    
    def get_audience_status(self, writing_state) -> Dict[str, Any]:
        """
        Get comprehensive audience alignment status
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            Dict with audience status information
        """
        
        stage_result = self.stage_manager.get_stage_result(FlowStage.AUDIENCE_ALIGN)
        
        return {
            "should_execute": self.should_execute_audience_alignment(writing_state),
            "is_completed": self._is_audience_completed(writing_state),
            "has_cached_result": self._get_cached_result(writing_state) is not None,
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "stage_result": stage_result.dict() if stage_result else None,
            "current_scores": writing_state.audience_scores,
            "depth_level": writing_state.target_depth_level,
            "has_insights": bool(writing_state.audience_insights)
        }


# Export main classes
__all__ = [
    "LinearAudienceExecutor",
    "AudienceAlignmentResult"
]