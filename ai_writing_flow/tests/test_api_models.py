#!/usr/bin/env python3
"""
Tests for AI Writing Flow V2 API Models

Tests Pydantic request/response models without requiring CrewAI dependency.
"""

import pytest
from pydantic import ValidationError


# Define models inline to avoid circular imports
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class FlowExecutionRequest(BaseModel):
    """Request model for flow execution"""
    topic_title: str = Field(..., description="Topic title for content generation")
    platform: str = Field(default="LinkedIn", description="Target platform")
    file_path: Optional[str] = Field(None, description="Optional input file path")
    content_type: str = Field(default="STANDALONE", description="Content type")
    content_ownership: str = Field(default="EXTERNAL", description="Content ownership")
    viral_score: float = Field(default=0.0, description="Expected viral score")
    editorial_recommendations: str = Field(default="", description="Editorial guidance")
    skip_research: bool = Field(default=False, description="Skip research phase")
    
    # V2-specific options
    monitoring_enabled: bool = Field(default=True, description="Enable monitoring")
    alerting_enabled: bool = Field(default=True, description="Enable alerting")
    quality_gates_enabled: bool = Field(default=True, description="Enable quality gates")


class FlowExecutionResponse(BaseModel):
    """Response model for flow execution"""
    flow_id: str = Field(..., description="Unique flow execution ID")
    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Status message")
    final_draft: Optional[str] = Field(None, description="Generated content")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Execution metrics")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    execution_time: float = Field(default=0.0, description="Total execution time")


class FlowStatusResponse(BaseModel):
    """Response model for flow status"""
    flow_id: str
    status: str  # "running", "completed", "failed", "not_found"
    current_stage: Optional[str] = None
    progress_percent: Optional[float] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str  # "healthy", "warning", "critical"
    timestamp: str
    version: str = "2.0.0"
    components: Dict[str, str] = Field(default_factory=dict)
    uptime_seconds: float = 0.0


