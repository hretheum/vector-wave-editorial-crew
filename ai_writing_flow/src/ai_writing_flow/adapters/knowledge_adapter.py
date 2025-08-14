"""
Knowledge Adapter - Hybrid Adapter Pattern for CrewAI Knowledge Base Integration

Implements Clean Architecture with:
- Circuit Breaker Pattern for reliability
- Multiple search strategies (KB_FIRST, FILE_FIRST, HYBRID, KB_ONLY)
- Comprehensive error handling
- Statistics tracking
- Async/await support
"""

import asyncio
try:
    import aiohttp  # type: ignore
except Exception:  # pragma: no cover - CI-light shim fallback
    aiohttp = None
import json
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

try:
    import structlog  # type: ignore
except Exception:  # pragma: no cover - CI-light shim fallback
    class _DummyLogger:
        def __getattr__(self, _):
            return lambda *args, **kwargs: None
    class _DummyStructlog:
        def get_logger(self, *args, **kwargs):
            return _DummyLogger()
    structlog = _DummyStructlog()

# Configure structured logging
logger = structlog.get_logger(__name__)


class SearchStrategy(Enum):
    """Search strategy options for the Knowledge Adapter"""
    KB_FIRST = "KB_FIRST"          # Try KB first, fallback to files
    FILE_FIRST = "FILE_FIRST"      # Try files first, then KB
    HYBRID = "HYBRID"              # Combine results from both sources
    KB_ONLY = "KB_ONLY"            # Use only Knowledge Base (no fallback)


class AdapterError(Exception):
    """Base exception for Knowledge Adapter errors"""
    pass


class CircuitBreakerOpen(AdapterError):
    """Exception raised when circuit breaker is open"""
    pass


@dataclass
class CircuitBreakerState:
    """Circuit breaker state management"""
    _is_open: bool = False
    _failure_count: int = 0
    _last_failure: Optional[datetime] = None
    _threshold: int = 5
    _timeout_seconds: int = 60
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self._is_open:
            return False
            
        # Check if timeout period has passed
        if (self._last_failure and 
            datetime.now() - self._last_failure > timedelta(seconds=self._timeout_seconds)):
            self.reset()
            return False
            
        return True
    
    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self._failure_count += 1
        self._last_failure = datetime.now()
        
        if self._failure_count >= self._threshold:
            self._is_open = True
            logger.warning("Circuit breaker opened", 
                         failure_count=self._failure_count,
                         threshold=self._threshold)
    
    def record_success(self):
        """Record a success and reset failure count"""
        self._failure_count = 0
        if self._is_open:
            logger.info("Circuit breaker closed after successful request")
        self._is_open = False
    
    def reset(self):
        """Reset circuit breaker state"""
        self._is_open = False
        self._failure_count = 0
        self._last_failure = None


@dataclass
class AdapterStatistics:
    """Statistics tracking for the Knowledge Adapter"""
    total_queries: int = 0
    kb_successes: int = 0
    kb_errors: int = 0
    file_searches: int = 0
    strategy_usage: Dict[SearchStrategy, int] = field(default_factory=dict)
    total_response_time_ms: float = 0.0
    
    @property
    def kb_availability(self) -> float:
        """Calculate KB availability percentage"""
        total_kb_attempts = self.kb_successes + self.kb_errors
        if total_kb_attempts == 0:
            return 1.0
        return self.kb_successes / total_kb_attempts
    
    @property
    def average_response_time_ms(self) -> float:
        """Calculate average response time"""
        if self.total_queries == 0:
            return 0.0
        return self.total_response_time_ms / self.total_queries


@dataclass
class KnowledgeResponse:
    """Response from knowledge search operations"""
    query: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    file_content: str = ""
    strategy_used: SearchStrategy = SearchStrategy.HYBRID
    kb_available: bool = True
    response_time_ms: float = 0.0
    context_used: bool = False
    
    def __str__(self) -> str:
        """String representation for compatibility"""
        return self.file_content if self.file_content else str(self.results)


