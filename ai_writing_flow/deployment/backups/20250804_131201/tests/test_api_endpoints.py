#!/usr/bin/env python3
"""
Tests for AI Writing Flow V2 API Endpoints

Tests API functionality, request/response handling, and backward compatibility.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import API classes
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writing_flow.api.endpoints import (
    FlowAPI, 
    StandaloneFlowAPI,
    FlowExecutionRequest,
    FlowExecutionResponse,
    FlowStatusResponse,
    HealthCheckResponse
)


class TestFlowAPI:
    """Test FlowAPI class functionality"""
    
    @pytest.fixture
    def flow_api(self):
        """Create FlowAPI instance for testing"""
        return FlowAPI(storage_path="test_metrics")
    
    @pytest.mark.asyncio
    async def test_execute_flow_success(self, flow_api):
        """Test successful flow execution"""
        
        # Mock AIWritingFlowV2
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.return_value = mock_flow
            
            # Mock successful execution
            mock_state = Mock()
            mock_state.current_stage = "completed"
            mock_state.final_draft = "Generated content here"
            mock_state.error_message = None
            mock_state.quality_score = 8.5
            mock_state.style_score = 9.0
            mock_state.revision_count = 2
            mock_state.agents_executed = ["research", "draft", "style"]
            
            mock_flow.kickoff.return_value = mock_state
            
            # Test data
            request_data = {
                "topic_title": "AI Testing Best Practices",
                "platform": "LinkedIn",
                "content_type": "STANDALONE",
                "viral_score": 7.5
            }
            
            # Execute
            result = await flow_api.execute_flow(request_data)
            
            # Assertions
            assert result["status"] == "completed"
            assert result["final_draft"] == "Generated content here"
            assert result["metrics"]["quality_score"] == 8.5
            assert result["metrics"]["word_count"] == 3  # "Generated content here"
            assert len(result["errors"]) == 0
            assert result["execution_time"] > 0
            
            # Verify flow was called correctly
            mock_flow.kickoff.assert_called_once()
            call_args = mock_flow.kickoff.call_args[0][0]
            assert call_args["topic_title"] == "AI Testing Best Practices"
            assert call_args["platform"] == "LinkedIn"
    
    @pytest.mark.asyncio
    async def test_execute_flow_failure(self, flow_api):
        """Test flow execution failure handling"""
        
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.return_value = mock_flow
            
            # Mock failed execution
            mock_state = Mock()
            mock_state.current_stage = "failed"
            mock_state.final_draft = None
            mock_state.error_message = "Generation failed due to API timeout"
            
            mock_flow.kickoff.return_value = mock_state
            
            request_data = {
                "topic_title": "Test Topic",
                "platform": "Twitter"
            }
            
            result = await flow_api.execute_flow(request_data)
            
            # Assertions
            assert result["status"] == "failed"
            assert result["final_draft"] is None
            assert "Generation failed due to API timeout" in result["errors"]
            assert result["execution_time"] > 0
    
    @pytest.mark.asyncio
    async def test_execute_flow_exception(self, flow_api):
        """Test flow execution with exception"""
        
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            # Mock exception during flow creation
            mock_flow_class.side_effect = Exception("Flow initialization failed")
            
            request_data = {
                "topic_title": "Test Topic"
            }
            
            result = await flow_api.execute_flow(request_data)
            
            # Assertions
            assert result["status"] == "error"
            assert "Flow initialization failed" in result["errors"][0]
            assert result["final_draft"] is None
    
    @pytest.mark.asyncio
    async def test_get_flow_status_completed(self, flow_api):
        """Test getting status of completed flow"""
        
        # Simulate completed flow
        flow_id = "test_flow_123"
        flow_api._flow_results[flow_id] = {
            "status": "completed",
            "metrics": {"execution_time": 15.5, "quality_score": 8.0},
            "errors": []
        }
        
        result = await flow_api.get_flow_status(flow_id)
        
        assert result["flow_id"] == flow_id
        assert result["status"] == "completed"
        assert result["current_stage"] == "completed"
        assert result["progress_percent"] == 100.0
        assert result["metrics"]["execution_time"] == 15.5
    
    @pytest.mark.asyncio
    async def test_get_flow_status_running(self, flow_api):
        """Test getting status of running flow"""
        
        # Simulate running flow
        flow_id = "test_flow_456"
        mock_flow = Mock()
        mock_ui_bridge = Mock()
        mock_ui_bridge.get_session_info.return_value = {
            "current_stage": "generate_draft",
            "start_time": Mock(isoformat=lambda: "2025-01-01T10:00:00Z"),
            "metrics": {"stages_completed": 2}
        }
        mock_flow.ui_bridge = mock_ui_bridge
        
        flow_api._active_flows[flow_id] = mock_flow
        
        result = await flow_api.get_flow_status(flow_id)
        
        assert result["flow_id"] == flow_id
        assert result["status"] == "running"
        assert result["current_stage"] == "generate_draft"
        assert result["start_time"] == "2025-01-01T10:00:00Z"
    
    @pytest.mark.asyncio
    async def test_get_flow_status_not_found(self, flow_api):
        """Test getting status of non-existent flow"""
        
        result = await flow_api.get_flow_status("nonexistent_flow")
        
        assert result["flow_id"] == "nonexistent_flow"
        assert result["status"] == "not_found"
        assert "not found" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_get_health_check_healthy(self, flow_api):
        """Test health check when system is healthy"""
        
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.return_value = mock_flow
            
            mock_flow.get_health_status.return_value = {
                "overall_status": "healthy",
                "timestamp": "2025-01-01T10:00:00Z",
                "components": {
                    "linear_flow": {"status": "healthy"},
                    "monitoring": {"status": "healthy"}
                }
            }
            
            result = await flow_api.get_health_check()
            
            assert result["overall_status"] == "healthy"
            assert result["version"] == "2.0.0"
            assert "api_statistics" in result
            assert result["api_statistics"]["total_requests"] >= 0
    
    @pytest.mark.asyncio
    async def test_get_health_check_error(self, flow_api):
        """Test health check when there's an error"""
        
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            mock_flow_class.side_effect = Exception("Health check failed")
            
            result = await flow_api.get_health_check()
            
            assert result["status"] == "critical"
            assert "Health check failed" in result["error"]
            assert result["version"] == "2.0.0"
    
    @pytest.mark.asyncio 
    async def test_get_dashboard_metrics(self, flow_api):
        """Test dashboard metrics endpoint"""
        
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.return_value = mock_flow
            
            mock_flow.get_dashboard_metrics.return_value = {
                "monitoring_enabled": True,
                "dashboard_metrics": {
                    "success_rate": 95.5,
                    "throughput": 12.3,
                    "avg_execution_time": 4.2
                }
            }
            
            result = await flow_api.get_dashboard_metrics()
            
            assert result["monitoring_enabled"] is True
            assert "api_metrics" in result
            assert result["api_metrics"]["active_flows"] == 0
    
    @pytest.mark.asyncio
    async def test_list_flows(self, flow_api):
        """Test listing flows"""
        
        # Add some test data
        flow_api._flow_results["flow_1"] = {
            "status": "completed",
            "execution_time": 10.5,
            "metrics": {"word_count": 500, "quality_score": 8.5}
        }
        flow_api._flow_results["flow_2"] = {
            "status": "failed", 
            "execution_time": 5.2,
            "metrics": {"word_count": 0, "quality_score": 0}
        }
        flow_api._active_flows["flow_3"] = Mock()
        
        result = await flow_api.list_flows()
        
        assert len(result["flows"]) == 3
        assert result["active_count"] == 1
        assert result["completed_count"] == flow_api._api_stats["successful_executions"]
        assert result["failed_count"] == flow_api._api_stats["failed_executions"]
    
    @pytest.mark.asyncio
    async def test_list_flows_with_filter(self, flow_api):
        """Test listing flows with status filter"""
        
        flow_api._flow_results["flow_1"] = {"status": "completed", "execution_time": 10.5, "metrics": {}}
        flow_api._flow_results["flow_2"] = {"status": "failed", "execution_time": 5.2, "metrics": {}}
        
        result = await flow_api.list_flows(status_filter="completed")
        
        # Should only return completed flows
        assert len(result["flows"]) == 1
        assert result["flows"][0]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_legacy_kickoff(self, flow_api):
        """Test legacy compatibility endpoint"""
        
        with patch.object(flow_api, 'execute_flow') as mock_execute:
            mock_execute.return_value = {
                "status": "completed",
                "flow_id": "test_flow",
                "final_draft": "Generated content",
                "metrics": {"execution_time": 12.3},
                "errors": [],
                "execution_time": 12.3
            }
            
            legacy_request = {
                "topic_title": "Legacy Test",
                "platform": "Twitter"
            }
            
            result = await flow_api.legacy_kickoff(legacy_request)
            
            assert result["success"] is True
            assert result["flow_id"] == "test_flow"
            assert result["final_draft"] == "Generated content"
            assert result["execution_time"] == 12.3
            assert result["error_message"] is None


