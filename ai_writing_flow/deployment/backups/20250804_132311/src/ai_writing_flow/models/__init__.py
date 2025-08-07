"""Models package for FlowControlState and related models."""

from .flow_stage import FlowStage
from .flow_control_state import FlowControlState
from .stage_execution import StageExecution

# Import models from parent module for compatibility
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

try:
    from models import (
        WritingFlowState, 
        HumanFeedbackDecision,
        ResearchResult,
        AudienceAlignment,
        DraftContent,
        StyleValidation,
        QualityAssessment
    )
except ImportError:
    # Fallback - create minimal compatibility models
    from pydantic import BaseModel, Field
    from typing import List, Dict, Any, Optional, Literal
    from datetime import datetime
    
    class WritingFlowState(BaseModel):
        """Legacy WritingFlowState compatibility model"""
        topic_title: str = ""
        platform: str = ""
        file_path: str = ""
        source_files: List[str] = Field(default_factory=list)
        content_type: str = "STANDALONE"
        content_ownership: str = "EXTERNAL"
        viral_score: float = 0.0
        editorial_recommendations: str = ""
        skip_research: bool = False
        human_feedback_type: Optional[str] = None
        current_stage: str = "initialized"
        research_sources: List[Dict[str, str]] = Field(default_factory=list) 
        research_summary: str = ""
        audience_scores: Dict[str, float] = Field(default_factory=dict)
        audience_insights: str = ""
        target_depth_level: int = 1
        draft_versions: List[str] = Field(default_factory=list)
        current_draft: str = ""
        human_feedback: Optional[str] = None
        style_violations: List[Dict[str, str]] = Field(default_factory=list)
        forbidden_phrases_found: List[str] = Field(default_factory=list)
        style_score: float = 0.0
        quality_score: float = 0.0
        quality_issues: List[str] = Field(default_factory=list)
        revision_count: int = 0
        final_draft: str = ""
        platform_variants: Dict[str, str] = Field(default_factory=dict)
        publication_metadata: Dict[str, Any] = Field(default_factory=dict)
        final_output: Optional[Dict[str, Any]] = None
        flow_start_time: datetime = Field(default_factory=datetime.now)
        total_processing_time: float = 0.0
        agents_executed: List[str] = Field(default_factory=list)
        error_message: str = ""  # Added for V2 compatibility
    
    class HumanFeedbackDecision(BaseModel):
        """Legacy HumanFeedbackDecision compatibility model"""
        feedback_text: str = ""
        feedback_type: str = ""
    
    class ResearchResult(BaseModel):
        """Research result model"""
        sources: List[Dict[str, str]] = Field(default_factory=list)
        summary: str = ""
        key_insights: List[str] = Field(default_factory=list)
        data_points: List[Dict[str, Any]] = Field(default_factory=list)
        methodology: str = ""
    
    class AudienceAlignment(BaseModel):
        """Audience alignment model"""
        technical_founder_score: float = 0.0
        senior_engineer_score: float = 0.0
        decision_maker_score: float = 0.0
        skeptical_learner_score: float = 0.0
        recommended_depth: int = 1
        tone_calibration: str = ""
        key_messages: Dict[str, str] = Field(default_factory=dict)
    
    class DraftContent(BaseModel):
        """Draft content model"""
        title: str = ""
        draft: str = ""
        word_count: int = 0
        structure_type: str = "deep_analysis"
        key_sections: List[str] = Field(default_factory=list)
        non_obvious_insights: List[str] = Field(default_factory=list)
    
    class StyleValidation(BaseModel):
        """Style validation model"""
        is_compliant: bool = True
        violations: List[Dict[str, str]] = Field(default_factory=list)
        forbidden_phrases: List[str] = Field(default_factory=list)
        suggestions: List[str] = Field(default_factory=list)
        compliance_score: float = 100.0
    
    class QualityAssessment(BaseModel):
        """Quality assessment model"""
        is_approved: bool = True
        quality_score: float = 100.0
        fact_check_results: List[Dict[str, str]] = Field(default_factory=list)
        code_verification: Optional[Dict[str, str]] = None
        ethics_checklist: Dict[str, bool] = Field(default_factory=dict)
        improvement_suggestions: List[str] = Field(default_factory=list)
        requires_human_review: bool = False
        controversy_score: float = 0.0

__all__ = [
    "FlowStage", 
    "FlowControlState", 
    "StageExecution",
    "WritingFlowState",
    "HumanFeedbackDecision",
    "ResearchResult",
    "AudienceAlignment", 
    "DraftContent",
    "StyleValidation",
    "QualityAssessment"
]
