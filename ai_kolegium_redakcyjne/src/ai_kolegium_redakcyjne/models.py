"""
Pydantic models for AI Kolegium Redakcyjne
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime


class TopicDiscovery(BaseModel):
    """Model for discovered topics"""
    topic_id: str = Field(..., description="Unique identifier for the topic")
    title: str = Field(..., description="Compelling headline")
    summary: str = Field(..., description="2-3 sentence description")
    source: str = Field(..., description="Origin URL/platform")
    category: Literal["AI", "Technology", "Digital Culture", "Startups"] = Field(..., description="Topic category")
    discovery_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When topic was found")
    initial_engagement_signals: Dict[str, int] = Field(default_factory=dict, description="Early metrics")


class ViralAnalysis(BaseModel):
    """Model for viral potential analysis"""
    topic_id: str = Field(..., description="Reference to discovered topic")
    viral_score: float = Field(..., ge=0.0, le=1.0, description="Viral probability 0-1")
    engagement_prediction: Dict[str, int] = Field(..., description="Expected views/shares/comments")
    trend_velocity: float = Field(..., description="How fast it's growing")
    competitive_landscape: str = Field(..., description="Similar content performance")
    recommendation: Literal["strong_yes", "yes", "maybe", "no"] = Field(..., description="Recommendation")
    reasoning: str = Field(..., description="Detailed explanation")


class EditorialDecision(BaseModel):
    """Model for editorial decisions"""
    topic_id: str = Field(..., description="Reference to topic")
    decision: Literal["approve", "reject", "human_review"] = Field(..., description="Editorial decision")
    controversy_level: float = Field(..., ge=0.0, le=1.0, description="Controversy score 0-1")
    brand_alignment: float = Field(..., ge=0.0, le=1.0, description="Brand alignment score 0-1")
    priority: Literal["high", "medium", "low"] = Field(..., description="Topic priority")
    editorial_notes: str = Field(..., description="Specific guidance")
    human_review_reason: Optional[str] = Field(None, description="Reason if escalated to human")


class QualityAssessment(BaseModel):
    """Model for quality check results"""
    topic_id: str = Field(..., description="Reference to topic")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality rating 0-1")
    fact_check_results: Dict[str, str] = Field(..., description="Claims verified/disputed")
    source_credibility: str = Field(..., description="Assessment of sources")
    plagiarism_check: Dict[str, bool] = Field(..., description="Pass/fail with details")
    required_corrections: List[str] = Field(default_factory=list, description="List of issues")
    quality_approved: bool = Field(..., description="Whether quality is approved")


class EditorialReport(BaseModel):
    """Model for final editorial report"""
    executive_summary: str = Field(..., description="Key decisions and rationale")
    approved_topics: List[Dict[str, Any]] = Field(..., description="List with full details")
    rejected_topics: List[Dict[str, Any]] = Field(..., description="List with reasons")
    human_review_queue: List[Dict[str, Any]] = Field(..., description="Topics needing attention")
    content_calendar: List[Dict[str, Any]] = Field(..., description="Proposed publication schedule")
    resource_allocation: Dict[str, List[str]] = Field(..., description="Team assignments")
    performance_predictions: Dict[str, float] = Field(..., description="Expected outcomes")
    visual_dashboard_data: Dict[str, Any] = Field(..., description="Charts/graphs data")


# Response models for list outputs
class TopicDiscoveryList(BaseModel):
    """List of discovered topics"""
    topics: List[TopicDiscovery] = Field(..., description="List of discovered topics")
    total_found: int = Field(..., description="Total number of topics found")
    categories: List[str] = Field(..., description="Categories searched")
    discovery_timestamp: datetime = Field(default_factory=datetime.utcnow)


class ViralAnalysisList(BaseModel):
    """List of viral analyses"""
    analyses: List[ViralAnalysis] = Field(..., description="List of viral analyses")
    average_viral_score: float = Field(..., description="Average viral score across all topics")
    recommendations_summary: Dict[str, int] = Field(..., description="Count by recommendation type")