class TestStandaloneFlowAPI:
    """Test StandaloneFlowAPI for non-FastAPI environments"""
    
    @pytest.fixture
    def standalone_api(self):
        """Create StandaloneFlowAPI instance"""
        return StandaloneFlowAPI(storage_path="test_metrics")
    
    @pytest.mark.asyncio
    async def test_handle_execute_request(self, standalone_api):
        """Test handling execute flow request"""
        
        with patch.object(standalone_api.flow_api, 'execute_flow') as mock_execute:
            mock_execute.return_value = {"status": "completed", "flow_id": "test"}
            
            result = await standalone_api.handle_request(
                "POST", 
                "/api/v2/flows/execute",
                {"topic_title": "Test"}
            )
            
            assert result["status"] == "completed"
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_status_request(self, standalone_api):
        """Test handling flow status request"""
        
        with patch.object(standalone_api.flow_api, 'get_flow_status') as mock_status:
            mock_status.return_value = {"flow_id": "test_123", "status": "running"}
            
            result = await standalone_api.handle_request(
                "GET", 
                "/api/v2/flows/test_123/status"
            )
            
            assert result["flow_id"] == "test_123"
            mock_status.assert_called_once_with("test_123")
    
    @pytest.mark.asyncio
    async def test_handle_health_request(self, standalone_api):
        """Test handling health check request"""
        
        with patch.object(standalone_api.flow_api, 'get_health_check') as mock_health:
            mock_health.return_value = {"status": "healthy"}
            
            result = await standalone_api.handle_request("GET", "/api/v2/health")
            
            assert result["status"] == "healthy"
            mock_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_unknown_endpoint(self, standalone_api):
        """Test handling unknown endpoint"""
        
        result = await standalone_api.handle_request("GET", "/api/unknown")
        
        assert "Endpoint not found" in result["error"]
        assert result["status_code"] == 404
    
    @pytest.mark.asyncio
    async def test_handle_request_exception(self, standalone_api):
        """Test handling request with exception"""
        
        with patch.object(standalone_api.flow_api, 'get_health_check') as mock_health:
            mock_health.side_effect = Exception("Internal error")
            
            result = await standalone_api.handle_request("GET", "/api/v2/health")
            
            assert "Request handling error" in result["error"]
            assert result["status_code"] == 500


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
    
    def test_flow_execution_request_missing_required(self):
        """Test FlowExecutionRequest with missing required field"""
        
        request_data = {
            "platform": "Twitter"
            # Missing topic_title
        }
        
        with pytest.raises(ValueError):
            FlowExecutionRequest(**request_data)
    
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
        assert response.final_draft == "Generated content"
        assert response.execution_time == 12.5
        assert response.metrics == {}  # Default
        assert response.errors == []   # Default
    
    def test_flow_status_response_valid(self):
        """Test valid FlowStatusResponse"""
        
        status_data = {
            "flow_id": "test_456",
            "status": "running",
            "current_stage": "generate_draft",
            "progress_percent": 60.0
        }
        
        status = FlowStatusResponse(**status_data)
        
        assert status.flow_id == "test_456"
        assert status.status == "running"
        assert status.current_stage == "generate_draft"
        assert status.progress_percent == 60.0
    
    def test_health_check_response_valid(self):
        """Test valid HealthCheckResponse"""
        
        health_data = {
            "status": "healthy",
            "timestamp": "2025-01-01T10:00:00Z",
            "uptime_seconds": 3600.0
        }
        
        health = HealthCheckResponse(**health_data)
        
        assert health.status == "healthy"
        assert health.timestamp == "2025-01-01T10:00:00Z"
        assert health.version == "2.0.0"  # Default
        assert health.uptime_seconds == 3600.0


