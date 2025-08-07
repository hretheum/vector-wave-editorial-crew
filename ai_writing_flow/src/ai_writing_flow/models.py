"""
Data models for AI Writing Flow
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime


class WritingFlowState(BaseModel):
    """State management for the writing flow"""
    
    # Input from Kolegium
    topic_title: str = Field(default="", description="Selected topic for content creation")
    platform: str = Field(default="", description="Target platform (LinkedIn, Twitter, etc.)")
    file_path: str = Field(default="", description="Path to specific source content file or folder")
    source_files: List[str] = Field(default_factory=list, description="List of source files when processing folder")
    content_type: Literal["STANDALONE", "SERIES"] = Field(default="STANDALONE")
    content_ownership: Literal["ORIGINAL", "EXTERNAL"] = Field(default="EXTERNAL")
    viral_score: float = Field(default=0.0, description="Viral potential score from Kolegium")
    editorial_recommendations: str = Field(default="", description="Editorial guidance from Kolegium")
    
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
    publication_metadata: Dict[str, Any] = Field(default_factory=dict)
    
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
    data_points: List[Dict[str, Any]] = Field(
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


class ContentAnalysisResult(BaseModel):
    """Output model for ContentAnalysisAgent with Knowledge Base integration"""
    
    content_type: str = Field(
        ..., 
        description="Identified content type (e.g., 'technical_tutorial', 'thought_leadership')"
    )
    viral_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Viral potential score based on content analysis"
    )
    complexity_level: str = Field(
        ..., 
        description="Content complexity level: 'beginner', 'intermediate', 'advanced'"
    )
    recommended_flow_path: str = Field(
        ..., 
        description="Recommended CrewAI flow path for content generation"
    )
    kb_insights: List[str] = Field(
        default_factory=list,
        description="Key insights from Knowledge Base search"
    )
    processing_time: float = Field(
        ..., 
        description="Analysis processing time in seconds"
    )
    
    # Extended analysis details
    target_platform: str = Field(
        ..., 
        description="Target platform for content publication"
    )
    analysis_confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score for the analysis results"
    )
    key_themes: List[str] = Field(
        default_factory=list,
        description="Key themes identified for content"
    )
    audience_indicators: Dict[str, Any] = Field(
        default_factory=dict,
        description="Target audience analysis results"
    )
    content_structure: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recommended content structure and format"
    )
    
    # Knowledge Base integration status
    kb_available: bool = Field(
        default=True,
        description="Whether Knowledge Base was available during analysis"
    )
    search_strategy_used: str = Field(
        default="HYBRID",
        description="Knowledge Base search strategy used"
    )
    kb_query_count: int = Field(
        default=0,
        description="Number of Knowledge Base queries performed"
    )