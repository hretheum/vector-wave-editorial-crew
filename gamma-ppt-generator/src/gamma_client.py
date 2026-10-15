"""
Gamma.app API Client
Handles communication with Gamma.app Generate API
"""

import os
import logging
import aiohttp
import asyncio
import time
from typing import Dict, Any, Optional, Iterable, Tuple
from datetime import datetime
import json

from models import GammaAPIResponse, GammaConnectionTest, ServiceStatus

logger = logging.getLogger(__name__)


class GammaAPIClient:
    """
    Gamma.app API client with rate limiting and error handling
    
    API Documentation: https://developers.gamma.app/docs/how-does-the-generations-api-work
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        demo_mode: bool = False,
        max_retries: int = 3,
        initial_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 8.0,
        retry_statuses: Optional[Iterable[int]] = None,
    ):
        self.api_key = api_key
        self.demo_mode = demo_mode
        # Allow override via env; default to public-api v0.2 per docs
        self.base_url = os.getenv("GAMMA_BASE_URL", "https://public-api.gamma.app/v0.2")
        self.max_retries = max(0, max_retries)
        self.initial_backoff_seconds = max(0.1, initial_backoff_seconds)
        self.max_backoff_seconds = max(self.initial_backoff_seconds, max_backoff_seconds)
        self.retry_statuses = set(retry_statuses or {429, 500, 502, 503, 504})
        
        # Rate limiting (50 generations per month in Beta)
        self.monthly_limit = 50
        self.current_usage = 0
        self.rate_limit_reset = None
        
        # Request tracking
        self.request_count = 0
        self.total_cost = 0.0
        
        # Session for connection pooling
        self.session = None
        
        logger.info(f"🎨 Gamma API Client initialized (demo_mode: {demo_mode})")

    def _should_retry_status(self, status_code: int) -> bool:
        return status_code in self.retry_statuses

    async def _post_json_with_retries(
        self,
        session: aiohttp.ClientSession,
        url: str,
        payload: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any]]:
        """POST JSON with retries and exponential backoff.
        Returns (status_code, response_data_dict)
        """
        attempt = 0
        backoff = self.initial_backoff_seconds
        last_status = 0
        last_data: Dict[str, Any] = {}
        while True:
            try:
                async with session.post(url, json=payload) as response:
                    last_status = response.status
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            last_data = await response.json()
                        except Exception:
                            last_data = {}
                    else:
                        try:
                            text = await response.text()
                            last_data = {"raw": text}
                        except Exception:
                            last_data = {}

                    # Do not retry on 401/403/404
                    if last_status in {401, 403, 404}:
                        return last_status, last_data

                    if last_status < 500 and last_status not in self.retry_statuses:
                        # For 2xx-4xx (excluding configured retry statuses), stop retrying
                        return last_status, last_data

                    # Retry if status indicates transient error
                    if attempt >= self.max_retries:
                        return last_status, last_data

                    logger.warning(
                        f"Gamma API POST {url} failed with HTTP {last_status}; retrying in {backoff:.1f}s (attempt {attempt+1}/{self.max_retries})"
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt >= self.max_retries:
                    return last_status or 0, {"error": "request_exception", "message": str(exc)}
                logger.warning(
                    f"Gamma API POST exception: {exc}; retrying in {backoff:.1f}s (attempt {attempt+1}/{self.max_retries})"
                )

            # Backoff (with tiny jitter)
            try:
                await asyncio.sleep(backoff)
            except Exception:
                pass
            attempt += 1
            backoff = min(self.max_backoff_seconds, backoff * 2)
        
        # Should not reach here
        return last_status, last_data
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Vector-Wave-Gamma-Client/1.0"
            }
            
            if self.api_key and not self.demo_mode:
                # Gamma v0.2 expects X-API-KEY
                headers["X-API-KEY"] = self.api_key
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout
            )
        
        return self.session
    
    async def test_connection(self) -> GammaConnectionTest:
        """Test connection to Gamma.app API"""
        start_time = time.time()
        
        if self.demo_mode:
            # Demo mode - simulate successful connection
            await asyncio.sleep(0.5)  # Simulate network delay
            
            return GammaConnectionTest(
                connected=True,
                response_time_ms=(time.time() - start_time) * 1000,
                api_version="v1.0-demo",
                limits={
                    "total": self.monthly_limit,
                    "used": self.current_usage,
                    "remaining": self.monthly_limit - self.current_usage
                }
            )
        
        try:
            session = await self._get_session()
            url = f"{self.base_url}/generations"
            # Prefer OPTIONS probe (cheap reachability/auth signal)
            try:
                async with session.options(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    if response.status in {200, 201, 202, 204, 405}:
                        return GammaConnectionTest(
                            connected=True,
                            response_time_ms=response_time,
                            api_version="v0.2",
                            limits={}
                        )
                    if response.status in {401, 403}:
                        return GammaConnectionTest(
                            connected=False,
                            response_time_ms=response_time,
                            api_version="v0.2",
                            limits={},
                            error=f"auth_error:{response.status}"
                        )
            except Exception:
                pass
            # Fallback GET (may 404/405)
            async with session.get(url) as response:
                response_time = (time.time() - start_time) * 1000
                if response.status in {200, 201, 202, 204}:
                    return GammaConnectionTest(
                        connected=True,
                        response_time_ms=response_time,
                        api_version="v0.2",
                        limits={}
                    )
                try:
                    text = await response.text()
                except Exception:
                    text = None
                return GammaConnectionTest(
                    connected=False,
                    response_time_ms=response_time,
                    api_version="v0.2",
                    limits={},
                    error=f"HTTP {response.status}: {text}"
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Gamma API connection test failed: {e}")
            
            return GammaConnectionTest(
                connected=False,
                response_time_ms=response_time,
                api_version="unknown",
                limits={},
                error=str(e)
            )
    
    async def get_status(self) -> ServiceStatus:
        """Get current API status (v0.2 lacks status; use connectivity probe)."""
        if self.demo_mode:
            return ServiceStatus(
                status="demo_mode",
                remaining_calls=self.monthly_limit - self.current_usage,
                monthly_usage=self.current_usage,
                rate_limit_reset=datetime(2025, 2, 1)
            )
        try:
            probe = await self.test_connection()
            if probe.connected:
                return ServiceStatus(
                    status="operational",
                    remaining_calls=self.monthly_limit - self.current_usage,
                    monthly_usage=self.current_usage
                )
            status_text = "auth_error" if (probe.error and "auth_error" in probe.error) else "api_error"
            return ServiceStatus(
                status=status_text,
                remaining_calls=0,
                monthly_usage=self.current_usage
            )
        except Exception as e:
            logger.error(f"Failed to get Gamma API status: {e}")
            return ServiceStatus(
                status="connection_error",
                remaining_calls=0,
                monthly_usage=self.current_usage
            )
    
    async def generate_presentation(self, request_data: Dict[str, Any]) -> GammaAPIResponse:
        """Generate presentation using Gamma.app API"""
        
        start_time = time.time()
        
        # Check rate limits
        if self.current_usage >= self.monthly_limit:
            return GammaAPIResponse(
                success=False,
                error_code="RATE_LIMIT_EXCEEDED",
                error_message=f"Monthly limit of {self.monthly_limit} generations exceeded"
            )
        
        if self.demo_mode:
            # Demo mode - simulate presentation generation
            await asyncio.sleep(2.0)  # Simulate processing time
            
            processing_time = (time.time() - start_time) * 1000
            
            # Simulate successful generation
            self.current_usage += 1
            self.request_count += 1
            
            demo_cost = 0.50  # Demo cost per generation
            self.total_cost += demo_cost
            
            presentation_id = f"gamma_demo_{int(time.time())}"
            
            return GammaAPIResponse(
                success=True,
                presentation_id=presentation_id,
                preview_url=f"https://gamma.app/docs/{presentation_id}",
                download_urls={
                    "pdf": f"https://gamma.app/download/{presentation_id}.pdf",
                    "pptx": f"https://gamma.app/download/{presentation_id}.pptx"
                },
                slides_count=request_data.get("slides_count", 8),
                processing_time_ms=processing_time,
                cost=demo_cost
            )
        
        try:
            session = await self._get_session()
            
            # Prepare request data for Gamma API
            gamma_request = self._prepare_gamma_request(request_data)
            
            logger.info(f"🎨 Sending generation request to Gamma.app: {request_data['topic']['title']}")
            
            # Use documented endpoint first; keep a couple of fallbacks
            candidate_paths = [
                "/generations",             # per docs v0.2
                "/presentations/generate",  # fallback guess
                "/generate"                  # fallback guess
            ]
            last_error_resp: Dict[str, Any] = {}
            last_status: Optional[int] = None
            last_data: Optional[Dict[str, Any]] = None
            for path in candidate_paths:
                url = f"{self.base_url}{path}"
                status_code, data = await self._post_json_with_retries(session, url, gamma_request)
                processing_time = (time.time() - start_time) * 1000
                last_status = status_code
                last_data = data
                if status_code == 200 and isinstance(data, dict):
                        # Map likely Gamma fields to our model
                        presentation_id = (
                            data.get("id")
                            or data.get("presentation_id")
                            or data.get("data", {}).get("id")
                        )
                        preview_url = (
                            data.get("url")
                            or data.get("preview_url")
                            or data.get("links", {}).get("preview")
                        )
                        download_urls = (
                            data.get("downloadUrls")
                            or data.get("download_urls")
                            or data.get("links", {}).get("downloads")
                        )
                        slides_count = data.get("slides_count") or data.get("meta", {}).get("slides")

                        # Update usage tracking
                        self.current_usage += 1
                        self.request_count += 1
                        
                        # Calculate cost (estimated)
                        estimated_cost = 0.50  # Placeholder cost per generation
                        self.total_cost += estimated_cost
                        
                        return GammaAPIResponse(
                            success=bool(preview_url or download_urls or presentation_id),
                            presentation_id=presentation_id,
                            preview_url=preview_url,
                            download_urls=download_urls,
                            slides_count=slides_count,
                            processing_time_ms=processing_time,
                            cost=estimated_cost,
                            error_message=None if (preview_url or download_urls or presentation_id) else "Gamma API returned incomplete payload"
                        )
                else:
                    # Try next candidate; remember last details
                    last_error_resp = data or {}
                    continue

            # If all endpoints failed
            processing_time = (time.time() - start_time) * 1000
            error_code = None
            error_message = None
            if isinstance(last_error_resp, dict):
                error_code = last_error_resp.get("error") or last_error_resp.get("code") or last_error_resp.get("status")
                error_message = last_error_resp.get("message") or last_error_resp.get("error_description") or last_error_resp.get("raw")
            path_list = ",".join(candidate_paths)
            return GammaAPIResponse(
                success=False,
                processing_time_ms=processing_time,
                error_code=error_code or "API_NOT_FOUND",
                error_message=error_message or f"No successful endpoint among: {path_list} (last HTTP {last_status})"
            )
        
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Gamma API generation failed: {e}")
            
            return GammaAPIResponse(
                success=False,
                processing_time_ms=processing_time,
                error_code="REQUEST_FAILED",
                error_message=str(e)
            )
    
    def _prepare_gamma_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request data for Gamma Generate API v0.2 format.
        https://developers.gamma.app/docs/how-does-the-generations-api-work
        """
        topic = request_data.get("topic", {})
        title = topic.get("title") or ""
        description = topic.get("description") or ""
        keywords = topic.get("keywords") or []
        audience = topic.get("target_audience") or None

        # Build inputText from topic fields
        parts = []
        if title:
            parts.append(title)
        if description:
            parts.append(description)
        if keywords:
            parts.append("Keywords: " + ", ".join(keywords))
        if audience:
            parts.append("Audience: " + str(audience))
        input_text = ". ".join([p for p in parts if p])

        # exportAs: choose preferred output
        export_as = None
        outputs = request_data.get("output_formats") or []
        if isinstance(outputs, list) and outputs:
            # Prefer pdf, else pptx
            export_as = "pdf" if "pdf" in outputs else ("pptx" if "pptx" in outputs else None)

        payload: Dict[str, Any] = {
            "inputText": input_text or title,
            "textMode": "generate",
            "format": "presentation",
            "themeName": request_data.get("theme") or "business",
            "numCards": request_data.get("slides_count") or 8,
            "cardSplit": "auto",
            "additionalInstructions": request_data.get("custom_instructions") or "",
            "textOptions": {
                "amount": "detailed",
                "tone": None,
                "audience": audience or None,
                "language": request_data.get("language") or "en",
            },
            "imageOptions": {
                "source": "aiGenerated"
            },
            "cardOptions": {},
            "sharingOptions": {}
        }
        # Remove None fields in nested dicts
        for section in ("textOptions",):
            payload[section] = {k: v for k, v in payload[section].items() if v is not None}
        if export_as:
            payload["exportAs"] = export_as

        return payload
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("🔌 Gamma API client session closed")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_requests": self.request_count,
            "current_monthly_usage": self.current_usage,
            "monthly_limit": self.monthly_limit,
            "remaining_calls": self.monthly_limit - self.current_usage,
            "total_cost": self.total_cost,
            "average_cost_per_request": self.total_cost / max(1, self.request_count)
        }