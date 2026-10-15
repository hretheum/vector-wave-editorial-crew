"""
Enhanced Publishing Orchestrator API
Multi-platform content publishing with Editorial Service integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union, Tuple
import uuid
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
import os
from enum import Enum
# Support running as script or package
try:
    from .adapters import PLATFORM_ADAPTERS  # type: ignore
    from .variations import generate_variations  # type: ignore
except Exception:
    from adapters import PLATFORM_ADAPTERS  # type: ignore
    from variations import generate_variations  # type: ignore
from linkedin_api import publish_pdf_from_url, is_configured as linkedin_api_configured

# Optional Redis support for queue status
try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Publishing Orchestrator", 
    version="2.0.0",
    description="Enhanced multi-platform publishing orchestration with Editorial Service integration"
)

class PlatformType(str, Enum):
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    BEEHIIV = "beehiiv"
    GHOST = "ghost"
    GENERAL = "general"

class PublicationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"

class PlatformConfig(BaseModel):
    enabled: bool
    account_id: str
    schedule_time: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    direct_content: bool = False  # If True, use provided content directly

class TopicRequest(BaseModel):
    title: str
    description: str
    keywords: Optional[List[str]] = []
    target_audience: Optional[str] = "general"
    content_type: str = "article"

class PublicationRequest(BaseModel):
    topic: TopicRequest
    platforms: Dict[PlatformType, PlatformConfig]
    global_options: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None

class ContentVariation(BaseModel):
    platform: PlatformType
    content: str
    metadata: Dict[str, Any]
    quality_score: Optional[float] = None
    presentation: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None

class PublicationResponse(BaseModel):
    publication_id: str
    request_id: Optional[str]
    status: PublicationStatus
    platform_content: Dict[str, Dict[str, Any]]
    scheduled_jobs: Dict[str, str]
    generation_time: float
    success_count: int
    error_count: int
    errors: List[str] = []

class PublicationStatusResponse(BaseModel):
    publication_id: str
    status: PublicationStatus
    platform_statuses: Dict[str, Dict[str, Any]]
    created_at: str
    completed_at: Optional[str] = None
    total_platforms: int
    successful_platforms: int
    failed_platforms: int

# In-memory storage for demo (in production would use Redis/DB)
publications_store: Dict[str, Dict[str, Any]] = {}
analytics_events: List[Dict[str, Any]] = []
preferences_store: Dict[str, Dict[str, Any]] = {}

# Service URLs (overridable via env for docker/local)
AI_WRITING_FLOW_URL = os.getenv("AI_WRITING_FLOW_URL", "http://localhost:8001")
EDITORIAL_SERVICE_URL = os.getenv("EDITORIAL_SERVICE_URL", "http://localhost:8040")

# Presentation services
# Prefer docker DNS names when running via compose; fall back to localhost when standalone
GAMMA_PPT_URL = os.getenv("GAMMA_PPT_URL", "http://localhost:8003")
PRESENTON_URL = os.getenv("PRESENTON_URL", "http://localhost:8089")
LINKEDIN_PPT_GENERATOR_URL = os.getenv("LINKEDIN_PPT_GENERATOR_URL", "http://localhost:8002")

# Toggle for Gamma usage
GAMMA_ENABLED = os.getenv("GAMMA_ENABLED", "false").lower() == "true"


def _get_redis_queue_stats() -> Optional[Dict[str, Any]]:
    """Return Redis queue stats if REDIS_URL and redis client are available.

    Expects queues and keys compatible with publisher's Redis schema:
    - Lists: publisher:queue:immediate, publisher:queue:processing, publisher:queue:failed, publisher:queue:completed
    - ZSet:  publisher:queue:scheduled
    - Hash:  publisher:stats (total_jobs, jobs_<platform>)
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url or not redis:
        return None

    try:
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
            retry_on_timeout=True,
        )
        client.ping()

        queue_immediate = "publisher:queue:immediate"
        queue_scheduled = "publisher:queue:scheduled"
        queue_processing = "publisher:queue:processing"
        queue_failed = "publisher:queue:failed"
        queue_completed = "publisher:queue:completed"
        key_stats = "publisher:stats"

        immediate_count = client.llen(queue_immediate)
        scheduled_count = client.zcard(queue_scheduled)
        processing_count = client.llen(queue_processing)
        failed_count = client.llen(queue_failed)
        completed_count = client.llen(queue_completed)

        stats = client.hgetall(key_stats) or {}

        return {
            "redis_connected": True,
            "queues": {
                "immediate": int(immediate_count),
                "scheduled": int(scheduled_count),
                "processing": int(processing_count),
                "failed": int(failed_count),
                "completed": int(completed_count),
            },
            "total_jobs": int(stats.get("total_jobs", 0)),
            "jobs_by_platform": {
                "twitter": int(stats.get("jobs_twitter", 0)),
                "linkedin": int(stats.get("jobs_linkedin", 0)),
                "substack": int(stats.get("jobs_substack", 0)),
                "ghost": int(stats.get("jobs_ghost", 0)),
            },
        }
    except Exception:
        return None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "publishing-orchestrator",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """Get publishing orchestrator metrics"""
    total_publications = len(publications_store)
    successful_publications = sum(1 for pub in publications_store.values() 
                                if pub.get("status") == "completed")
    failed_publications = sum(1 for pub in publications_store.values() 
                            if pub.get("status") == "failed")
    
    platform_usage = {}
    for pub in publications_store.values():
        for platform in pub.get("platform_content", {}):
            platform_usage[platform] = platform_usage.get(platform, 0) + 1
    
    # Presentor readiness (best-effort, quick check)
    presentor_ready = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get(f"{LINKEDIN_PPT_GENERATOR_URL}/health")
            presentor_ready = r.status_code == 200
    except Exception:
        presentor_ready = False

    return {
        "total_publications": total_publications,
        "successful_publications": successful_publications,
        "failed_publications": failed_publications,
        "success_rate": successful_publications / total_publications if total_publications > 0 else 0,
        "platform_usage": platform_usage,
        "analytics_events": len(analytics_events),
        "presentor_ready": presentor_ready,
        "service": "publishing-orchestrator"
    }