class TestAPIIntegration:
    """Integration tests for complete API workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_flow_execution_workflow(self):
        """Test complete workflow: execute -> check status -> get results"""
        
        flow_api = FlowAPI()
        
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.return_value = mock_flow
            
            # Mock successful execution
            mock_state = Mock()
            mock_state.current_stage = "completed"
            mock_state.final_draft = "Complete article content"
            mock_state.error_message = None
            mock_state.quality_score = 9.0
            mock_state.style_score = 8.5
            mock_state.revision_count = 1
            mock_state.agents_executed = ["research", "draft", "style", "quality"]
            
            mock_flow.kickoff.return_value = mock_state
            
            # Step 1: Execute flow
            execution_result = await flow_api.execute_flow({
                "topic_title": "Complete Workflow Test",
                "platform": "LinkedIn"
            })
            
            flow_id = execution_result["flow_id"]
            
            assert execution_result["status"] == "completed"
            assert execution_result["final_draft"] == "Complete article content"
            
            # Step 2: Check status (should be completed)
            status_result = await flow_api.get_flow_status(flow_id)
            
            assert status_result["status"] == "completed"
            assert status_result["progress_percent"] == 100.0
            
            # Step 3: Verify it appears in flow list
            list_result = await flow_api.list_flows()
            
            flow_ids = [flow["flow_id"] for flow in list_result["flows"]]
            assert flow_id in flow_ids
    
    @pytest.mark.asyncio
    async def test_api_statistics_tracking(self):
        """Test that API statistics are properly tracked"""
        
        flow_api = FlowAPI()
        initial_requests = flow_api._api_stats["total_requests"]
        
        with patch('ai_writing_flow.api.endpoints.AIWritingFlowV2') as mock_flow_class:
            mock_flow = Mock()
            mock_flow_class.return_value = mock_flow
            
            # Mock successful execution
            mock_state = Mock()
            mock_state.current_stage = "completed"
            mock_state.final_draft = "Success"
            mock_state.error_message = None
            
            mock_flow.kickoff.return_value = mock_state
            
            # Execute multiple flows
            await flow_api.execute_flow({"topic_title": "Test 1"})
            await flow_api.execute_flow({"topic_title": "Test 2"})
            
            # Check statistics
            assert flow_api._api_stats["total_requests"] == initial_requests + 2
            assert flow_api._api_stats["successful_executions"] >= 2
            
            # Health check should include statistics
            health_result = await flow_api.get_health_check()
            assert "api_statistics" in health_result
            assert health_result["api_statistics"]["total_requests"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])