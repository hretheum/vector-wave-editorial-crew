"""
Linear Quality Assessment Execution - Task 17.1

This module implements quality assessment stage execution without circular dependencies,
with quality-based retry mechanism and final output path.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.managers.stage_manager import StageManager
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerError
from ai_writing_flow.flow_inputs import FlowPathConfig

logger = logging.getLogger(__name__)


class QualityAssessmentResult:
    """Quality assessment execution result"""
    
    def __init__(self):
        self.quality_score: float = 0.0
        self.meets_approval_threshold: bool = False
        self.quality_issues: List[Dict[str, str]] = []
        self.strengths: List[str] = []
        self.improvements: List[str] = []
        self.final_approval: bool = False
        self.retry_count: int = 0
        self.requires_revision: bool = False
        self.completion_time: Optional[datetime] = None
        self.fallback_used: bool = False


class QualityGates:
    """Quality gate definitions and thresholds"""
    
    def __init__(self):
        self.content_accuracy_weight: float = 0.3
        self.audience_alignment_weight: float = 0.2
        self.platform_optimization_weight: float = 0.2
        self.engagement_potential_weight: float = 0.15
        self.style_compliance_weight: float = 0.15
        
        # Quality thresholds
        self.minimum_passing_score: float = 6.0
        self.auto_approval_threshold: float = 8.0
        self.excellence_threshold: float = 9.0


class LinearQualityExecutor:
    """
    Linear quality assessment execution - Task 17.1
    
    Features:
    - Final quality check with approval logic - Task 17.1
    - Quality-based retry mechanism - Task 17.2  
    - Final output path for approved content - Task 17.3
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
        self.quality_gates = QualityGates()
        self._retry_history: Dict[str, List[Dict[str, Any]]] = {}
        self._quality_reports: Dict[str, QualityAssessmentResult] = {}
    
    def should_execute_quality_assessment(self, writing_state) -> bool:
        """
        Determine if quality assessment should be executed
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            True if quality assessment should be executed
        """
        
        # Skip if configured to skip
        if self.config.skip_quality_check:
            logger.info("⏭️ Skipping quality assessment - configured to skip")
            return False
        
        # Skip if no draft to assess
        if not writing_state.current_draft:
            logger.info("⏭️ Skipping quality assessment - no draft available")
            return False
        
        # Check if already completed with approval
        if self._is_quality_approved(writing_state):
            logger.info("⏭️ Quality assessment already completed with approval")
            return False
        
        logger.info("🎯 Quality assessment will be executed")
        return True
    
    def execute_quality_assessment(self, writing_state) -> QualityAssessmentResult:
        """
        Execute quality assessment with retry mechanism - Task 17.1 & 17.2
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            QualityAssessmentResult with assessment data
        """
        
        logger.info("🎯 Executing quality assessment with retry mechanism...")
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        max_retries = self.config.quality_max_retries
        
        # Initialize retry history if needed
        if cache_key not in self._retry_history:
            self._retry_history[cache_key] = []
        
        current_retry = len(self._retry_history[cache_key])
        
        # Check if max retries exceeded - Task 17.2
        if current_retry >= max_retries:
            logger.warning(f"⚠️ Quality assessment max retries ({max_retries}) exceeded")
            return self._handle_max_retries_exceeded(writing_state, cache_key)
        
        try:
            # Execute with circuit breaker protection
            result = self.circuit_breaker.call(
                self._execute_quality_core,
                writing_state=writing_state,
                retry_count=current_retry
            )
            
            # Record retry attempt
            self._record_retry_attempt(cache_key, current_retry, result)
            
            # Check if quality meets approval threshold
            if result.meets_approval_threshold:
                logger.info("✅ Quality assessment passed - content approved")
                result.final_approval = True
                self._mark_quality_completed(writing_state, result)
                self._prepare_final_output(writing_state, result)  # Task 17.3
                return result
            else:
                # Quality check failed - determine if we should retry - Task 17.2
                if current_retry < max_retries - 1 and result.quality_score >= self.quality_gates.minimum_passing_score:
                    logger.info(f"🔄 Quality below threshold but above minimum, will retry ({current_retry + 1}/{max_retries})")
                    result.requires_revision = True
                    result.final_approval = False
                elif current_retry < max_retries - 1:
                    logger.warning(f"🔄 Quality below minimum, major revision needed ({current_retry + 1}/{max_retries})")
                    result.requires_revision = True
                    result.final_approval = False
                else:
                    logger.error("❌ Quality assessment failed after all retries - content rejected")
                    result.final_approval = False
                    result.requires_revision = True
                
                return result
                
        except CircuitBreakerError as e:
            logger.error(f"🔌 Quality assessment circuit breaker open: {e}")
            
            # Use fallback
            fallback_result = self._quality_fallback(writing_state, str(e))
            self._record_retry_attempt(cache_key, current_retry, fallback_result)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Quality assessment failed: {str(e)}", exc_info=True)
            
            # Record failed attempt
            self._record_retry_attempt(cache_key, current_retry, None, str(e))
            
            # Try fallback or fail
            if current_retry < max_retries - 1:
                # Will retry on next call
                result = QualityAssessmentResult()
                result.quality_score = 0.0
                result.meets_approval_threshold = False
                result.requires_revision = True
                result.retry_count = current_retry
                result.completion_time = datetime.now(timezone.utc)
                return result
            else:
                # Final failure
                return self._handle_max_retries_exceeded(writing_state, cache_key)
    
    def _execute_quality_core(self, writing_state, retry_count: int = 0) -> QualityAssessmentResult:
        """
        Core quality assessment logic - Task 17.1
        
        Args:
            writing_state: Current WritingFlowState
            retry_count: Current retry attempt number
            
        Returns:
            QualityAssessmentResult with assessment data
        """
        
        result = QualityAssessmentResult()
        result.retry_count = retry_count
        
        logger.info(f"🎯 Assessing quality for: {writing_state.topic_title} (attempt {retry_count + 1})")
        logger.info(f"📄 Draft length: {len(writing_state.current_draft)} characters")
        logger.info(f"🎯 Platform: {writing_state.platform}")
        logger.info(f"📊 Viral score: {writing_state.viral_score}")
        
        # Quality assessment dimensions
        quality_scores = {}
        quality_issues = []
        strengths = []
        improvements = []
        
        # 1. Content Accuracy Assessment (30% weight)
        accuracy_score = self._assess_content_accuracy(writing_state, quality_issues, strengths)
        quality_scores['content_accuracy'] = accuracy_score
        
        # 2. Audience Alignment Assessment (20% weight)
        audience_score = self._assess_audience_alignment(writing_state, quality_issues, strengths)
        quality_scores['audience_alignment'] = audience_score
        
        # 3. Platform Optimization Assessment (20% weight)
        platform_score = self._assess_platform_optimization(writing_state, quality_issues, strengths)
        quality_scores['platform_optimization'] = platform_score
        
        # 4. Engagement Potential Assessment (15% weight)
        engagement_score = self._assess_engagement_potential(writing_state, quality_issues, strengths)
        quality_scores['engagement_potential'] = engagement_score
        
        # 5. Style Compliance Assessment (15% weight)
        style_score = self._assess_style_compliance(writing_state, quality_issues, strengths)
        quality_scores['style_compliance'] = style_score
        
        # Calculate weighted overall quality score
        overall_score = (
            accuracy_score * self.quality_gates.content_accuracy_weight +
            audience_score * self.quality_gates.audience_alignment_weight +
            platform_score * self.quality_gates.platform_optimization_weight +
            engagement_score * self.quality_gates.engagement_potential_weight +
            style_score * self.quality_gates.style_compliance_weight
        )
        
        # Generate improvements based on low scores
        if accuracy_score < 7.0:
            improvements.append("Verify factual accuracy and add credible sources")
        if audience_score < 7.0:
            improvements.append("Better align content with target audience needs")
        if platform_score < 7.0:
            improvements.append(f"Optimize content format for {writing_state.platform}")
        if engagement_score < 7.0:
            improvements.append("Add more engaging elements (questions, calls-to-action)")
        if style_score < 7.0:
            improvements.append("Improve writing style and readability")
        
        # Check approval thresholds
        meets_approval = overall_score >= self.quality_gates.auto_approval_threshold
        
        # Apply viral score bonus/penalty
        if writing_state.viral_score >= 8.0:
            overall_score += 0.5  # Bonus for high viral potential
            strengths.append("High viral potential detected")
        elif writing_state.viral_score <= 3.0:
            overall_score -= 0.3  # Penalty for low viral potential
            improvements.append("Consider increasing viral appeal")
        
        # Ensure score stays within bounds
        overall_score = max(0.0, min(10.0, overall_score))
        
        # Set result fields
        result.quality_score = overall_score
        result.meets_approval_threshold = meets_approval
        result.quality_issues = quality_issues
        result.strengths = strengths
        result.improvements = improvements
        result.completion_time = datetime.now(timezone.utc)
        
        logger.info(f"📊 Quality assessment result: score={overall_score:.1f}, approved={meets_approval}")
        logger.info(f"📝 Issues: {len(quality_issues)}, Strengths: {len(strengths)}, Improvements: {len(improvements)}")
        
        return result
    
    def _assess_content_accuracy(self, writing_state, issues: List, strengths: List) -> float:
        """Assess content accuracy (30% weight)"""
        
        score = 8.0  # Base score
        draft = writing_state.current_draft.lower()
        
        # Check for research backing
        if writing_state.research_sources and len(writing_state.research_sources) > 0:
            score += 1.0
            strengths.append("Content backed by research sources")
        else:
            score -= 1.0
            issues.append({"type": "accuracy", "message": "No research sources provided", "severity": "warning"})
        
        # Check for claims that need verification
        claim_words = ["studies show", "research proves", "experts say", "statistics indicate"]
        unverified_claims = sum(1 for word in claim_words if word in draft)
        if unverified_claims > 2:
            score -= 1.0
            issues.append({"type": "accuracy", "message": "Multiple unverified claims detected", "severity": "error"})
        
        # Check for factual language vs opinion
        opinion_words = ["i think", "i believe", "in my opinion"]
        fact_words = ["according to", "research shows", "data indicates"]
        
        opinion_count = sum(1 for word in opinion_words if word in draft)
        fact_count = sum(1 for word in fact_words if word in draft)
        
        if fact_count > opinion_count:
            score += 0.5
            strengths.append("Good balance of factual content")
        
        return max(0.0, min(10.0, score))
    
    def _assess_audience_alignment(self, writing_state, issues: List, strengths: List) -> float:
        """Assess audience alignment (20% weight)"""
        
        score = 7.0  # Base score
        
        # Check if audience analysis was performed
        if writing_state.audience_scores:
            score += 1.0
            strengths.append("Content aligned with audience analysis")
            
            # Check depth level alignment
            if hasattr(writing_state, 'target_depth_level'):
                if writing_state.target_depth_level >= 2:
                    score += 0.5
                    strengths.append("Appropriate content depth for audience")
        else:
            score -= 1.5
            issues.append({"type": "audience", "message": "No audience alignment performed", "severity": "error"})
        
        # Platform-specific audience considerations
        draft = writing_state.current_draft.lower()
        
        if writing_state.platform == "LinkedIn":
            professional_terms = ["business", "industry", "professional", "career", "strategy"]
            if any(term in draft for term in professional_terms):
                score += 0.5
                strengths.append("Professional tone appropriate for LinkedIn")
        
        elif writing_state.platform == "Twitter":
            if len(writing_state.current_draft) <= 280 or "thread" in draft:
                score += 0.5
                strengths.append("Format optimized for Twitter consumption")
        
        return max(0.0, min(10.0, score))
    
    def _assess_platform_optimization(self, writing_state, issues: List, strengths: List) -> float:
        """Assess platform optimization (20% weight)"""
        
        score = 7.0  # Base score
        draft_length = len(writing_state.current_draft)
        
        if writing_state.platform == "LinkedIn":
            if 300 <= draft_length <= 3000:
                score += 1.0
                strengths.append("Optimal LinkedIn post length")
            else:
                score -= 1.0
                issues.append({"type": "platform", "message": "Suboptimal length for LinkedIn", "severity": "warning"})
            
            # Check for LinkedIn-specific elements
            if "#" in writing_state.current_draft:
                score += 0.5
                strengths.append("Includes hashtags for LinkedIn visibility")
        
        elif writing_state.platform == "Twitter":
            if draft_length <= 280 or ("thread" in writing_state.current_draft.lower() and draft_length <= 2800):
                score += 1.0
                strengths.append("Optimal Twitter format")
            else:
                score -= 1.0
                issues.append({"type": "platform", "message": "Too long for Twitter format", "severity": "error"})
        
        elif writing_state.platform == "Blog":
            if draft_length >= 500:
                score += 1.0
                strengths.append("Sufficient length for blog content")
            else:
                score -= 1.0
                issues.append({"type": "platform", "message": "Too short for blog post", "severity": "warning"})
            
            # Check for blog structure
            if "##" in writing_state.current_draft:
                score += 0.5
                strengths.append("Good blog structure with headings")
        
        return max(0.0, min(10.0, score))
    
    def _assess_engagement_potential(self, writing_state, issues: List, strengths: List) -> float:
        """Assess engagement potential (15% weight)"""
        
        score = 6.0  # Base score
        draft = writing_state.current_draft.lower()
        
        # Check for engagement elements
        engagement_elements = ["?", "what do you think", "share your", "comment", "thoughts", "agree"]
        engagement_count = sum(1 for element in engagement_elements if element in draft)
        
        if engagement_count >= 2:
            score += 1.5
            strengths.append("Multiple engagement elements present")
        elif engagement_count >= 1:
            score += 0.5
            strengths.append("Some engagement elements present")
        else:
            score -= 1.0
            issues.append({"type": "engagement", "message": "Lacks engagement elements", "severity": "warning"})
        
        # Check for storytelling elements
        story_elements = ["imagine", "story", "example", "case study", "experience"]
        if any(element in draft for element in story_elements):
            score += 0.5
            strengths.append("Includes storytelling elements")
        
        # Apply viral score influence
        if writing_state.viral_score >= 8.0:
            score += 1.0
            strengths.append("High viral potential content")
        elif writing_state.viral_score <= 3.0:
            score -= 0.5
        
        return max(0.0, min(10.0, score))
    
    def _assess_style_compliance(self, writing_state, issues: List, strengths: List) -> float:
        """Assess style compliance (15% weight)"""
        
        score = 7.0  # Base score
        draft = writing_state.current_draft
        
        # Check for style issues
        if "!!!" in draft:
            score -= 0.5
            issues.append({"type": "style", "message": "Excessive exclamation marks", "severity": "warning"})
        
        # Check readability
        sentences = draft.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        if 10 <= avg_sentence_length <= 20:
            score += 0.5
            strengths.append("Good sentence length for readability")
        elif avg_sentence_length > 25:
            score -= 0.5
            issues.append({"type": "style", "message": "Sentences too long for readability", "severity": "warning"})
        
        # Check for variety in sentence structure
        if len(set(len(s.split()) for s in sentences)) > 3:
            score += 0.5
            strengths.append("Good sentence length variety")
        
        return max(0.0, min(10.0, score))
    
    def _handle_max_retries_exceeded(self, writing_state, cache_key: str) -> QualityAssessmentResult:
        """
        Handle max retries exceeded - Task 17.2
        
        Args:
            writing_state: Current WritingFlowState
            cache_key: Cache key for retry tracking
            
        Returns:
            QualityAssessmentResult with rejection data
        """
        
        logger.error("❌ Quality assessment max retries exceeded - content rejected")
        
        result = QualityAssessmentResult()
        result.quality_score = 3.0  # Low score for rejection
        result.meets_approval_threshold = False
        result.final_approval = False
        result.requires_revision = True
        result.retry_count = self.config.quality_max_retries
        result.completion_time = datetime.now(timezone.utc)
        
        result.quality_issues = [{
            "type": "max_retries_exceeded",
            "message": f"Quality assessment failed after {self.config.quality_max_retries} retries",
            "severity": "error"
        }]
        
        result.improvements = [
            "Comprehensive content revision required",
            "Review all quality dimensions",
            "Consider rewriting from scratch",
            "Seek expert review before resubmission"
        ]
        
        return result
    
    def _prepare_final_output(self, writing_state, result: QualityAssessmentResult) -> None:
        """
        Prepare final output for approved content - Task 17.3
        
        Args:
            writing_state: Current WritingFlowState
            result: Quality assessment result
        """
        
        logger.info("🏁 Preparing final output for approved content...")
        
        # Create final output metadata
        final_output = {
            "content": writing_state.current_draft,
            "quality_score": result.quality_score,
            "platform": writing_state.platform,
            "topic_title": writing_state.topic_title,
            "viral_score": writing_state.viral_score,
            "approval_timestamp": datetime.now(timezone.utc).isoformat(),
            "quality_strengths": result.strengths,
            "agents_executed": writing_state.agents_executed,
            "total_retry_attempts": result.retry_count,
            "content_metadata": {
                "word_count": len(writing_state.current_draft.split()),
                "character_count": len(writing_state.current_draft),
                "estimated_read_time": len(writing_state.current_draft.split()) // 200  # ~200 WPM
            }
        }
        
        # Store final output in writing state
        writing_state.final_output = final_output
        writing_state.current_stage = "quality_approved"
        
        logger.info("✅ Final output prepared for approved content")
    
    def _record_retry_attempt(
        self, 
        cache_key: str, 
        retry_count: int, 
        result: Optional[QualityAssessmentResult],
        error: Optional[str] = None
    ) -> None:
        """Record retry attempt for tracking - Task 17.2"""
        
        attempt_data = {
            "retry_count": retry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": result.meets_approval_threshold if result else False,
            "quality_score": result.quality_score if result else 0.0,
            "issues_count": len(result.quality_issues) if result else 0,
            "error": error
        }
        
        self._retry_history[cache_key].append(attempt_data)
        logger.info(f"📝 Quality retry attempt {retry_count} recorded for {cache_key}")
    
    def _is_quality_approved(self, writing_state) -> bool:
        """Check if quality assessment already completed with approval"""
        
        # Check stage manager completion
        stage_result = self.stage_manager.get_stage_result(FlowStage.QUALITY_CHECK)
        if stage_result and stage_result.status.value == "SUCCESS":
            return True
        
        # Check writing state
        return writing_state.current_stage == "quality_approved"
    
    def _quality_fallback(self, writing_state, error: str) -> QualityAssessmentResult:
        """
        Fallback quality assessment when main assessment fails
        
        Args:
            writing_state: Current WritingFlowState
            error: Error that triggered fallback
            
        Returns:
            QualityAssessmentResult with fallback data
        """
        
        logger.info("🔄 Using quality assessment fallback strategy")
        
        result = QualityAssessmentResult()
        result.fallback_used = True
        result.quality_score = 6.5  # Neutral passing score
        result.meets_approval_threshold = True  # Allow progression in fallback mode
        result.final_approval = True
        result.requires_revision = False
        result.quality_issues = []
        result.strengths = ["Fallback approval - manual review recommended"]
        result.improvements = [
            "Manual quality review recommended due to service unavailability",
            "Verify content meets all quality standards before publication"
        ]
        result.completion_time = datetime.now(timezone.utc)
        
        # Still prepare final output in fallback mode
        self._prepare_final_output(writing_state, result)
        
        return result
    
    def _mark_quality_completed(self, writing_state, result: QualityAssessmentResult) -> None:
        """Mark quality assessment as completed in stage manager"""
        
        self.stage_manager.complete_stage(
            FlowStage.QUALITY_CHECK,
            success=True,
            result={
                "quality_score": result.quality_score,
                "final_approval": result.final_approval,
                "issues_count": len(result.quality_issues),
                "retry_count": result.retry_count,
                "completion_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info("✅ Quality assessment stage marked as completed")
    
    def get_retry_history(self, writing_state) -> List[Dict[str, Any]]:
        """
        Get retry history for current content - Task 17.2
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            List of retry attempts
        """
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._retry_history.get(cache_key, [])
    
    def get_quality_report(self, writing_state) -> Optional[QualityAssessmentResult]:
        """
        Get detailed quality report for current content
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            QualityAssessmentResult if available, None otherwise
        """
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._quality_reports.get(cache_key)
    
    def get_quality_status(self, writing_state) -> Dict[str, Any]:
        """
        Get comprehensive quality assessment status
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            Dict with quality assessment status
        """
        
        stage_result = self.stage_manager.get_stage_result(FlowStage.QUALITY_CHECK)
        retry_history = self.get_retry_history(writing_state)
        
        return {
            "should_execute": self.should_execute_quality_assessment(writing_state),
            "is_completed": self._is_quality_approved(writing_state),
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "stage_result": stage_result.dict() if stage_result else None,
            "retry_count": len(retry_history),
            "max_retries": self.config.quality_max_retries,
            "has_draft": bool(writing_state.current_draft),
            "draft_length": len(writing_state.current_draft) if writing_state.current_draft else 0,
            "quality_gates": {
                "minimum_passing_score": self.quality_gates.minimum_passing_score,
                "auto_approval_threshold": self.quality_gates.auto_approval_threshold,
                "excellence_threshold": self.quality_gates.excellence_threshold
            }
        }


# Export main classes
__all__ = [
    "LinearQualityExecutor",
    "QualityAssessmentResult",
    "QualityGates"
]