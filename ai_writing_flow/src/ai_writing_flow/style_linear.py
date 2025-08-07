"""
Linear Style Validation Execution - Task 16.1

This module implements style validation stage execution without circular dependencies,
with retry limits and escalation pathway.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.managers.stage_manager import StageManager
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerError
from ai_writing_flow.flow_inputs import FlowPathConfig

logger = logging.getLogger(__name__)


class StyleValidationResult:
    """Style validation execution result"""
    
    def __init__(self):
        self.is_compliant: bool = False
        self.compliance_score: float = 0.0
        self.violations: List[Dict[str, str]] = []
        self.forbidden_phrases: List[str] = []
        self.suggestions: List[str] = []
        self.retry_count: int = 0
        self.requires_escalation: bool = False
        self.completion_time: Optional[datetime] = None
        self.fallback_used: bool = False


class StyleEscalation:
    """Style validation escalation data"""
    
    def __init__(self):
        self.escalation_required: bool = False
        self.escalation_reason: str = ""
        self.escalation_level: str = "human_review"  # human_review, expert_review, override
        self.max_retries_exceeded: bool = False
        self.critical_violations: List[str] = []
        self.escalation_time: Optional[datetime] = None


class LinearStyleExecutor:
    """
    Linear style validation execution - Task 16.1
    
    Features:
    - Style validation with retry limits - Task 16.2
    - Escalation pathway for style issues - Task 16.3
    - Circuit breaker protection
    - No circular dependencies
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
        self._retry_history: Dict[str, List[Dict[str, Any]]] = {}
        self._escalation_cache: Dict[str, StyleEscalation] = {}
    
    def should_execute_style_validation(self, writing_state) -> bool:
        """
        Determine if style validation should be executed
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            True if style validation should be executed
        """
        
        # Skip if configured to skip
        if self.config.skip_style_validation:
            logger.info("⏭️ Skipping style validation - configured to skip")
            return False
        
        # Skip if no draft to validate
        if not writing_state.current_draft:
            logger.info("⏭️ Skipping style validation - no draft available")
            return False
        
        # Check if already completed and passed
        if self._is_style_completed_and_passed(writing_state):
            logger.info("⏭️ Style validation already completed successfully")
            return False
        
        logger.info("📏 Style validation will be executed")
        return True
    
    def execute_style_validation(self, writing_state) -> StyleValidationResult:
        """
        Execute style validation with retry logic - Task 16.1 & 16.2
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            StyleValidationResult with validation data
        """
        
        logger.info("📏 Executing style validation with retry logic...")
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        max_retries = self.config.style_max_retries
        
        # Initialize retry history if needed
        if cache_key not in self._retry_history:
            self._retry_history[cache_key] = []
        
        current_retry = len(self._retry_history[cache_key])
        
        # Check if max retries exceeded - Task 16.2
        if current_retry >= max_retries:
            logger.warning(f"⚠️ Style validation max retries ({max_retries}) exceeded")
            return self._handle_max_retries_exceeded(writing_state, cache_key)
        
        try:
            # Execute with circuit breaker protection
            result = self.circuit_breaker.call(
                self._execute_style_core,
                writing_state=writing_state,
                retry_count=current_retry
            )
            
            # Record retry attempt
            self._record_retry_attempt(cache_key, current_retry, result)
            
            # Check if validation passed
            if result.is_compliant:
                logger.info("✅ Style validation passed")
                self._mark_style_completed(writing_state, result)
                return result
            else:
                # Validation failed - check if we should retry - Task 16.2
                if current_retry < max_retries - 1:
                    logger.info(f"🔄 Style validation failed, will retry ({current_retry + 1}/{max_retries})")
                    result.requires_escalation = False
                else:
                    logger.warning("🚨 Style validation failed after all retries - escalation required")
                    result.requires_escalation = True
                    escalation = self._create_escalation(writing_state, result, "max_retries_exceeded")
                    self._store_escalation(cache_key, escalation)
                
                return result
                
        except CircuitBreakerError as e:
            logger.error(f"🔌 Style validation circuit breaker open: {e}")
            
            # Use fallback
            fallback_result = self._style_fallback(writing_state, str(e))
            self._record_retry_attempt(cache_key, current_retry, fallback_result)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Style validation failed: {str(e)}", exc_info=True)
            
            # Record failed attempt
            self._record_retry_attempt(cache_key, current_retry, None, str(e))
            
            # Try fallback or escalate
            if current_retry < max_retries - 1:
                # Will retry on next call
                result = StyleValidationResult()
                result.is_compliant = False
                result.retry_count = current_retry
                result.completion_time = datetime.now(timezone.utc)
                return result
            else:
                # Escalate
                return self._handle_max_retries_exceeded(writing_state, cache_key)
    
    def _execute_style_core(self, writing_state, retry_count: int = 0) -> StyleValidationResult:
        """
        Core style validation logic - Task 16.1
        
        Args:
            writing_state: Current WritingFlowState
            retry_count: Current retry attempt number
            
        Returns:
            StyleValidationResult with validation data
        """
        
        result = StyleValidationResult()
        result.retry_count = retry_count
        
        logger.info(f"📏 Validating style for: {writing_state.topic_title} (attempt {retry_count + 1})")
        logger.info(f"📄 Draft length: {len(writing_state.current_draft)} characters")
        logger.info(f"🎯 Platform: {writing_state.platform}")
        
        # Mock style validation (replace with actual style engine)
        draft_content = writing_state.current_draft.lower()
        
        # Platform-specific style rules
        violations = []
        forbidden_phrases = []
        suggestions = []
        
        if writing_state.platform == "LinkedIn":
            # LinkedIn style rules
            if len(writing_state.current_draft) > 3000:
                violations.append({
                    "type": "length_violation",
                    "message": "LinkedIn posts should be under 3000 characters",
                    "severity": "warning"
                })
            
            if not any(hashtag in draft_content for hashtag in ["#", "hashtag"]):
                suggestions.append("Consider adding relevant hashtags for LinkedIn visibility")
            
            # Forbidden phrases for LinkedIn
            linkedin_forbidden = ["click here", "buy now", "limited offer"]
            for phrase in linkedin_forbidden:
                if phrase in draft_content:
                    forbidden_phrases.append(phrase)
                    violations.append({
                        "type": "forbidden_phrase",
                        "message": f"Phrase '{phrase}' not recommended for LinkedIn",
                        "severity": "error"
                    })
        
        elif writing_state.platform == "Twitter":
            # Twitter style rules
            if len(writing_state.current_draft) > 280:
                violations.append({
                    "type": "length_violation", 
                    "message": "Individual tweets should be under 280 characters",
                    "severity": "error"
                })
            
            if "thread" not in draft_content and len(writing_state.current_draft) > 200:
                suggestions.append("Consider breaking into a thread for better readability")
            
            # Twitter forbidden phrases
            twitter_forbidden = ["follow me", "retweet if"]
            for phrase in twitter_forbidden:
                if phrase in draft_content:
                    forbidden_phrases.append(phrase)
                    violations.append({
                        "type": "forbidden_phrase",
                        "message": f"Phrase '{phrase}' may reduce organic reach",
                        "severity": "warning"
                    })
        
        elif writing_state.platform == "Blog":
            # Blog style rules
            if len(writing_state.current_draft) < 300:
                violations.append({
                    "type": "length_violation",
                    "message": "Blog posts should be at least 300 words for SEO",
                    "severity": "warning"
                })
            
            if "## " not in writing_state.current_draft:
                suggestions.append("Consider adding subheadings (##) for better structure")
            
            # Blog forbidden phrases
            blog_forbidden = ["click bait", "you won't believe"]
            for phrase in blog_forbidden:
                if phrase in draft_content:
                    forbidden_phrases.append(phrase)
                    violations.append({
                        "type": "forbidden_phrase",
                        "message": f"Phrase '{phrase}' may be considered clickbait",
                        "severity": "error"
                    })
        
        # Common style issues
        if "!!!" in draft_content:
            violations.append({
                "type": "style_violation",
                "message": "Avoid excessive exclamation marks",
                "severity": "warning"
            })
        
        if draft_content.count("amazing") > 2:
            violations.append({
                "type": "overuse_violation",
                "message": "Word 'amazing' overused - consider alternatives",
                "severity": "warning"
            })
        
        # Calculate compliance score
        error_count = len([v for v in violations if v["severity"] == "error"])
        warning_count = len([v for v in violations if v["severity"] == "warning"])
        
        # Base score starts at 10.0
        compliance_score = 10.0
        compliance_score -= (error_count * 2.0)  # Errors are -2 points each
        compliance_score -= (warning_count * 0.5)  # Warnings are -0.5 points each
        compliance_score = max(0.0, compliance_score)  # Don't go below 0
        
        # Determine if compliant (passing threshold)
        passing_threshold = 7.0  # Configurable threshold
        is_compliant = (error_count == 0 and compliance_score >= passing_threshold)
        
        # Set result fields
        result.is_compliant = is_compliant
        result.compliance_score = compliance_score
        result.violations = violations
        result.forbidden_phrases = forbidden_phrases
        result.suggestions = suggestions
        result.completion_time = datetime.now(timezone.utc)
        
        logger.info(f"📊 Style validation result: compliant={is_compliant}, score={compliance_score:.1f}")
        logger.info(f"📝 Violations: {error_count} errors, {warning_count} warnings")
        
        return result
    
    def _handle_max_retries_exceeded(self, writing_state, cache_key: str) -> StyleValidationResult:
        """
        Handle max retries exceeded - Task 16.2 & 16.3
        
        Args:
            writing_state: Current WritingFlowState
            cache_key: Cache key for retry tracking
            
        Returns:
            StyleValidationResult with escalation data
        """
        
        logger.warning("🚨 Style validation max retries exceeded - creating escalation")
        
        result = StyleValidationResult()
        result.is_compliant = False
        result.requires_escalation = True
        result.retry_count = self.config.style_max_retries
        result.completion_time = datetime.now(timezone.utc)
        
        # Create escalation - Task 16.3
        escalation = self._create_escalation(writing_state, result, "max_retries_exceeded")
        self._store_escalation(cache_key, escalation)
        
        # Set basic violations indicating escalation needed
        result.violations = [{
            "type": "escalation_required",
            "message": f"Style validation failed after {self.config.style_max_retries} retries",
            "severity": "error"
        }]
        
        result.suggestions = [
            "Manual review required",
            "Consider revising content structure",
            "Check platform-specific guidelines"
        ]
        
        return result
    
    def _create_escalation(self, writing_state, result: StyleValidationResult, reason: str) -> StyleEscalation:
        """
        Create escalation for style issues - Task 16.3
        
        Args:
            writing_state: Current WritingFlowState
            result: Style validation result
            reason: Reason for escalation
            
        Returns:
            StyleEscalation with escalation data
        """
        
        escalation = StyleEscalation()
        escalation.escalation_required = True
        escalation.escalation_reason = reason
        escalation.max_retries_exceeded = (reason == "max_retries_exceeded")
        escalation.escalation_time = datetime.now(timezone.utc)
        
        # Determine escalation level based on violations
        error_violations = [v for v in result.violations if v.get("severity") == "error"]
        critical_violations = [v["message"] for v in error_violations]
        
        if len(critical_violations) > 3:
            escalation.escalation_level = "expert_review"
        elif len(critical_violations) > 0:
            escalation.escalation_level = "human_review"
        else:
            escalation.escalation_level = "override"  # Only warnings, can override
        
        escalation.critical_violations = critical_violations
        
        logger.info(f"🚨 Escalation created: level={escalation.escalation_level}, reason={reason}")
        
        return escalation
    
    def _store_escalation(self, cache_key: str, escalation: StyleEscalation) -> None:
        """Store escalation data"""
        self._escalation_cache[cache_key] = escalation
        logger.info(f"📋 Escalation stored for {cache_key}")
    
    def _record_retry_attempt(
        self, 
        cache_key: str, 
        retry_count: int, 
        result: Optional[StyleValidationResult],
        error: Optional[str] = None
    ) -> None:
        """Record retry attempt for tracking - Task 16.2"""
        
        attempt_data = {
            "retry_count": retry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": result.is_compliant if result else False,
            "compliance_score": result.compliance_score if result else 0.0,
            "error": error
        }
        
        self._retry_history[cache_key].append(attempt_data)
        logger.info(f"📝 Retry attempt {retry_count} recorded for {cache_key}")
    
    def _is_style_completed_and_passed(self, writing_state) -> bool:
        """Check if style validation already completed successfully"""
        
        # Check stage manager completion
        stage_result = self.stage_manager.get_stage_result(FlowStage.STYLE_VALIDATION)
        if stage_result and stage_result.status.value == "SUCCESS":
            return True
        
        # Check writing state
        return writing_state.current_stage == "style_validation_completed"
    
    def _style_fallback(self, writing_state, error: str) -> StyleValidationResult:
        """
        Fallback style validation when main validation fails
        
        Args:
            writing_state: Current WritingFlowState
            error: Error that triggered fallback
            
        Returns:
            StyleValidationResult with fallback data
        """
        
        logger.info("🔄 Using style validation fallback strategy")
        
        result = StyleValidationResult()
        result.fallback_used = True
        result.is_compliant = True  # Allow progression in fallback mode
        result.compliance_score = 5.0  # Neutral score
        result.violations = []
        result.forbidden_phrases = []
        result.suggestions = [
            "Manual style review recommended due to service unavailability",
            "Verify content follows platform guidelines"
        ]
        result.completion_time = datetime.now(timezone.utc)
        
        return result
    
    def _mark_style_completed(self, writing_state, result: StyleValidationResult) -> None:
        """Mark style validation as completed in stage manager"""
        
        self.stage_manager.complete_stage(
            FlowStage.STYLE_VALIDATION,
            success=True,
            result={
                "compliance_score": result.compliance_score,
                "violations_count": len(result.violations),
                "retry_count": result.retry_count,
                "completion_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Update writing state
        writing_state.current_stage = "style_validation_completed"
        
        logger.info("✅ Style validation stage marked as completed")
    
    def get_escalation_status(self, writing_state) -> Optional[StyleEscalation]:
        """
        Get escalation status for current content - Task 16.3
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            StyleEscalation if escalation exists, None otherwise
        """
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._escalation_cache.get(cache_key)
    
    def get_retry_history(self, writing_state) -> List[Dict[str, Any]]:
        """
        Get retry history for current content - Task 16.2
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            List of retry attempts
        """
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._retry_history.get(cache_key, [])
    
    def get_style_status(self, writing_state) -> Dict[str, Any]:
        """
        Get comprehensive style validation status
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            Dict with style validation status
        """
        
        stage_result = self.stage_manager.get_stage_result(FlowStage.STYLE_VALIDATION)
        escalation = self.get_escalation_status(writing_state)
        retry_history = self.get_retry_history(writing_state)
        
        return {
            "should_execute": self.should_execute_style_validation(writing_state),
            "is_completed": self._is_style_completed_and_passed(writing_state),
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "stage_result": stage_result.dict() if stage_result else None,
            "retry_count": len(retry_history),
            "max_retries": self.config.style_max_retries,
            "escalation_required": escalation.escalation_required if escalation else False,
            "escalation_level": escalation.escalation_level if escalation else None,
            "has_draft": bool(writing_state.current_draft),
            "draft_length": len(writing_state.current_draft) if writing_state.current_draft else 0
        }


# Export main classes
__all__ = [
    "LinearStyleExecutor",
    "StyleValidationResult",
    "StyleEscalation"
]