@app.get("/queue/status")
async def get_queue_status():
    """Queue status for production orchestrator (8085).

    Prefer Redis (when REDIS_URL and redis client available). Fallback to
    in-memory publication stats if Redis is not configured.
    """
    redis_stats = _get_redis_queue_stats()
    if redis_stats and redis_stats.get("redis_connected"):
        return {
            "queue_manager": "Redis",
            "connected": True,
            "queues": redis_stats["queues"],
            "statistics": {
                "total_jobs_processed": redis_stats.get("total_jobs", 0),
                "jobs_by_platform": redis_stats.get("jobs_by_platform", {}),
            },
            "timestamp": datetime.now().isoformat(),
        }

    # Fallback: summarize from in-memory publications_store
    status_counts: Dict[str, int] = {"in_progress": 0, "completed": 0, "failed": 0, "scheduled": 0}
    for pub in publications_store.values():
        st = str(pub.get("status", "")).lower()
        if st in status_counts:
            status_counts[st] += 1
        elif st:
            status_counts["in_progress"] += 1

    return {
        "queue_manager": "InMemory",
        "connected": False,
        "queues": {
            "immediate": 0,
            "scheduled": status_counts["scheduled"],
            "processing": status_counts["in_progress"],
            "failed": status_counts["failed"],
            "completed": status_counts["completed"],
        },
        "statistics": {
            "total_jobs_processed": status_counts["completed"],
            "jobs_by_platform": {},
        },
        "note": "Redis not configured; returning in-memory publication summary",
        "timestamp": datetime.now().isoformat(),
    }