class KnowledgeAdapter:
    """
    Hybrid Knowledge Adapter implementing multiple search strategies
    with circuit breaker pattern and comprehensive error handling.
    """
    
    def __init__(self,
                 strategy: Union[SearchStrategy, str] = SearchStrategy.HYBRID,
                 kb_api_url: str = "http://localhost:8080",
                 timeout: float = 10.0,
                 max_retries: int = 3,
                 circuit_breaker_threshold: int = 5,
                 docs_path: Optional[str] = None):
        """
        Initialize Knowledge Adapter
        
        Args:
            strategy: Search strategy to use
            kb_api_url: Knowledge Base API URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            circuit_breaker_threshold: Failures before opening circuit breaker
            docs_path: Path to local documentation files
        """
        # Convert string strategy to enum if needed
        if isinstance(strategy, str):
            try:
                self.strategy = SearchStrategy(strategy)
            except ValueError:
                raise ValueError(f"Invalid search strategy: {strategy}. "
                               f"Valid options: {[s.value for s in SearchStrategy]}")
        else:
            self.strategy = strategy
            
        self.kb_api_url = kb_api_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Circuit breaker setup
        self.circuit_breaker = CircuitBreakerState()
        self.circuit_breaker._threshold = circuit_breaker_threshold
        
        # Statistics tracking
        self.stats = AdapterStatistics()
        
        # Documentation path
        self.docs_path = Path(docs_path) if docs_path else Path(
            "/Users/hretheum/dev/bezrobocie/vector-wave/knowledge-base/knowledge-base/data/crewai-docs/docs/en"
        )
        
        # CI-Light mode to avoid external dependencies in tests
        # When enabled, adapter returns deterministic responses without network/filesystem
        self.ci_light: bool = os.getenv('CI_LIGHT', '0') in ('1', 'true', 'TRUE')
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info("Knowledge Adapter initialized",
                   strategy=self.strategy.value,
                   kb_api_url=self.kb_api_url,
                   docs_path=str(self.docs_path),
                   ci_light=self.ci_light)
    
    async def _get_session(self):
        """Get or create HTTP session with connection pooling"""
        if self._session is None or getattr(self._session, 'closed', False):
            if aiohttp is None:
                # In CI-light mode, we don't need a real session
                if self.ci_light:
                    self._session = object()  # placeholder
                    return self._session
                raise AdapterError("aiohttp is not available in this environment")
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'Content-Type': 'application/json'}
            )
        return self._session
    
    async def close(self):
        """Close HTTP session and cleanup resources"""
        if self._session and not getattr(self._session, 'closed', True):
            try:
                await self._session.close()
            except Exception:
                pass
    
    async def search_knowledge_base(self, 
                                  query: str, 
                                  limit: int = 5,
                                  score_threshold: float = 0.7) -> KnowledgeResponse:
        """
        Search the Knowledge Base API with retry logic and circuit breaker
        
        Args:
            query: Search query
            limit: Maximum number of results
            score_threshold: Minimum score threshold for results
            
        Returns:
            KnowledgeResponse with results
            
        Raises:
            CircuitBreakerOpen: When circuit breaker is open
            AdapterError: For other KB-related errors
        """
        # CI-Light deterministic response (no network)
        if self.ci_light or aiohttp is None:
            # Allow forcing unavailability via env for specific tests
            kb_enabled = os.getenv('CI_LIGHT_KB_AVAILABLE', '1') in ('1', 'true', 'TRUE')
            if not kb_enabled:
                raise CircuitBreakerOpen("CI-Light: KB forced unavailable")

            # Build deterministic KB results
            items: List[Dict[str, Any]] = []
            for i in range(max(1, min(limit, 5))):
                score = max(0.0, 0.95 - i * 0.07)
                if score < score_threshold:
                    break
                items.append({
                    "content": f"KB result {i+1} for '{query}'",
                    "score": score,
                    "metadata": {"source": "kb", "title": f"KB Doc {i+1}"}
                })

            return KnowledgeResponse(
                query=query,
                results=items,
                strategy_used=SearchStrategy.KB_FIRST,
                kb_available=True,
                response_time_ms=150.0,
                context_used=False,
            )

        # Check circuit breaker
        if self.circuit_breaker.is_open():
            logger.warning("Circuit breaker is open, blocking KB request")
            raise CircuitBreakerOpen("Knowledge Base circuit breaker is open")
        
        payload = {
            "query": query,
            "limit": limit,
            "score_threshold": score_threshold,
            "sources": ["cache", "vector", "markdown"],
            "use_cache": True
        }
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                session = await self._get_session()
                
                async with session.post(
                    f"{self.kb_api_url}/api/v1/knowledge/query",
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Validate response format
                        if "results" not in data:
                            raise AdapterError("Invalid response format from Knowledge Base")
                        
                        self.circuit_breaker.record_success()
                        self.stats.kb_successes += 1
                        
                        return KnowledgeResponse(
                            query=query,
                            results=data["results"],
                            strategy_used=SearchStrategy.KB_FIRST,
                            kb_available=True
                        )
                    else:
                        error_msg = f"KB API returned status {response.status}"
                        logger.warning("KB API error", status=response.status)
                        raise AdapterError(error_msg)
                        
            except asyncio.TimeoutError:
                last_error = AdapterError("Knowledge Base request timed out")
                logger.warning("KB request timeout", attempt=attempt + 1)
                
            except aiohttp.ClientError as e:
                last_error = AdapterError(f"Knowledge Base connection error: {str(e)}")
                logger.warning("KB connection error", error=str(e), attempt=attempt + 1)
                
            except Exception as e:
                last_error = AdapterError(f"Unexpected KB error: {str(e)}")
                logger.error("Unexpected KB error", error=str(e), attempt=attempt + 1)
            
            # Exponential backoff for retries
            if attempt < self.max_retries:
                await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        self.circuit_breaker.record_failure()
        self.stats.kb_errors += 1
        
        if last_error:
            raise last_error
        else:
            raise AdapterError("Knowledge Base request failed after all retries")
    
    def _search_local_files(self, query: str, limit: int = 5) -> str:
        """
        Search local documentation files using simple text matching
        
        Args:
            query: Search query
            limit: Maximum number of results to include
            
        Returns:
            Formatted string with search results
        """
        self.stats.file_searches += 1
        
        # CI-Light mode: return deterministic local content
        if self.ci_light:
            return f"Local documentation content for query: {query}\n\nHighlights:\n- Example snippet A\n- Example snippet B"

        if not self.docs_path.exists():
            logger.warning("Documentation path not found", path=str(self.docs_path))
            return f"Documentation path not found: {self.docs_path}"
        
        results = []
        query_lower = query.lower()
        
        try:
            # Search through all MDX files
            for mdx_file in self.docs_path.rglob("*.mdx"):
                try:
                    content = mdx_file.read_text(encoding='utf-8')
                    content_lower = content.lower()
                    
                    # Simple keyword matching
                    if query_lower in content_lower:
                        # Extract relevant section
                        lines = content.split('\n')
                        relevant_lines = []
                        
                        for i, line in enumerate(lines):
                            if query_lower in line.lower():
                                # Get context: 5 lines before and after
                                start = max(0, i - 5)
                                end = min(len(lines), i + 6)
                                relevant_lines.extend(lines[start:end])
                        
                        if relevant_lines:
                            relative_path = mdx_file.relative_to(self.docs_path)
                            results.append({
                                'path': str(relative_path),
                                'content': '\n'.join(relevant_lines[:50])  # Limit to 50 lines
                            })
                        
                        if len(results) >= limit:
                            break
                            
                except Exception as e:
                    logger.debug("Error reading file", file=str(mdx_file), error=str(e))
                    continue
            
            if not results:
                return f"No results found in local documentation for query: {query}"
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(f"**Source: {result['path']}**\n{result['content']}")
            
            return "\n\n---\n\n".join(formatted_results)
            
        except Exception as e:
            logger.error("Error reading documentation", error=str(e))
            return f"Error reading documentation: {str(e)}"
    
    async def search(self, 
                    query: str,
                    limit: int = 5,
                    score_threshold: float = 0.7,
                    context: Optional[KnowledgeResponse] = None) -> KnowledgeResponse:
        """
        Main search method implementing different strategies
        
        Args:
            query: Search query
            limit: Maximum number of results
            score_threshold: Minimum score threshold
            context: Previous search context for continuity
            
        Returns:
            KnowledgeResponse with combined results
        """
        start_time = time.time()
        self.stats.total_queries += 1
        
        # Track strategy usage
        if self.strategy not in self.stats.strategy_usage:
            self.stats.strategy_usage[self.strategy] = 0
        self.stats.strategy_usage[self.strategy] += 1
        
        logger.info("Starting knowledge search",
                   query=query,
                   strategy=self.strategy.value,
                   limit=limit,
                   score_threshold=score_threshold)
        
        try:
            if self.strategy == SearchStrategy.KB_FIRST:
                return await self._search_kb_first(query, limit, score_threshold, context)
            elif self.strategy == SearchStrategy.FILE_FIRST:
                return await self._search_file_first(query, limit, score_threshold, context)
            elif self.strategy == SearchStrategy.HYBRID:
                return await self._search_hybrid(query, limit, score_threshold, context)
            elif self.strategy == SearchStrategy.KB_ONLY:
                return await self._search_kb_only(query, limit, score_threshold, context)
            else:
                raise AdapterError(f"Unknown search strategy: {self.strategy}")
                
        finally:
            # Track response time
            response_time_ms = (time.time() - start_time) * 1000
            self.stats.total_response_time_ms += response_time_ms
            
            logger.info("Knowledge search completed",
                       query=query,
                       strategy=self.strategy.value,
                       response_time_ms=response_time_ms)
    
    async def _search_kb_first(self, query: str, limit: int, score_threshold: float, 
                              context: Optional[KnowledgeResponse]) -> KnowledgeResponse:
        """KB_FIRST strategy: Try KB first, fallback to files on failure"""
        try:
            kb_response = await self.search_knowledge_base(query, limit, score_threshold)
            
            # If KB returns good results, use them
            if kb_response.results:
                return kb_response
            
            # If KB returns no results, try files as fallback
            file_content = self._search_local_files(query, limit)
            return KnowledgeResponse(
                query=query,
                results=[],
                file_content=file_content,
                strategy_used=SearchStrategy.KB_FIRST,
                kb_available=True,
                context_used=context is not None
            )
            
        except (AdapterError, CircuitBreakerOpen):
            # KB failed, fallback to files
            file_content = self._search_local_files(query, limit)
            return KnowledgeResponse(
                query=query,
                results=[],
                file_content=file_content,
                strategy_used=SearchStrategy.FILE_FIRST,  # Indicate fallback used
                kb_available=False,
                context_used=context is not None
            )
    
    async def _search_file_first(self, query: str, limit: int, score_threshold: float,
                                context: Optional[KnowledgeResponse]) -> KnowledgeResponse:
        """FILE_FIRST strategy: Search files first, optionally enrich with KB"""
        file_content = self._search_local_files(query, limit)
        
        # Try to enrich with KB results if available
        kb_results = []
        kb_available = True
        
        try:
            if not self.circuit_breaker.is_open():
                kb_response = await self.search_knowledge_base(query, limit, score_threshold)
                kb_results = kb_response.results
        except (AdapterError, CircuitBreakerOpen):
            kb_available = False
        
        return KnowledgeResponse(
            query=query,
            results=kb_results,
            file_content=file_content,
            strategy_used=SearchStrategy.FILE_FIRST,
            kb_available=kb_available,
            context_used=context is not None
        )
    
    async def _search_hybrid(self, query: str, limit: int, score_threshold: float,
                            context: Optional[KnowledgeResponse]) -> KnowledgeResponse:
        """HYBRID strategy: Combine results from both KB and files"""
        # Search files first (always available)
        file_content = self._search_local_files(query, limit)
        
        # Try to get KB results
        kb_results = []
        kb_available = True
        
        try:
            if not self.circuit_breaker.is_open():
                kb_response = await self.search_knowledge_base(query, limit, score_threshold)
                kb_results = kb_response.results
        except (AdapterError, CircuitBreakerOpen):
            kb_available = False
        
        return KnowledgeResponse(
            query=query,
            results=kb_results,
            file_content=file_content,
            strategy_used=SearchStrategy.HYBRID,
            kb_available=kb_available,
            context_used=context is not None
        )
    
    async def _search_kb_only(self, query: str, limit: int, score_threshold: float,
                             context: Optional[KnowledgeResponse]) -> KnowledgeResponse:
        """KB_ONLY strategy: Use only Knowledge Base, no fallback"""
        try:
            return await self.search_knowledge_base(query, limit, score_threshold)
        except (AdapterError, CircuitBreakerOpen) as e:
            raise AdapterError(f"Knowledge Base unavailable and no fallback allowed: {str(e)}")
    
    def get_statistics(self) -> AdapterStatistics:
        """Get current adapter statistics"""
        return self.stats
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.stats = AdapterStatistics()
        logger.info("Adapter statistics reset")
    
    def __del__(self):
        """Cleanup on object destruction"""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            # Note: This is not ideal for async cleanup, but provides safety net
            logger.warning("Session not properly closed, attempting cleanup")


# Global adapter instance for tools
_adapter_instance: Optional[KnowledgeAdapter] = None


def get_adapter(strategy: Optional[Union[SearchStrategy, str]] = None) -> KnowledgeAdapter:
    """
    Get global adapter instance with lazy initialization
    
    Args:
        strategy: Override default strategy
        
    Returns:
        KnowledgeAdapter instance
    """
    global _adapter_instance
    
    # Check environment for configuration
    env_strategy = os.getenv('KNOWLEDGE_STRATEGY', 'HYBRID')
    actual_strategy = strategy or env_strategy
    
    if _adapter_instance is None:
        _adapter_instance = KnowledgeAdapter(
            strategy=actual_strategy,
            kb_api_url=os.getenv('KB_API_URL', 'http://localhost:8082'),
            timeout=float(os.getenv('KB_API_TIMEOUT', '30.0')),
            max_retries=int(os.getenv('KB_MAX_RETRIES', '3'))
        )
    
    return _adapter_instance


# Context manager for proper cleanup
@asynccontextmanager
async def knowledge_adapter(**kwargs):
    """
    Async context manager for Knowledge Adapter
    
    Usage:
        async with knowledge_adapter(strategy=SearchStrategy.KB_FIRST) as adapter:
            result = await adapter.search("query")
    """
    adapter = KnowledgeAdapter(**kwargs)
    try:
        yield adapter
    finally:
        await adapter.close()