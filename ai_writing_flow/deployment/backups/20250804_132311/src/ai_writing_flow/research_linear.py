"""
Linear Research Execution - replaces @listen("conduct_research") 

This module implements research stage execution without circular dependencies,
with circuit breaker protection and completion tracking.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.models.flow_control_state import FlowControlState
from ai_writing_flow.managers.stage_manager import StageManager
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerError
from ai_writing_flow.flow_inputs import FlowPathConfig

logger = logging.getLogger(__name__)


class ResearchResult:
    """Research execution result"""
    
    def __init__(self):
        self.sources: List[Dict[str, str]] = []
        self.summary: str = ""
        self.key_insights: List[str] = []
        self.data_points: List[Dict[str, Any]] = []
        self.methodology: str = ""
        self.completion_time: Optional[datetime] = None
        self.fallback_used: bool = False


class LinearResearchExecutor:
    """
    Linear research execution replacing @listen("conduct_research")
    
    Features:
    - No circular dependencies
    - Circuit breaker protection
    - Completion state tracking
    - Skip logic for ORIGINAL content
    - Retry mechanism integration
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
        self._completion_cache: Dict[str, ResearchResult] = {}
    
    def should_execute_research(self, writing_state) -> bool:
        """
        Determine if research should be executed based on state and config
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            True if research should be executed
        """
        
        # Skip if configured to skip
        if self.config.skip_research:
            logger.info("⏭️ Skipping research phase - configured to skip")
            return False
        
        # Skip for ORIGINAL content unless explicitly requested
        if writing_state.content_ownership == "ORIGINAL":
            logger.info("⏭️ Skipping research phase for ORIGINAL content")
            return False
        
        # Check if already completed
        if self._is_research_completed(writing_state):
            logger.info("⏭️ Research already completed, skipping...")
            return False
        
        # Check if research agent already executed
        if "research_agent" in writing_state.agents_executed:
            logger.warning("⚠️ Research agent already executed, skipping to prevent duplicate")
            return False
        
        logger.info("🔍 Research phase will be executed")
        return True
    
    def execute_research(self, writing_state) -> ResearchResult:
        """
        Execute research phase with circuit breaker protection
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            ResearchResult with findings
            
        Raises:
            CircuitBreakerError: If circuit breaker is open
            RuntimeError: If research execution fails
        """
        
        logger.info("🔍 Executing research phase...")
        
        # Check completion state first
        if self._is_research_completed(writing_state):
            cached_result = self._get_cached_result(writing_state)
            if cached_result:
                logger.info("✅ Using cached research result")
                return cached_result
        
        try:
            # Execute with circuit breaker protection
            result = self.circuit_breaker.call(
                self._execute_research_core,
                writing_state=writing_state
            )
            
            # Update state with results
            self._update_writing_state(writing_state, result)
            
            # Cache result
            self._cache_result(writing_state, result)
            
            # Mark completion
            self._mark_research_completed(writing_state)
            
            logger.info("✅ Research phase completed successfully")
            return result
            
        except CircuitBreakerError as e:
            logger.error(f"🔌 Research circuit breaker open: {e}")
            
            # Use fallback research
            fallback_result = self._research_fallback(writing_state, str(e))
            self._update_writing_state(writing_state, fallback_result)
            self._mark_research_completed(writing_state)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Research execution failed: {str(e)}", exc_info=True)
            
            # Try fallback before failing
            try:
                fallback_result = self._research_fallback(writing_state, str(e))
                self._update_writing_state(writing_state, fallback_result)
                self._mark_research_completed(writing_state)
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"❌ Research fallback also failed: {fallback_error}")
                raise RuntimeError(f"Research execution failed: {str(e)}") from e
    
    def _execute_research_core(self, writing_state) -> ResearchResult:
        """
        Core research execution logic (mocked for now)
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            ResearchResult with findings
        """
        
        result = ResearchResult()
        
        # Mock research execution (replace with actual crew execution)
        logger.info(f"📚 Researching topic: {writing_state.topic_title}")
        logger.info(f"📁 Sources path: {writing_state.file_path}")
        
        # Simulate research process
        result.sources = [
            {
                "url": "https://example.com/source1",
                "title": f"Research on {writing_state.topic_title}",
                "date": datetime.now(timezone.utc).isoformat(),
                "type": "article"
            }
        ]
        
        result.summary = f"Research summary for {writing_state.topic_title}"
        result.key_insights = [
            f"Key insight 1 about {writing_state.topic_title}",
            f"Key insight 2 about {writing_state.topic_title}"
        ]
        
        result.data_points = [
            {
                "metric": "engagement_rate",
                "value": "5.2%",
                "source": "industry_report"
            }
        ]
        
        result.methodology = "Comprehensive analysis of available sources"
        result.completion_time = datetime.now(timezone.utc)
        
        logger.info(f"📊 Research completed: {len(result.sources)} sources, {len(result.key_insights)} insights")
        
        return result
    
    def _research_fallback(self, writing_state, error: str) -> ResearchResult:
        """
        Fallback research when main research fails
        
        Args:
            writing_state: Current WritingFlowState
            error: Error that triggered fallback
            
        Returns:
            ResearchResult with fallback data
        """
        
        logger.info("🔄 Using research fallback strategy")
        
        result = ResearchResult()
        result.fallback_used = True
        result.sources = []
        result.summary = f"Research unavailable for {writing_state.topic_title}. Please verify content manually."
        result.key_insights = [
            "Manual research recommended",
            "Verify content accuracy before publication"
        ]
        result.data_points = []
        result.methodology = f"Fallback mode due to: {error}"
        result.completion_time = datetime.now(timezone.utc)
        
        return result
    
    def _is_research_completed(self, writing_state) -> bool:
        """Check if research is already completed"""
        
        # Check stage manager completion
        stage_result = self.stage_manager.get_stage_result(FlowStage.RESEARCH)
        if stage_result and stage_result.status.value == "SUCCESS":
            return True
        
        # Check writing state
        return (
            bool(writing_state.research_sources) or 
            bool(writing_state.research_summary) or
            "research_agent" in writing_state.agents_executed
        )
    
    def _get_cached_result(self, writing_state) -> Optional[ResearchResult]:
        """Get cached research result if available"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.file_path}"
        return self._completion_cache.get(cache_key)
    
    def _cache_result(self, writing_state, result: ResearchResult) -> None:
        """Cache research result for potential reuse"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.file_path}"
        self._completion_cache[cache_key] = result
    
    def _update_writing_state(self, writing_state, result: ResearchResult) -> None:
        """Update WritingFlowState with research results"""
        
        writing_state.research_sources = result.sources
        writing_state.research_summary = result.summary
        
        # Add to execution history
        if "research_agent" not in writing_state.agents_executed:
            writing_state.agents_executed.append("research_agent")
        
        # Update current stage
        writing_state.current_stage = "research_completed"
        
        logger.info("📊 WritingFlowState updated with research results")
    
    def _mark_research_completed(self, writing_state) -> None:
        """Mark research as completed in stage manager"""
        
        self.stage_manager.complete_stage(
            FlowStage.RESEARCH,
            success=True,
            result={
                "sources_count": len(writing_state.research_sources),
                "summary_length": len(writing_state.research_summary),
                "completion_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info("✅ Research stage marked as completed")
    
    def get_research_status(self, writing_state) -> Dict[str, Any]:
        """
        Get comprehensive research execution status
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            Dict with research status information
        """
        
        stage_result = self.stage_manager.get_stage_result(FlowStage.RESEARCH)
        
        return {
            "should_execute": self.should_execute_research(writing_state),
            "is_completed": self._is_research_completed(writing_state),
            "has_cached_result": self._get_cached_result(writing_state) is not None,
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "stage_result": stage_result.dict() if stage_result else None,
            "sources_count": len(writing_state.research_sources),
            "has_summary": bool(writing_state.research_summary),
            "agents_executed": writing_state.agents_executed
        }


# Export main classes
__all__ = [
    "LinearResearchExecutor",
    "ResearchResult"
]