async def call_ai_writing_flow(topic: TopicRequest, platform: str) -> Dict[str, Any]:
    """Call AI Writing Flow service to generate platform-specific content"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_WRITING_FLOW_URL}/generate",
                json={
                    "topic": topic.dict(),
                    "platform": platform,
                    "options": {"enhanced": True}
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"AI Writing Flow call failed for {platform}: {e}")
        return {
            "error": str(e),
            "content": f"Generated content for {topic.title} on {platform}",
            "quality_score": 0.5
        }

async def generate_linkedin_presentation(content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate LinkedIn presentation using best available service (Gamma → Presenton → LinkedIn-PPT)."""
    try:
        if not should_generate_presentation(content):
            return None

        # Decide which service to use
        force_gamma_flag = bool(content.get("force_gamma", False))
        service, reason = await choose_presentation_service(content.get("content", ""), force_gamma=force_gamma_flag)
        logger.info(f"Presentation service selected: {service} ({reason})")

        async with httpx.AsyncClient() as client:
            if service == "gamma":
                try:
                    payload = {
                        "topic": {
                            "title": (content.get("topic") or {}).get("title") or "LinkedIn Presentation",
                            "description": (content.get("topic") or {}).get("description") or "",
                            "keywords": (content.get("topic") or {}).get("keywords") or [],
                            "target_audience": (content.get("topic") or {}).get("target_audience") or "linkedin"
                        },
                        "slides_count": 5,
                        "language": "en",
                        "output_formats": ["pdf", "pptx"],
                        "custom_instructions": "Optimize for LinkedIn document post with concise bullets"
                    }
                    r = await client.post(f"{GAMMA_PPT_URL}/generate/presentation", json=payload, timeout=90.0)
                    r.raise_for_status()
                    data = r.json()
                    return {
                        "ppt_url": (data.get("download_urls") or {}).get("pptx"),
                        "pdf_url": (data.get("download_urls") or {}).get("pdf"),
                        "provider": "gamma",
                        "preview_url": data.get("preview_url"),
                    }
                except Exception as e:
                    logger.warning(f"Gamma generation failed, attempting fallback to Presenton: {e}")
                    # Fallback to Presenton, then LinkedIn-PPT
                    if await check_service_health(PRESENTON_URL):
                        try:
                            prompt = build_presenton_prompt(content)
                            r = await client.post(
                                f"{PRESENTON_URL}/generate",
                                json={
                                    "prompt": prompt,
                                    "slides_count": 5,
                                    "template": "default",
                                    "topic_title": (content.get("topic") or {}).get("title") or "LinkedIn Presentation"
                                },
                                timeout=90.0
                            )
                            r.raise_for_status()
                            data = r.json()
                            return {"ppt_url": data.get("pptx_url"), "pdf_url": data.get("pdf_url"), "provider": "presenton"}
                        except Exception as e2:
                            logger.warning(f"Presenton fallback failed, trying LinkedIn-PPT: {e2}")
                    # Final fallback: LinkedIn-PPT wrapper
                    try:
                        r = await client.post(
                            f"{LINKEDIN_PPT_GENERATOR_URL}/generate-linkedin-ppt",
                            json={
                                "topic_title": (content.get("topic") or {}).get("title") or "LinkedIn Presentation",
                                "topic_description": (content.get("topic") or {}).get("description") or "",
                                "slides_count": 5,
                                "template": "default"
                            },
                            timeout=90.0
                        )
                        r.raise_for_status()
                        data = r.json()
                        return {"ppt_url": data.get("pptx_url"), "pdf_url": data.get("pdf_url"), "provider": "linkedin-ppt"}
                    except Exception as e3:
                        logger.error(f"All fallbacks failed for presentation generation: {e3}")
                        return None

            if service == "presenton":
                try:
                    prompt = build_presenton_prompt(content)
                    r = await client.post(
                        f"{PRESENTON_URL}/generate",
                        json={
                            "prompt": prompt,
                            "slides_count": 5,
                            "template": "default",
                            "topic_title": (content.get("topic") or {}).get("title") or "LinkedIn Presentation"
                        },
                        timeout=90.0
                    )
                    r.raise_for_status()
                    data = r.json()
                    return {"ppt_url": data.get("pptx_url"), "pdf_url": data.get("pdf_url"), "provider": "presenton"}
                except Exception as e:
                    logger.warning(f"Presenton generation failed, attempting fallback to LinkedIn-PPT: {e}")
                    try:
                        r = await client.post(
                            f"{LINKEDIN_PPT_GENERATOR_URL}/generate-linkedin-ppt",
                            json={
                                "topic_title": (content.get("topic") or {}).get("title") or "LinkedIn Presentation",
                                "topic_description": (content.get("topic") or {}).get("description") or "",
                                "slides_count": 5,
                                "template": "default"
                            },
                            timeout=90.0
                        )
                        r.raise_for_status()
                        data = r.json()
                        return {"ppt_url": data.get("pptx_url"), "pdf_url": data.get("pdf_url"), "provider": "linkedin-ppt"}
                    except Exception as e2:
                        logger.error(f"LinkedIn-PPT fallback also failed: {e2}")
                        return None

            # Fallback: legacy LinkedIn PPT wrapper (proxied to Presenton)
            r = await client.post(
                f"{LINKEDIN_PPT_GENERATOR_URL}/generate-linkedin-ppt",
                json={
                    "topic_title": (content.get("topic") or {}).get("title") or "LinkedIn Presentation",
                    "topic_description": (content.get("topic") or {}).get("description") or "",
                    "slides_count": 5,
                    "template": "default"
                },
                timeout=90.0
            )
            r.raise_for_status()
            data = r.json()
            return {"ppt_url": data.get("pptx_url"), "pdf_url": data.get("pdf_url"), "provider": "linkedin-ppt"}
    except Exception as e:
        logger.error(f"LinkedIn presentation generation failed: {e}")
        return None