class TestRequestResponseModels:
    """Test Pydantic request/response models"""
    
    def test_flow_execution_request_valid(self):
        """Test valid FlowExecutionRequest"""
        
        request_data = {
            "topic_title": "AI in Healthcare",
            "platform": "LinkedIn",
            "viral_score": 8.5
        }
        
        request = FlowExecutionRequest(**request_data)
        
        assert request.topic_title == "AI in Healthcare"
        assert request.platform == "LinkedIn"
        assert request.viral_score == 8.5
        assert request.content_type == "STANDALONE"  # Default
        assert request.monitoring_enabled is True    # Default
        assert request.alerting_enabled is True      # Default
        assert request.quality_gates_enabled is True # Default
    
    def test_flow_execution_request_all_fields(self):
        """Test FlowExecutionRequest with all fields"""
        
        request_data = {
            "topic_title": "Complete Test Topic",
            "platform": "Twitter",
            "file_path": "/path/to/file.md",
            "content_type": "SERIES",
            "content_ownership": "ORIGINAL",
            "viral_score": 9.2,
            "editorial_recommendations": "Focus on technical depth",
            "skip_research": True,
            "monitoring_enabled": False,
            "alerting_enabled": False,
            "quality_gates_enabled": False
        }
        
        request = FlowExecutionRequest(**request_data)
        
        assert request.topic_title == "Complete Test Topic"
        assert request.platform == "Twitter"
        assert request.file_path == "/path/to/file.md"
        assert request.content_type == "SERIES"
        assert request.content_ownership == "ORIGINAL"
        assert request.viral_score == 9.2
        assert request.editorial_recommendations == "Focus on technical depth"
        assert request.skip_research is True
        assert request.monitoring_enabled is False
        assert request.alerting_enabled is False
        assert request.quality_gates_enabled is False
    
    def test_flow_execution_request_missing_required(self):
        """Test FlowExecutionRequest with missing required field"""
        
        request_data = {
            "platform": "Twitter"
            # Missing topic_title
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FlowExecutionRequest(**request_data)
        
        assert "topic_title" in str(exc_info.value)
    
    def test_flow_execution_request_invalid_viral_score(self):
        """Test FlowExecutionRequest with invalid viral score"""
        
        request_data = {
            "topic_title": "Test Topic",
            "viral_score": "invalid"  # Should be float
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FlowExecutionRequest(**request_data)
        
        assert "viral_score" in str(exc_info.value)
    
    def test_flow_execution_response_valid(self):
        """Test valid FlowExecutionResponse"""
        
        response_data = {
            "flow_id": "test_123",
            "status": "completed",
            "message": "Success",
            "final_draft": "Generated content",
            "execution_time": 12.5
        }
        
        response = FlowExecutionResponse(**response_data)
        
        assert response.flow_id == "test_123"
        assert response.status == "completed"
        assert response.message == "Success"
        assert response.final_draft == "Generated content"
        assert response.execution_time == 12.5
        assert response.metrics == {}  # Default
        assert response.errors == []   # Default
    
    def test_flow_execution_response_with_metrics(self):
        """Test FlowExecutionResponse with metrics and errors"""
        
        response_data = {
            "flow_id": "test_456",
            "status": "failed",
            "message": "Generation failed",
            "metrics": {
                "execution_time": 5.2,
                "quality_score": 0.0,
                "word_count": 0
            },
            "errors": ["API timeout", "Retry limit exceeded"],
            "execution_time": 5.2
        }
        
        response = FlowExecutionResponse(**response_data)
        
        assert response.flow_id == "test_456"
        assert response.status == "failed"
        assert response.final_draft is None  # Default
        assert response.metrics["execution_time"] == 5.2
        assert len(response.errors) == 2
        assert "API timeout" in response.errors
    
    def test_flow_execution_response_missing_required(self):
        """Test FlowExecutionResponse with missing required fields"""
        
        response_data = {
            "flow_id": "test_789"
            # Missing status and message
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FlowExecutionResponse(**response_data)
        
        error_str = str(exc_info.value)
        assert "status" in error_str
        assert "message" in error_str
    
    def test_flow_status_response_running(self):
        """Test FlowStatusResponse for running flow"""
        
        status_data = {
            "flow_id": "test_456",
            "status": "running",
            "current_stage": "generate_draft",
            "progress_percent": 60.0,
            "start_time": "2025-01-01T10:00:00Z"
        }
        
        status = FlowStatusResponse(**status_data)
        
        assert status.flow_id == "test_456"
        assert status.status == "running"
        assert status.current_stage == "generate_draft"
        assert status.progress_percent == 60.0
        assert status.start_time == "2025-01-01T10:00:00Z"
        assert status.end_time is None  # Default
        assert status.metrics == {}     # Default
        assert status.errors == []      # Default
    
    def test_flow_status_response_completed(self):
        """Test FlowStatusResponse for completed flow"""
        
        status_data = {
            "flow_id": "test_789",
            "status": "completed",
            "current_stage": "completed",
            "progress_percent": 100.0,
            "start_time": "2025-01-01T10:00:00Z",
            "end_time": "2025-01-01T10:15:30Z",
            "metrics": {
                "execution_time": 930.5,
                "quality_score": 8.7,
                "word_count": 1250
            }
        }
        
        status = FlowStatusResponse(**status_data)
        
        assert status.flow_id == "test_789"
        assert status.status == "completed"
        assert status.progress_percent == 100.0
        assert status.metrics["quality_score"] == 8.7
        assert status.metrics["word_count"] == 1250
    
    def test_flow_status_response_failed(self):
        """Test FlowStatusResponse for failed flow"""
        
        status_data = {
            "flow_id": "test_fail",
            "status": "failed",
            "current_stage": "generate_draft",
            "errors": ["Connection timeout", "Max retries exceeded"]
        }
        
        status = FlowStatusResponse(**status_data)
        
        assert status.flow_id == "test_fail"
        assert status.status == "failed"
        assert len(status.errors) == 2
        assert "Connection timeout" in status.errors
    
    def test_flow_status_response_invalid_progress(self):
        """Test FlowStatusResponse with invalid progress percentage"""
        
        status_data = {
            "flow_id": "test_invalid",
            "status": "running",
            "progress_percent": "invalid"  # Should be float
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FlowStatusResponse(**status_data)
        
        assert "progress_percent" in str(exc_info.value)
    
    def test_health_check_response_healthy(self):
        """Test HealthCheckResponse for healthy system"""
        
        health_data = {
            "status": "healthy",
            "timestamp": "2025-01-01T10:00:00Z",
            "uptime_seconds": 3600.0,
            "components": {
                "linear_flow": "healthy",
                "monitoring": "healthy",
                "alerting": "healthy"
            }
        }
        
        health = HealthCheckResponse(**health_data)
        
        assert health.status == "healthy"
        assert health.timestamp == "2025-01-01T10:00:00Z"
        assert health.version == "2.0.0"  # Default
        assert health.uptime_seconds == 3600.0
        assert health.components["linear_flow"] == "healthy"
        assert len(health.components) == 3
    
    def test_health_check_response_warning(self):
        """Test HealthCheckResponse for system with warnings"""
        
        health_data = {
            "status": "warning",
            "timestamp": "2025-01-01T11:00:00Z",
            "uptime_seconds": 7200.0,
            "components": {
                "linear_flow": "healthy",
                "monitoring": "warning",
                "alerting": "healthy"
            }
        }
        
        health = HealthCheckResponse(**health_data)
        
        assert health.status == "warning"
        assert health.components["monitoring"] == "warning"
        assert health.uptime_seconds == 7200.0
    
    def test_health_check_response_critical(self):
        """Test HealthCheckResponse for critical system state"""
        
        health_data = {
            "status": "critical",
            "timestamp": "2025-01-01T12:00:00Z",
            "version": "2.1.0",  # Override default
            "uptime_seconds": 10800.0,
            "components": {
                "linear_flow": "critical",
                "monitoring": "healthy",
                "alerting": "failed"
            }
        }
        
        health = HealthCheckResponse(**health_data)
        
        assert health.status == "critical"
        assert health.version == "2.1.0"  # Overridden
        assert health.components["linear_flow"] == "critical"
        assert health.components["alerting"] == "failed"
    
    def test_health_check_response_missing_required(self):
        """Test HealthCheckResponse with missing required fields"""
        
        health_data = {
            "timestamp": "2025-01-01T10:00:00Z"
            # Missing status
        }
        
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckResponse(**health_data)
        
        assert "status" in str(exc_info.value)
    
    def test_all_models_serialization(self):
        """Test that all models can be serialized to JSON"""
        
        import json
        
        # Test request serialization
        request = FlowExecutionRequest(
            topic_title="Serialization Test",
            platform="LinkedIn",
            viral_score=7.5
        )
        request_json = json.dumps(request.dict())
        assert "Serialization Test" in request_json
        
        # Test response serialization
        response = FlowExecutionResponse(
            flow_id="serialize_123",
            status="completed",
            message="Serialization successful",
            metrics={"score": 8.5}
        )
        response_json = json.dumps(response.dict())
        assert "serialize_123" in response_json
        
        # Test status serialization
        status = FlowStatusResponse(
            flow_id="status_123",
            status="running",
            progress_percent=75.5
        )
        status_json = json.dumps(status.dict())
        assert "75.5" in status_json
        
        # Test health serialization
        health = HealthCheckResponse(
            status="healthy",
            timestamp="2025-01-01T10:00:00Z"
        )
        health_json = json.dumps(health.dict())
        assert "healthy" in health_json
    
    def test_model_field_validation(self):
        """Test field validation across all models"""
        
        # Test required vs optional fields
        
        # FlowExecutionRequest: topic_title is required
        with pytest.raises(ValidationError):
            FlowExecutionRequest()
        
        # But can create with just topic_title
        req = FlowExecutionRequest(topic_title="Test")
        assert req.topic_title == "Test"
        assert req.platform == "LinkedIn"  # Default
        
        # FlowExecutionResponse: flow_id, status, message are required
        with pytest.raises(ValidationError):
            FlowExecutionResponse(flow_id="test")  # Missing status, message
        
        # FlowStatusResponse: flow_id and status are required
        with pytest.raises(ValidationError):
            FlowStatusResponse(flow_id="test")  # Missing status
        
        # HealthCheckResponse: status and timestamp are required
        with pytest.raises(ValidationError):
            HealthCheckResponse(status="healthy")  # Missing timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])