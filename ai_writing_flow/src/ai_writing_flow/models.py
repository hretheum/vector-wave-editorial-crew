"""
Data models for AI Writing Flow
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime


class WritingFlowState(BaseModel):
    """State management for the writing flow"""
    
    # Input from Kolegium
    topic_title: str = Field(description="Selected topic for content creation")
    platform: str = Field(description="Target platform (LinkedIn, Twitter, etc.)")
    folder_path: str = Field(description="Path to source content folder")
    content_type: Literal["STANDALONE", "SERIES"] = Field(default="STANDALONE")
    content_ownership: Literal["ORIGINAL", "EXTERNAL"] = Field(default="EXTERNAL")
    viral_score: float = Field(description="Viral potential score from Kolegium")
    editorial_recommendations: str = Field(description="Editorial guidance from Kolegium")
    
    # Flow control
    skip_research: bool = Field(default=False, description="UI override to skip research")
    human_feedback_type: Optional[Literal["minor", "major", "pivot"]] = None
    current_stage: str = Field(default="initialized")
    
    # Research tracking
    research_sources: List[Dict[str, str]] = Field(default_factory=list)
    research_summary: str = Field(default="")
    
    # Audience alignment
    audience_scores: Dict[str, float] = Field(default_factory=dict)
    audience_insights: str = Field(default="")
    target_depth_level: int = Field(default=1)  # 1-3 technical depth
    
    # Content generation
    draft_versions: List[str] = Field(default_factory=list)
    current_draft: str = Field(default="")
    human_feedback: Optional[str] = None
    
    # Style validation
    style_violations: List[Dict[str, str]] = Field(default_factory=list)
    forbidden_phrases_found: List[str] = Field(default_factory=list)
    style_score: float = Field(default=0.0)
    
    # Quality assessment
    quality_score: float = Field(default=0.0)
    quality_issues: List[str] = Field(default_factory=list)
    revision_count: int = Field(default=0)
    
    # Output
    final_draft: str = Field(default="")
    platform_variants: Dict[str, str] = Field(default_factory=dict)
    publication_metadata: Dict[str, any] = Field(default_factory=dict)
    
    # Metadata
    flow_start_time: datetime = Field(default_factory=datetime.now)
    total_processing_time: float = Field(default=0.0)
    agents_executed: List[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Output from Research Agent"""
    sources: List[Dict[str, str]] = Field(
        description="List of sources with url, title, date, type"
    )
    summary: str = Field(description="Executive summary of research findings")
    key_insights: List[str] = Field(description="Bullet points of key insights")
    data_points: List[Dict[str, any]] = Field(
        default_factory=list,
        description="Specific data points with sources"
    )
    methodology: str = Field(description="How the research was conducted")


class AudienceAlignment(BaseModel):
    """Output from Audience Mapper"""
    technical_founder_score: float = Field(ge=0, le=1)
    senior_engineer_score: float = Field(ge=0, le=1)
    decision_maker_score: float = Field(ge=0, le=1)
    skeptical_learner_score: float = Field(ge=0, le=1)
    
    recommended_depth: int = Field(ge=1, le=3, description="Technical depth level")
    tone_calibration: str = Field(description="Recommended tone adjustments")
    key_messages: Dict[str, str] = Field(
        description="Key messages per audience segment"
    )


class DraftContent(BaseModel):
    """Output from Content Writer"""
    title: str
    draft: str
    word_count: int
    structure_type: Literal["deep_analysis", "quick_take", "tutorial", "critique"]
    key_sections: List[str]
    non_obvious_insights: List[str]


class StyleValidation(BaseModel):
    """Output from Style Validator"""
    is_compliant: bool
    violations: List[Dict[str, str]]
    forbidden_phrases: List[str]
    suggestions: List[str]
    compliance_score: float = Field(ge=0, le=100)


class QualityAssessment(BaseModel):
    """Output from Quality Controller"""
    is_approved: bool
    quality_score: float = Field(ge=0, le=100)
    fact_check_results: List[Dict[str, str]]
    code_verification: Optional[Dict[str, str]] = None
    ethics_checklist: Dict[str, bool]
    improvement_suggestions: List[str]
    requires_human_review: bool = False
    controversy_score: float = Field(ge=0, le=1)


class HumanFeedbackDecision(BaseModel):
    """Human feedback on draft"""
    feedback_type: Literal["minor", "major", "pivot"]
    feedback_text: str
    specific_changes: Optional[List[str]] = None
    continue_to_stage: str  # Which stage to continue from