def build_presenton_prompt(content: Dict[str, Any]) -> str:
    topic = (content.get("topic") or {})
    parts = [
        topic.get("title") or "LinkedIn Presentation",
        topic.get("description") or "",
        "Create concise, business-ready slides for LinkedIn document post."
    ]
    return ". ".join([p for p in parts if p])

def should_generate_presentation(content: Dict[str, Any]) -> bool:
    """Determine if content should have a LinkedIn presentation"""
    if content.get("force_presentation") is True:
        return True
    content_text = content.get("content", "")
    return (
        len(content_text.split()) > 400 and  # Long enough content
        any(keyword in content_text.lower() for keyword in ["architecture", "system", "framework", "process", "strategy"])
    )

async def check_service_health(url: str, path: str = "/health") -> bool:
    """Lightweight health probe with small retry/backoff.

    Uses slightly longer timeout to accommodate cold starts in containers.
    """
    attempts = 3
    backoff = 0.6
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{url}{path}")
                if r.status_code == 200:
                    # Optional: verify status field if JSON
                    try:
                        data = r.json()
                        if isinstance(data, dict) and data.get("status") not in (None, "unhealthy"):
                            return True
                    except Exception:
                        return True
        except Exception:
            pass
        if attempt < attempts - 1:
            try:
                await asyncio.sleep(backoff)
            except Exception:
                pass
            backoff *= 1.5
    return False

async def choose_presentation_service(content_text: str, force_gamma: bool = False) -> Tuple[str, str]:
    """Choose between gamma, presenton, and linkedin-ppt based on health and heuristics.

    When force_gamma is True and Gamma is healthy, prefer Gamma regardless of heuristics.
    """
    # Health checks in priority order
    gamma_ok, presenton_ok, li_ppt_ok = await asyncio.gather(
        check_service_health(GAMMA_PPT_URL),
        check_service_health(PRESENTON_URL),
        check_service_health(LINKEDIN_PPT_GENERATOR_URL)
    )

    # Heuristic: long technical content → gamma preferred
    is_technical = any(k in (content_text or "").lower() for k in ["architecture", "system", "design", "strategy", "framework"])

    if force_gamma and gamma_ok:
        return "gamma", "forced_gamma_preference"

    if gamma_ok and is_technical:
        return "gamma", "gamma available and content appears technical"
    if presenton_ok:
        return "presenton", "presenton available (fast local)"
    if gamma_ok:
        return "gamma", "presenton unavailable; gamma available"
    if li_ppt_ok:
        return "linkedin-ppt", "both gamma/presenton unavailable; linkedin-ppt wrapper available"
    return "none", "no presentation services available"

