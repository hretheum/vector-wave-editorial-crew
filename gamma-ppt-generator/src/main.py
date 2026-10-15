#!/usr/bin/env python3
"""
Gamma PPT Generator Service - Task 4.1.1
API wrapper service with circuit breaker for Gamma.app integration

Port: 8003
Objective: Create Gamma.app API wrapper service with circuit breaker
"""

import os
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel

# Internal imports
from models import (
    GammaGenerationRequest, GammaGenerationResponse, 
    HealthResponse, ServiceStatus, GammaTestResponse
)
from gamma_client import GammaAPIClient
from circuit_breaker import GammaCircuitBreaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Initialize FastAPI app
app = FastAPI(
    title="Gamma PPT Generator Service",
    description="Gamma.app API wrapper for AI-powered presentations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Generation", "description": "Presentation generation endpoints"},
        {"name": "System", "description": "Health checks and monitoring"}
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
service_state = {
    "start_time": time.time(),
    "gamma_client": None,
    "circuit_breaker": None,
    "health_status": "starting",
    "generation_count": 0,
    "total_cost": 0.0
}

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract user from JWT token (placeholder implementation)"""
    # TODO: Implement proper JWT validation
    return "user_dev"  # Development placeholder

@app.on_event("startup")
async def startup_event():
    """Initialize Gamma PPT Generator Service on startup"""
    logger.info("🚀 Starting Gamma PPT Generator Service...")
    
    try:
        # Initialize Gamma.app API client
        # Support multiple env var names for the API key
        gamma_api_key = (
            os.getenv("GAMMA_API_KEY")
            or os.getenv("GAMMA_PPT_API_KEY")
            or os.getenv("GAMMA_TOKEN")
        )
        if not gamma_api_key:
            logger.warning("⚠️ GAMMA_API_KEY not set (also checked GAMMA_PPT_API_KEY, GAMMA_TOKEN) - service will run in demo mode")
        
        service_state["gamma_client"] = GammaAPIClient(
            api_key=gamma_api_key,
            demo_mode=not bool(gamma_api_key)
        )
        
        # Initialize circuit breaker
        service_state["circuit_breaker"] = GammaCircuitBreaker(
            failure_threshold=3,  # Lower threshold for external API
            recovery_timeout=120,  # Longer recovery time for external service
            success_threshold=2
        )
        
        # Test Gamma API connection
        if gamma_api_key:
            try:
                await service_state["circuit_breaker"].call_with_circuit_breaker(
                    "gamma_api",
                    service_state["gamma_client"].test_connection
                )
                logger.info("✅ Gamma.app API connection verified")
            except Exception as e:
                logger.warning(f"⚠️ Gamma.app API test failed: {e}")
        
        service_state["health_status"] = "healthy"
        logger.info("✅ Gamma PPT Generator Service initialized successfully")
        logger.info("🎨 Ready for AI-powered presentation generation")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        service_state["health_status"] = "unhealthy"
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Gamma PPT Generator Service shutting down...")

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with service information"""
    uptime = time.time() - service_state["start_time"]
    
    # Detect API key presence for UI/reporting
    gamma_api_key_present = bool(
        os.getenv("GAMMA_API_KEY")
        or os.getenv("GAMMA_PPT_API_KEY")
        or os.getenv("GAMMA_TOKEN")
    )

    return {
        "service": "Gamma PPT Generator Service",
        "description": "Gamma.app API wrapper for AI-powered presentations",
        "version": "1.0.0",
        "status": service_state["health_status"],
        "port": 8003,
        "capabilities": {
            "presentation_generation": "AI-powered presentations via Gamma.app",
            "cost_tracking": "Per-generation cost monitoring",
            "rate_limiting": "API usage control and burst handling",
            "circuit_breaker": "Fault tolerance for external API calls"
        },
        "gamma_integration": {
            "api_status": "connected" if gamma_api_key_present else "demo_mode",
            "monthly_limit": "50 generations (Beta)",
            "supported_formats": ["PDF", "PPTX"],
            "languages": "60+ supported"
        },
        "usage_stats": {
            "generations_completed": service_state["generation_count"],
            "estimated_cost": f"${service_state['total_cost']:.2f}",
            "uptime_seconds": uptime
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Comprehensive health check with Gamma API connectivity"""
    try:
        health_data = {
            "status": service_state["health_status"],
            "service": "gamma-ppt-generator",
            "version": "1.0.0",
            "port": 8003,
            "timestamp": datetime.now(),
            "uptime_seconds": time.time() - service_state["start_time"]
        }
        
        # Check Gamma API connectivity
        if service_state["gamma_client"]:
            try:
                gamma_status = await service_state["gamma_client"].get_status()
                health_data["gamma_api_status"] = gamma_status.status
                health_data["api_calls_remaining"] = gamma_status.remaining_calls
                health_data["monthly_usage"] = gamma_status.monthly_usage
            except Exception as e:
                health_data["gamma_api_status"] = "error"
                health_data["gamma_api_error"] = str(e)
        else:
            health_data["gamma_api_status"] = "not_configured"
        
        # Check circuit breaker state
        if service_state["circuit_breaker"]:
            cb_state = service_state["circuit_breaker"].get_state("gamma_api")
            health_data["circuit_breaker_state"] = cb_state.get("gamma_api", {}).get("state", "UNKNOWN")
        
        return HealthResponse(**health_data)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "health_check_failed",
                "message": "Service health check encountered an error",
                "details": str(e)
            }
        )

@app.post("/test-gamma-connectivity", response_model=GammaTestResponse, tags=["System"])
async def test_gamma_connectivity(current_user: str = Depends(get_current_user)):
    """Test connectivity to Gamma.app API"""
    
    logger.info("🧪 Testing Gamma.app API connectivity...")
    
    try:
        if not service_state["gamma_client"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gamma client not initialized"
            )
        
        # Test connection through circuit breaker
        test_result = await service_state["circuit_breaker"].call_with_circuit_breaker(
            "gamma_api",
            service_state["gamma_client"].test_connection
        )
        
        response = GammaTestResponse(
            status="success",
            connection_test=test_result.connected,
            response_time_ms=test_result.response_time_ms,
            api_version=test_result.api_version,
            monthly_limits=test_result.limits,
            tested_at=datetime.now()
        )
        
        logger.info("✅ Gamma.app connectivity test successful")
        return response
        
    except Exception as e:
        logger.error(f"❌ Gamma connectivity test failed: {e}")
        
        return GammaTestResponse(
            status="failed",
            connection_test=False,
            response_time_ms=0.0,
            api_version="unknown",
            monthly_limits={},
            error_message=str(e),
            tested_at=datetime.now()
        )

# Presentation Generation Endpoints
@app.post("/generate/presentation",
          response_model=GammaGenerationResponse,
          tags=["Generation"])
async def generate_presentation(
    request: GammaGenerationRequest,
    current_user: str = Depends(get_current_user)
):
    """Generate AI-powered presentation using Gamma.app"""
    
    generation_id = f"gamma_{uuid.uuid4().hex[:12]}"
    logger.info(f"🎨 Starting presentation generation: {generation_id}")
    
    try:
        # Validate request
        if not request.topic or not request.topic.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topic title is required for presentation generation"
            )
        
        # Check if Gamma client is available
        if not service_state["gamma_client"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gamma API client not initialized"
            )
        
        # Generate presentation through circuit breaker
        generation_result = await service_state["circuit_breaker"].call_with_circuit_breaker(
            "gamma_api",
            service_state["gamma_client"].generate_presentation,
            request.dict()
        )

        # If Gamma API indicates failure or missing essential data, map to failed response
        if (
            not getattr(generation_result, "success", False)
            or (
                not generation_result.preview_url
                and not generation_result.download_urls
                and not generation_result.presentation_id
            )
        ):
            error_parts = []
            if getattr(generation_result, "error_code", None):
                error_parts.append(str(generation_result.error_code))
            if getattr(generation_result, "error_message", None):
                error_parts.append(str(generation_result.error_message))
            error_text = ": ".join(error_parts) if error_parts else "Gamma API returned an incomplete or error response"

            logger.warning(f"❗ Gamma generation failed ({generation_id}): {error_text}")
            return GammaGenerationResponse(
                generation_id=generation_id,
                status="failed",
                gamma_presentation_id=None,
                preview_url=None,
                download_urls=None,
                slides_count=None,
                generation_time_ms=getattr(generation_result, "processing_time_ms", None),
                cost=None,
                error_message=error_text,
                created_at=datetime.now()
            )

        # Update service stats only on success
        service_state["generation_count"] += 1
        service_state["total_cost"] += generation_result.cost or 0.0

        response = GammaGenerationResponse(
            generation_id=generation_id,
            status="completed",
            gamma_presentation_id=generation_result.presentation_id,
            preview_url=generation_result.preview_url,
            download_urls=generation_result.download_urls,
            slides_count=generation_result.slides_count,
            generation_time_ms=generation_result.processing_time_ms,
            cost=generation_result.cost,
            created_at=datetime.now()
        )

        safe_cost = generation_result.cost if isinstance(generation_result.cost, (int, float)) else 0.0
        logger.info(f"✅ Presentation generated: {generation_id}, cost: ${safe_cost:.2f}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Presentation generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "generation_failed",
                "message": "Presentation generation encountered an error",
                "generation_id": generation_id,
                "details": str(e)
            }
        )

@app.get("/generation/{generation_id}/status",
         response_model=Dict[str, Any],
         tags=["Generation"])
async def get_generation_status(
    generation_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get status of presentation generation"""
    
    logger.info(f"📊 Checking generation status: {generation_id}")
    
    try:
        # In a production system, this would query generation status from database
        # For now, return a placeholder response
        
        return {
            "generation_id": generation_id,
            "status": "completed",
            "message": "Generation status tracking will be implemented in production",
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "status_check_failed",
                "message": "Generation status check failed",
                "generation_id": generation_id
            }
        )

@app.get("/cost-tracking", response_model=Dict[str, Any], tags=["System"])
async def get_cost_tracking(current_user: str = Depends(get_current_user)):
    """Get cost tracking metrics"""
    
    try:
        uptime_hours = (time.time() - service_state["start_time"]) / 3600
        
        return {
            "service": "gamma-ppt-generator",
            "cost_metrics": {
                "total_generations": service_state["generation_count"],
                "total_cost": f"${service_state['total_cost']:.2f}",
                "average_cost_per_generation": f"${service_state['total_cost'] / max(1, service_state['generation_count']):.2f}",
                "cost_per_hour": f"${service_state['total_cost'] / max(1, uptime_hours):.2f}"
            },
            "gamma_api_limits": {
                "monthly_limit": 50,  # Beta limitation
                "used_this_month": service_state["generation_count"],
                "remaining": max(0, 50 - service_state["generation_count"])
            },
            "tracked_since": service_state["start_time"],
            "last_updated": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Cost tracking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cost tracking data unavailable"
        )

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("SERVICE_PORT", "8003"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"🚀 Starting Gamma PPT Generator Service on {host}:{port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info("🎨 Gamma.app AI-powered presentations ready")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )