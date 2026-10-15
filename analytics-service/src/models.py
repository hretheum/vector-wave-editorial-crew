#!/usr/bin/env python3
"""
Data models for Analytics Service
Production-ready Pydantic models for multi-platform analytics
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class CollectionMethod(str, Enum):
    """Supported data collection methods"""
    API = "api"
    PROXY = "proxy"
    MANUAL = "manual"
    CSV = "csv"


class PlatformEnum(str, Enum):
    """Supported analytics platforms"""
    GHOST = "ghost"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    BEEHIIV = "beehiiv"


class CollectionFrequency(str, Enum):
    """Data collection frequencies"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


# Platform Configuration Models
class PlatformConfig(BaseModel):
    """Platform-specific analytics configuration"""
    platform: PlatformEnum
    collection_method: CollectionMethod
    api_credentials: Optional[Dict[str, str]] = None
    proxy_config: Optional[Dict[str, Any]] = None
    collection_frequency: CollectionFrequency = CollectionFrequency.DAILY
    enabled_metrics: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "platform": "linkedin",
                "collection_method": "manual",
                "collection_frequency": "weekly",
                "enabled_metrics": ["views", "reactions", "comments", "shares"]
            }
        }


class ConfigurationResponse(BaseModel):
    """Response for platform configuration"""
    platform: str
    status: str
    collection_method: str
    available_metrics: List[str]
    limitations: List[str]
    next_collection: Optional[datetime] = None


# Manual Data Entry Models
class ManualMetricsEntry(BaseModel):
    """Manual metrics entry for platforms without API access"""
    publication_id: str
    platform: PlatformEnum
    platform_post_id: str
    metrics: Dict[str, Union[int, float]]
    screenshot_urls: Optional[List[str]] = []
    entry_date: datetime
    notes: Optional[str] = None


class ManualEntryResponse(BaseModel):
    """Response for manual metrics entry"""
    entry_id: str
    publication_id: str
    platform: str
    metrics_accepted: Dict[str, bool]
    data_quality_score: float
    stored_at: datetime


# CSV Import Models
class CSVImportRequest(BaseModel):
    """CSV data import request"""
    platform: PlatformEnum
    file_url: str
    date_range: Dict[str, str]
    column_mapping: Dict[str, str]
    import_settings: Optional[Dict[str, Any]] = {}


class CSVImportResponse(BaseModel):
    """CSV import processing response"""
    import_id: str
    platform: str
    status: str
    records_processed: int
    records_imported: int
    records_skipped: int
    validation_errors: List[str]
    processing_time_ms: float


# Analytics Insights Models
class AnalyticsInsights(BaseModel):
    """Comprehensive analytics insights"""
    user_id: str
    time_period: str
    total_publications: int
    platforms_analyzed: List[str]
    
    # Performance metrics
    overall_performance: Dict[str, float]
    platform_comparison: Dict[str, Dict[str, float]]
    content_type_performance: Dict[str, Dict[str, float]]
    trending_topics: List[Dict[str, Any]]
    
    # Insights and recommendations
    key_insights: List[str]
    recommendations: List[str]
    optimal_posting_schedule: Dict[str, str]
    
    # Data quality and coverage
    data_coverage: Dict[str, float]
    data_quality_score: float
    
    generated_at: datetime


# Data Export Models
class ExportResponse(BaseModel):
    """Data export response"""
    export_id: str
    format: str
    file_url: str
    file_size_mb: float
    records_exported: int
    expires_at: datetime
    generated_at: datetime


# Health and Monitoring Models
class HealthResponse(BaseModel):
    """Service health check response"""
    status: str
    service: str
    version: str
    port: int
    timestamp: datetime
    uptime_seconds: float
    chromadb_status: Optional[str] = None
    collections_available: Optional[int] = None
    circuit_breaker_state: Optional[Dict[str, Any]] = None
    platform_collectors: Optional[Dict[str, str]] = None


# Legacy models for backward compatibility
class PublicationMetrics(BaseModel):
    """Publication metrics tracking (legacy)"""
    publication_id: str = Field(..., description="Unique publication identifier")
    platform: str = Field(..., description="Publishing platform (linkedin, twitter, etc.)")
    metrics: Dict[str, Any] = Field(..., description="Platform-specific metrics")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Metric collection timestamp")
    user_id: Optional[str] = Field(None, description="User identifier")
    content_type: Optional[str] = Field(None, description="Content type (article, post, presentation)")


class TrackingResponse(BaseModel):
    """Response for publication tracking (legacy)"""
    status: str = Field(..., description="Tracking status")
    publication_id: str = Field(..., description="Publication identifier")
    platform: str = Field(..., description="Platform name")
    note: str = Field(..., description="Status note")
    tracked_metrics: List[str] = Field(..., description="List of tracked metric types")
    future_features: List[str] = Field(..., description="Future analytics capabilities")


class UserInsights(BaseModel):
    """User analytics insights response (legacy)"""
    user_id: str = Field(..., description="User identifier")
    insights: Dict[str, Any] = Field(..., description="Analytics insights data")
    placeholder_recommendations: List[str] = Field(..., description="Placeholder recommendations")
    future_features: List[str] = Field(..., description="Future insights capabilities")


class PlatformAnalytics(BaseModel):
    """Platform-specific analytics response (legacy)"""
    platform: str = Field(..., description="Platform name")
    total_publications: int = Field(default=0, description="Total publications tracked")
    performance_summary: Dict[str, Any] = Field(..., description="Performance summary")
    placeholder_note: str = Field(..., description="Placeholder status note")