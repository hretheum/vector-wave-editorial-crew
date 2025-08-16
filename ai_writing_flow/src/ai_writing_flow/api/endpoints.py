"""
AI Writing Flow V2 API Endpoints

REST API endpoints for executing and monitoring AI Writing Flow V2.
Provides backward compatibility with existing Kolegium system.

Key Features:
- Flow execution endpoints
- Real-time monitoring APIs  
- Health check endpoints
- Dashboard data APIs
- Legacy API compatibility
"""

import json
import asyncio
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
    from fastapi.responses import JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    # Fallback for environments without FastAPI
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = None
    JSONResponse = None

from ..ai_writing_flow_v2 import AIWritingFlowV2
from ..models import WritingFlowState
from ..monitoring.dashboard_api import DashboardAPI, TimeRange


# Request/Response Models
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


class FlowAPI:
    """
    AI Writing Flow V2 API Handler
    
    Provides REST API endpoints for flow execution and monitoring.
    Designed to be framework-agnostic but optimized for FastAPI.
    """
    
    def __init__(self, 
                 storage_path: Optional[str] = None,
                 enable_cors: bool = True):
        """
        Initialize Flow API
        
        Args:
            storage_path: Optional custom storage path for metrics
            enable_cors: Enable CORS middleware
        """
        self.storage_path = storage_path
        self.enable_cors = enable_cors
        
        # Flow instance cache (in production, use Redis or similar)
        self._active_flows: Dict[str, AIWritingFlowV2] = {}
        self._flow_results: Dict[str, Dict[str, Any]] = {}
        
        # API statistics
        self._api_stats = {
            "total_requests": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "start_time": datetime.now(timezone.utc)
        }
    
    async def execute_flow(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute AI Writing Flow V2
        
        Args:
            request_data: Flow execution parameters
            
        Returns:
            Flow execution result
        """
        try:
            # Validate request
            flow_request = FlowExecutionRequest(**request_data)
            
            # Generate flow ID
            flow_id = f"flow_{int(datetime.now().timestamp())}"
            
            # Create flow instance
            flow_v2 = AIWritingFlowV2(
                monitoring_enabled=flow_request.monitoring_enabled,
                alerting_enabled=flow_request.alerting_enabled,
                quality_gates_enabled=flow_request.quality_gates_enabled,
                storage_path=self.storage_path
            )
            
            self._active_flows[flow_id] = flow_v2
            self._api_stats["total_requests"] += 1
            
            # Prepare inputs
            flow_inputs = {
                "topic_title": flow_request.topic_title,
                "platform": flow_request.platform,
                "file_path": flow_request.file_path or "",
                "content_type": flow_request.content_type,
                "content_ownership": flow_request.content_ownership,
                "viral_score": flow_request.viral_score,
                "editorial_recommendations": flow_request.editorial_recommendations,
                "skip_research": flow_request.skip_research
            }
            
            # Execute flow
            start_time = datetime.now()
            final_state = flow_v2.kickoff(flow_inputs)
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            # Determine success/failure
            success = final_state.current_stage != "failed"
            
            if success:
                self._api_stats["successful_executions"] += 1
            else:
                self._api_stats["failed_executions"] += 1
            
            # Build response
            # Be defensive about optional attributes when mocked in tests
            agents_attr = getattr(final_state, 'agents_executed', None)
            agents_count = len(agents_attr) if isinstance(agents_attr, list) else 0
            response_data = {
                "flow_id": flow_id,
                "status": "completed" if success else "failed",
                "message": "Flow executed successfully" if success else f"Flow failed: {final_state.error_message}",
                "final_draft": final_state.final_draft if success else None,
                "metrics": {
                    "execution_time": execution_time,
                    "quality_score": getattr(final_state, 'quality_score', 0),
                    "style_score": getattr(final_state, 'style_score', 0),
                    "revision_count": getattr(final_state, 'revision_count', 0),
                    "agents_executed": agents_count,
                    "word_count": len(final_state.final_draft.split()) if final_state.final_draft else 0
                },
                "errors": [final_state.error_message] if final_state.error_message else [],
                "execution_time": execution_time
            }
            
            # Cache result
            self._flow_results[flow_id] = response_data
            
            # Cleanup active flow
            if flow_id in self._active_flows:
                del self._active_flows[flow_id]
            
            return response_data
            
        except Exception as e:
            self._api_stats["failed_executions"] += 1
            
            # If flow was already started and we have a final_state, treat as a failed execution
            flow_id_value = flow_id if 'flow_id' in locals() else "unknown"
            if 'final_state' in locals():
                try:
                    fs_error = getattr(final_state, 'error_message', None)
                except Exception:
                    fs_error = None
                error_list = [msg for msg in [fs_error, str(e)] if msg]
                return {
                    "flow_id": flow_id_value,
                    "status": "failed",
                    "message": f"Flow failed: {fs_error or str(e)}",
                    "final_draft": None,
                    "metrics": {},
                    "errors": error_list + [traceback.format_exc()],
                    "execution_time": 0.0
                }
            
            # Otherwise it's an API error before the flow started
            return {
                "flow_id": flow_id_value,
                "status": "error",
                "message": f"API execution error: {str(e)}",
                "final_draft": None,
                "metrics": {},
                "errors": [str(e), traceback.format_exc()],
                "execution_time": 0.0
            }
    
    async def get_flow_status(self, flow_id: str) -> Dict[str, Any]:
        """
        Get status of specific flow execution
        
        Args:
            flow_id: Flow execution ID
            
        Returns:
            Flow status information
        """
        # Check completed results first
        if flow_id in self._flow_results:
            result = self._flow_results[flow_id]
            return {
                "flow_id": flow_id,
                "status": result["status"],
                "current_stage": "completed" if result["status"] == "completed" else "failed",
                "progress_percent": 100.0,
                "start_time": None,  # Would be stored in production
                "end_time": None,    # Would be stored in production
                "metrics": result["metrics"],
                "errors": result["errors"]
            }
        
        # Check active flows
        if flow_id in self._active_flows:
            flow = self._active_flows[flow_id]
            
            # Get progress from UI bridge if available
            progress_info = {}
            if hasattr(flow, 'ui_bridge') and flow.ui_bridge:
                session_info = flow.ui_bridge.get_session_info(flow_id)
                if session_info:
                    # Robust handling of start_time which may be a datetime-like object with isoformat(),
                    # a plain string, a dict exposing isoformat, or a Mock in tests.
                    start_time_value = None
                    raw_start_time = session_info.get("start_time")
                    if isinstance(raw_start_time, str):
                        start_time_value = raw_start_time
                    else:
                        iso_attr = getattr(raw_start_time, "isoformat", None) if raw_start_time is not None else None
                        if callable(iso_attr):
                            try:
                                start_time_value = iso_attr()
                            except Exception:
                                start_time_value = None
                        elif isinstance(raw_start_time, dict):
                            iso_callable = raw_start_time.get("isoformat")
                            if callable(iso_callable):
                                try:
                                    start_time_value = iso_callable()
                                except Exception:
                                    start_time_value = None
                    progress_info = {
                        "current_stage": session_info.get("current_stage", "unknown"),
                        "progress_percent": None,  # Would calculate from stage progress
                        "start_time": start_time_value,
                        "metrics": session_info.get("metrics", {})
                    }
            
            return {
                "flow_id": flow_id,
                "status": "running",
                "current_stage": progress_info.get("current_stage", "executing"),
                "progress_percent": progress_info.get("progress_percent"),
                "start_time": progress_info.get("start_time"),
                "end_time": None,
                "metrics": progress_info.get("metrics", {}),
                "errors": []
            }
        
        # Flow not found
        return {
            "flow_id": flow_id,
            "status": "not_found",
            "current_stage": None,
            "progress_percent": None,
            "start_time": None,
            "end_time": None,
            "metrics": {},
            "errors": [f"Flow {flow_id} not found"]
        }
    
    async def get_health_check(self) -> Dict[str, Any]:
        """
        Get system health status
        
        Returns:
            System health information
        """
        # Create a temporary flow to check system health
        try:
            temp_flow = AIWritingFlowV2(
                monitoring_enabled=True,
                alerting_enabled=False,  # Don't trigger alerts during health check
                quality_gates_enabled=True
            )
            
            health_status = temp_flow.get_health_status()

            # Ensure we always return a plain dict (tests may mock this method)
            if not isinstance(health_status, dict):
                health_status = {}

            # Add API-specific health info
            uptime = (datetime.now(timezone.utc) - self._api_stats["start_time"]).total_seconds()

            result: Dict[str, Any] = {
                **health_status,
                "version": "2.0.0",
                "api_statistics": {
                    "total_requests": self._api_stats["total_requests"],
                    "successful_executions": self._api_stats["successful_executions"],
                    "failed_executions": self._api_stats["failed_executions"],
                    "success_rate": (
                        self._api_stats["successful_executions"] / max(self._api_stats["total_requests"], 1) * 100
                    ),
                    "active_flows": len(self._active_flows),
                    "cached_results": len(self._flow_results),
                },
                "uptime_seconds": uptime,
            }

            # Guarantee a timestamp field for consumers if missing
            if "timestamp" not in result:
                result["timestamp"] = datetime.now(timezone.utc).isoformat()

            return result
            
        except Exception as e:
            return {
                "status": "critical",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "2.0.0",
                "error": f"Health check failed: {str(e)}",
                "uptime_seconds": 0.0
            }
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get dashboard metrics data
        
        Returns:
            Dashboard metrics for monitoring UI
        """
        try:
            # Create temporary flow to access dashboard API
            temp_flow = AIWritingFlowV2(monitoring_enabled=True)
            dashboard_metrics = temp_flow.get_dashboard_metrics()
            
            # Add API-specific metrics
            dashboard_metrics["api_metrics"] = {
                "total_requests": self._api_stats["total_requests"],
                "request_rate": self._calculate_request_rate(),
                "active_flows": len(self._active_flows),
                "cached_results": len(self._flow_results)
            }
            
            return dashboard_metrics
            
        except Exception as e:
            return {
                "error": f"Failed to get dashboard metrics: {str(e)}",
                "monitoring_enabled": False
            }
    
    async def list_flows(self, limit: int = 50, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        List recent flow executions
        
        Args:
            limit: Maximum number of flows to return
            status_filter: Optional status filter ("completed", "failed", "running")
            
        Returns:
            List of flow executions
        """
        flows = []
        
        # Add completed/failed flows
        for flow_id, result in list(self._flow_results.items())[-limit:]:
            if status_filter is None or result["status"] == status_filter:
                flows.append({
                    "flow_id": flow_id,
                    "status": result["status"],
                    "topic_title": "Unknown",  # Would be stored in production
                    "execution_time": result["execution_time"],
                    "word_count": result["metrics"].get("word_count", 0),
                    "quality_score": result["metrics"].get("quality_score", 0)
                })
        
        # Add active flows
        if status_filter is None or status_filter == "running":
            for flow_id in self._active_flows.keys():
                flows.append({
                    "flow_id": flow_id,
                    "status": "running",
                    "topic_title": "Unknown",
                    "execution_time": 0.0,
                    "word_count": 0,
                    "quality_score": 0
                })
        
        return {
            "flows": flows[-limit:],
            "total_count": len(flows),
            "active_count": len(self._active_flows),
            "completed_count": self._api_stats["successful_executions"],
            "failed_count": self._api_stats["failed_executions"]
        }
    
    def _calculate_request_rate(self) -> float:
        """Calculate requests per minute over last hour"""
        uptime_minutes = (datetime.now(timezone.utc) - self._api_stats["start_time"]).total_seconds() / 60
        if uptime_minutes > 0:
            return self._api_stats["total_requests"] / uptime_minutes
        return 0.0
    
    # Legacy compatibility endpoints
    
    async def legacy_kickoff(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy compatibility endpoint for existing Kolegium integration
        
        Args:
            request_data: Legacy format request data
            
        Returns:
            Legacy format response
        """
        # Convert legacy format to V2 format
        v2_request = {
            "topic_title": request_data.get("topic_title", ""),
            "platform": request_data.get("platform", "LinkedIn"),
            "file_path": request_data.get("file_path", ""),
            "content_type": request_data.get("content_type", "STANDALONE"),
            "content_ownership": request_data.get("content_ownership", "EXTERNAL"),
            "viral_score": request_data.get("viral_score", 0.0),
            "editorial_recommendations": request_data.get("editorial_recommendations", ""),
            "skip_research": request_data.get("skip_research", False)
        }
        
        # Execute using V2 API
        result = await self.execute_flow(v2_request)
        
        # Convert back to legacy format
        legacy_response = {
            "success": result["status"] in ["completed"],
            "flow_id": result["flow_id"],
            "final_draft": result["final_draft"],
            "metrics": result["metrics"],
            "execution_time": result["execution_time"],
            "error_message": result["errors"][0] if result["errors"] else None
        }
        
        return legacy_response


def create_flow_app(storage_path: Optional[str] = None) -> Optional[FastAPI]:
    """
    Create FastAPI application with AI Writing Flow V2 endpoints
    
    Args:
        storage_path: Optional custom storage path for metrics
        
    Returns:
        FastAPI application or None if FastAPI not available
    """
    if not FASTAPI_AVAILABLE:
        print("Warning: FastAPI not available. Install with: pip install fastapi uvicorn")
        return None
    
    app = FastAPI(
        title="AI Writing Flow V2 API",
        description="REST API for AI Writing Flow V2 execution and monitoring",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize API handler
    flow_api = FlowAPI(storage_path=storage_path)
    
    @app.post("/api/v2/flows/execute", response_model=FlowExecutionResponse)
    async def execute_flow(request: FlowExecutionRequest):
        """Execute AI Writing Flow V2"""
        result = await flow_api.execute_flow(request.dict())
        return FlowExecutionResponse(**result)
    
    @app.get("/api/v2/flows/{flow_id}/status", response_model=FlowStatusResponse) 
    async def get_flow_status(flow_id: str):
        """Get status of specific flow execution"""
        result = await flow_api.get_flow_status(flow_id)
        return FlowStatusResponse(**result)
    
    @app.get("/api/v2/health", response_model=HealthCheckResponse)
    async def health_check():
        """System health check"""
        result = await flow_api.get_health_check()
        return HealthCheckResponse(**result)
    
    @app.get("/api/v2/dashboard/metrics")
    async def get_dashboard_metrics():
        """Get dashboard metrics"""
        return await flow_api.get_dashboard_metrics()
    
    @app.get("/api/v2/flows")
    async def list_flows(limit: int = 50, status: Optional[str] = None):
        """List recent flow executions"""
        return await flow_api.list_flows(limit=limit, status_filter=status)
    
    # Legacy compatibility endpoints
    
    @app.post("/api/v1/kickoff")
    async def legacy_kickoff(request: Request):
        """Legacy compatibility endpoint"""
        request_data = await request.json()
        return await flow_api.legacy_kickoff(request_data)
    
    @app.get("/api/v1/health")
    async def legacy_health():
        """Legacy health check"""
        result = await flow_api.get_health_check()
        return {
            "status": result["status"],
            "version": result["version"]
        }
    
    @app.get("/")
    async def root():
        """API root endpoint"""
        return {
            "service": "AI Writing Flow V2 API",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "execute_flow": "/api/v2/flows/execute",
                "flow_status": "/api/v2/flows/{flow_id}/status",
                "health_check": "/api/v2/health",
                "dashboard": "/api/v2/dashboard/metrics",
                "list_flows": "/api/v2/flows",
                "docs": "/docs"
            },
            "legacy_endpoints": {
                "kickoff": "/api/v1/kickoff",
                "health": "/api/v1/health"
            }
        }
    
    return app


# Standalone API handler for non-FastAPI environments
class StandaloneFlowAPI:
    """
    Standalone API handler for environments without FastAPI
    
    Can be used with Flask, Django, or custom HTTP servers
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.flow_api = FlowAPI(storage_path=storage_path)
    
    async def handle_request(self, method: str, path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle API request
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            data: Request data for POST requests
            
        Returns:
            Response data
        """
        try:
            if method == "POST" and path == "/api/v2/flows/execute":
                return await self.flow_api.execute_flow(data or {})
            
            elif method == "GET" and path.startswith("/api/v2/flows/") and path.endswith("/status"):
                flow_id = path.split("/")[-2]
                return await self.flow_api.get_flow_status(flow_id)
            
            elif method == "GET" and path == "/api/v2/health":
                return await self.flow_api.get_health_check()
            
            elif method == "GET" and path == "/api/v2/dashboard/metrics":
                return await self.flow_api.get_dashboard_metrics()
            
            elif method == "GET" and path == "/api/v2/flows":
                return await self.flow_api.list_flows()
            
            elif method == "POST" and path == "/api/v1/kickoff":
                return await self.flow_api.legacy_kickoff(data or {})
            
            else:
                return {
                    "error": f"Endpoint not found: {method} {path}",
                    "status_code": 404
                }
                
        except Exception as e:
            return {
                "error": f"Request handling error: {str(e)}",
                "status_code": 500
            }


# Export main classes
__all__ = [
    "FlowAPI", 
    "create_flow_app", 
    "StandaloneFlowAPI",
    "FlowExecutionRequest",
    "FlowExecutionResponse", 
    "FlowStatusResponse",
    "HealthCheckResponse"
]