async def validate_with_editorial_service(content: str, platform: str) -> Dict[str, Any]:
    """Validate content with Editorial Service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{EDITORIAL_SERVICE_URL}/validate/comprehensive",
                json={
                    "content": content,
                    "platform": platform,
                    "content_type": "article",
                    "context": {
                        "agent": "orchestrator",
                        "validation_type": "comprehensive"
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Editorial Service validation failed: {e}")
        return {
            "error": str(e),
            "is_compliant": True,  # Allow publishing despite validation failure
            "violations": [],
            "suggestions": []
        }

async def schedule_platform_publication(platform: str, content: Dict[str, Any], 
                                     config: PlatformConfig) -> str:
    """Schedule publication to specific platform"""
    job_id = f"{platform}_{uuid.uuid4()}"
    
    # In production, would integrate with Celery/Redis for scheduling
    logger.info(f"Scheduled publication {job_id} for {platform}")
    
    return job_id

async def generate_platform_content(topic: TopicRequest, platform: str, 
                                  config: PlatformConfig) -> Dict[str, Any]:
    """Generate platform-specific content using AI Writing Flow"""
    start_time = datetime.now()
    
    if config.direct_content:
        # Use provided content directly
        content = {
            "content": f"Direct content for {topic.title} on {platform}",
            "platform": platform,
            "quality_score": 1.0,
            "metadata": {"generation_method": "direct"}
        }
    else:
        # Generate content using AI Writing Flow
        content = await call_ai_writing_flow(topic, platform)
    
    # Generate variations per platform
    variations = generate_variations(content.get("content", ""), num=3)
    valid_variations: List[Dict[str, Any]] = []
    # Validate each variation with Editorial Service (best-effort)
    for v in variations:
        vr = await validate_with_editorial_service(v.get("content", ""), platform)
        v["validation_results"] = vr
        # Exclude failed validations if returned
        if vr.get("error"):
            continue
        valid_variations.append(v)

    # Choose first valid or fallback to base
    chosen = valid_variations[0] if valid_variations else {"content": content.get("content", ""), "validation_results": {"is_compliant": True}}
    content.update(chosen)

    # Apply platform adapter formatting
    adapter = PLATFORM_ADAPTERS.get(platform, lambda c, t: {"content": c})
    formatted = adapter(content.get("content", ""), topic.dict())
    content.update(formatted)

    # For LinkedIn, include manual upload package info (placeholder)
    if platform == PlatformType.LINKEDIN.value:
        content["linkedin_manual_upload"] = {
            "checklist": [
                "Review content and validation suggestions",
                "Upload presentation (if available) as document",
                "Paste content, add hashtags, and schedule",
            ],
            "assets": {}
        }
    
    generation_time = (datetime.now() - start_time).total_seconds()
    content["generation_time"] = generation_time
    
    return content

@app.post("/publish", response_model=PublicationResponse)
async def orchestrate_publication(request: PublicationRequest, 
                                background_tasks: BackgroundTasks):
    """Complete multi-platform publishing orchestration"""
    start_time = datetime.now()
    publication_id = f"pub_{uuid.uuid4()}"
    
    # Store initial publication record
    publications_store[publication_id] = {
        "publication_id": publication_id,
        "request_id": request.request_id,
        "status": "in_progress",
        "created_at": start_time.isoformat(),
        "topic": request.topic.dict(),
        "platforms": [p.value for p in request.platforms.keys()],
        "platform_content": {},
        "scheduled_jobs": {},
        "errors": []
    }
    
    logger.info(f"Starting publication {publication_id} for topic: {request.topic.title}")
    
    # Generate content for each platform
    content_variations = {}
    scheduled_jobs = {}
    errors = []
    success_count = 0
    
    for platform, config in request.platforms.items():
        if not config.enabled:
            continue
            
        try:
            logger.info(f"Generating content for {platform}")
            
            # Platform-specific content generation
            content = await generate_platform_content(
                request.topic, platform.value, config
            )
            
            # If AI Writing Flow failed but provided fallback content, continue
            if "error" in content and not content.get("content"):
                errors.append(f"{platform}: {content['error']}")
                continue
                
            content_variations[platform.value] = content
            success_count += 1
            
            # Special LinkedIn handling (presentation generation via Gamma/Presenton)
            # Try to generate presentation for LinkedIn; generator may decide
            if platform == PlatformType.LINKEDIN:
                # Pass optional global flags to influence selection/forcing
                force_presentation_flag = False
                force_gamma_flag = False
                try:
                    if request.global_options:
                        force_presentation_flag = bool(request.global_options.get("force_presentation", False))
                        force_gamma_flag = bool(request.global_options.get("force_gamma", False))
                except Exception:
                    force_presentation_flag = False
                    force_gamma_flag = False

                content_with_flags = {
                    **content,
                    "topic": request.topic.dict() if hasattr(request, "topic") else {},
                }
                if force_presentation_flag:
                    content_with_flags["force_presentation"] = True
                if force_gamma_flag:
                    content_with_flags["force_gamma"] = True

                # Generate presentation using selected policy/flags
                presentation = await generate_linkedin_presentation(content_with_flags)
                if presentation:
                    content_variations[platform.value]["presentation"] = presentation
                    # Attach asset references for manual upload
                    assets = content_variations[platform.value].setdefault("linkedin_manual_upload", {}).setdefault("assets", {})
                    for key in ("ppt_url", "pdf_url", "preview_url"):
                        if presentation.get(key):
                            assets[key] = presentation[key]
                    # Optional: if LinkedIn API configured, publish automatically as document post
                    try:
                        if await linkedin_api_configured() and presentation.get("pdf_url"):
                            post = await publish_pdf_from_url(
                                presentation["pdf_url"],
                                text=content.get("content", ""),
                                title=request.topic.title,
                                description=request.topic.description
                            )
                            if post:
                                content_variations[platform.value].setdefault("linkedin_manual_upload", {})["auto_publish"] = post
                    except Exception as e:
                        logger.warning(f"LinkedIn API auto-publish failed: {e}")
            
            # Schedule publication
            job_id = await schedule_platform_publication(
                platform.value, content, config
            )
            scheduled_jobs[platform.value] = job_id
            
        except Exception as e:
            error_msg = f"{platform}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Publication failed for {platform}: {e}")
    
    generation_time = (datetime.now() - start_time).total_seconds()
    
    # Update publication record
    final_status = "completed" if success_count > 0 else "failed"
    publications_store[publication_id].update({
        "status": final_status,
        "completed_at": datetime.now().isoformat(),
        "platform_content": content_variations,
        "scheduled_jobs": scheduled_jobs,
        "generation_time": generation_time,
        "success_count": success_count,
        "error_count": len(errors),
        "errors": errors
    })
    
    logger.info(f"Publication {publication_id} completed. Success: {success_count}, Errors: {len(errors)}")
    
    # Enrich LinkedIn content with manual upload URLs if presentation was generated
    enriched_platform_content: Dict[str, Dict[str, Any]] = {}
    for plat, data in content_variations.items():
        enriched = {
            "content": data.get("content", ""),
            "quality_score": data.get("quality_score", 0),
            "validation_results": data.get("validation_results", {}),
            "generation_time": data.get("generation_time", 0)
        }
        if data.get("presentation"):
            enriched["manual_upload"] = {
                "ppt_url": data["presentation"].get("ppt_url"),
                "pdf_url": data["presentation"].get("pdf_url"),
                "provider": data["presentation"].get("provider")
            }
        enriched_platform_content[plat] = enriched

    return PublicationResponse(
        publication_id=publication_id,
        request_id=request.request_id,
        status=PublicationStatus(final_status),
        platform_content=enriched_platform_content,
        scheduled_jobs=scheduled_jobs,
        generation_time=generation_time,
        success_count=success_count,
        error_count=len(errors),
        errors=errors
    )


# --- Presentation services discovery and recommendations ---

@app.get("/presentation-options")
async def presentation_options():
    gamma_ok, presenton_ok, li_ppt_ok = await asyncio.gather(
        check_service_health(GAMMA_PPT_URL),
        check_service_health(PRESENTON_URL),
        check_service_health(LINKEDIN_PPT_GENERATOR_URL)
    )
    return {
        "services": {
            "gamma": {"url": GAMMA_PPT_URL, "healthy": gamma_ok},
            "presenton": {"url": PRESENTON_URL, "healthy": presenton_ok},
            "linkedin_ppt": {"url": LINKEDIN_PPT_GENERATOR_URL, "healthy": li_ppt_ok},
        }
    }


class RecommendationRequest(BaseModel):
    content_sample: str = Field("", description="Sample content to analyze")
    prefer_cost_savings: bool = Field(False, description="Prefer cheaper local generation")


@app.post("/presentation-services/recommend")
async def recommend_presentation_service(payload: RecommendationRequest = Body(...)):
    # If user prefers cost savings, bias toward Presenton when healthy
    if payload.prefer_cost_savings:
        presenton_ok = await check_service_health(PRESENTON_URL)
        if presenton_ok:
            return {"recommended": "presenton", "reason": "cost_savings_preference", "url": PRESENTON_URL}

    service, reason = await choose_presentation_service(payload.content_sample)
    url = {
        "gamma": GAMMA_PPT_URL,
        "presenton": PRESENTON_URL,
        "linkedin-ppt": LINKEDIN_PPT_GENERATOR_URL,
        "none": None,
    }.get(service)
    return {"recommended": service, "reason": reason, "url": url}


class GammaTestPayload(BaseModel):
    title: str = Field("Architecture Strategy Overview")
    description: str = Field("System architecture and strategy for multi-service publishing")
    keywords: List[str] = Field(default_factory=lambda: ["architecture", "system", "strategy"])
    target_audience: str = Field("developers")
    force_presentation: bool = Field(True)
    force_gamma: bool = Field(True)
    direct_content: bool = Field(False)


@app.post("/test/publish-gamma")
async def test_publish_gamma(payload: GammaTestPayload = Body(default=None)):
    """Test endpoint to trigger LinkedIn flow with Gamma presentation generation.

    - Uses technical keywords to satisfy heuristics
    - Allows forcing presentation and Gamma via flags
    - Returns publication response (provider and URLs included if generation succeeds)
    """
    p = payload or GammaTestPayload()
    req = PublicationRequest(
        topic=TopicRequest(
            title=p.title,
            description=p.description,
            keywords=p.keywords,
            target_audience=p.target_audience,
        ),
        platforms={
            PlatformType.LINKEDIN: PlatformConfig(
                enabled=True,
                account_id="test",
                direct_content=p.direct_content,
            )
        },
        global_options={
            "force_presentation": p.force_presentation,
            "force_gamma": p.force_gamma,
        },
    )
    return await orchestrate_publication(req, BackgroundTasks())


class AnalyticsEvent(BaseModel):
    request_id: Optional[str] = None
    publication_id: Optional[str] = None
    platform: Optional[str] = None
    status: Optional[str] = None  # scheduled|completed|failed
    validation_score: Optional[Union[int, float]] = None
    scheduled_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


@app.post("/analytics/track")
async def analytics_track(event: AnalyticsEvent):
    payload = event.model_dump()
    payload["ts"] = datetime.now().isoformat()
    analytics_events.append(payload)
    return {"status": "tracked", "events": len(analytics_events)}


@app.get("/analytics/events")
async def analytics_list(limit: int = 50):
    return {"events": analytics_events[-limit:], "total": len(analytics_events)}


class PreferenceUpdate(BaseModel):
    platform: str
    hour: Optional[str] = None  # e.g., "11:00"
    score: Optional[float] = 0.5


@app.put("/preferences/{user_id}")
async def preferences_put(user_id: str, pref: PreferenceUpdate):
    user = preferences_store.setdefault(user_id, {"platforms": {}, "hours": {}})
    if pref.platform:
        user["platforms"][pref.platform] = max(0.0, min(1.0, float(pref.score or 0.0)))
    if pref.hour:
        user["hours"][pref.hour] = max(0.0, min(1.0, float(pref.score or 0.0)))
    return {"status": "ok", "preferences": user}


@app.get("/preferences/{user_id}")
async def preferences_get(user_id: str):
    return preferences_store.get(user_id, {"platforms": {}, "hours": {}})

@app.get("/publication/{publication_id}", response_model=PublicationStatusResponse)
async def get_publication_status(publication_id: str):
    """Get status of specific publication"""
    if publication_id not in publications_store:
        raise HTTPException(status_code=404, detail="Publication not found")
    
    pub = publications_store[publication_id]
    
    platform_statuses = {}
    for platform in pub.get("platforms", []):
        content = pub["platform_content"].get(platform, {})
        platform_statuses[platform] = {
            "status": "completed" if content else "failed",
            "quality_score": content.get("quality_score", 0),
            "generation_time": content.get("generation_time", 0),
            "validation_compliant": content.get("validation_results", {}).get("is_compliant", True)
        }
    
    return PublicationStatusResponse(
        publication_id=publication_id,
        status=PublicationStatus(pub["status"]),
        platform_statuses=platform_statuses,
        created_at=pub["created_at"],
        completed_at=pub.get("completed_at"),
        total_platforms=len(pub.get("platforms", [])),
        successful_platforms=pub["success_count"],
        failed_platforms=pub["error_count"]
    )

@app.get("/publications")
async def list_publications(limit: int = 20, status: Optional[str] = None):
    """List recent publications"""
    publications = list(publications_store.values())
    
    if status:
        publications = [p for p in publications if p.get("status") == status]
    
    # Sort by created_at descending
    publications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "publications": publications[:limit],
        "total": len(publications_store),
        "filtered": len(publications)
    }

@app.post("/test/simple")
async def test_simple_publication():
    """Simple test endpoint for basic functionality validation"""
    test_request = PublicationRequest(
        topic=TopicRequest(
            title="Test Publication",
            description="Testing Enhanced Orchestrator API",
            keywords=["test", "api", "orchestrator"]
        ),
        platforms={
            PlatformType.LINKEDIN: PlatformConfig(
                enabled=True,
                account_id="test_account",
                direct_content=True
            )
        }
    )
    
    return await orchestrate_publication(test_request, BackgroundTasks())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)