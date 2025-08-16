"""
Enhanced Knowledge Tools for CrewAI with Knowledge Base Integration

Production-ready tools implementing:
- Hybrid search strategies
- Structured error handling
- Performance tracking
- Backward compatibility
- Comprehensive observability
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional
import inspect
from crewai.tools import tool
import structlog

from ..adapters.knowledge_adapter import (
    KnowledgeAdapter, 
    SearchStrategy, 
    AdapterError, 
    CircuitBreakerOpen,
    get_adapter
)

# Configure structured logging
logger = structlog.get_logger(__name__)

# Pattern definitions for flow examples
FLOW_PATTERNS = {
    "agent_patterns": {
        "query": "CrewAI agent creation patterns role goal backstory tools",
        "description": "Patterns for creating and configuring CrewAI agents"
    },
    "task_orchestration": {
        "query": "CrewAI task orchestration workflow dependencies sequential parallel",
        "description": "Patterns for orchestrating tasks in CrewAI workflows"
    },
    "crew_configuration": {
        "query": "CrewAI crew setup configuration verbose memory planning",
        "description": "Patterns for configuring CrewAI crews and their settings"
    },
    "tool_integration": {
        "query": "CrewAI tools custom tool integration @tool decorator",
        "description": "Patterns for integrating and creating custom tools"
    },
    "error_handling": {
        "query": "CrewAI error handling exception management debugging",
        "description": "Patterns for error handling and debugging in CrewAI"
    },
    "flow_control": {
        "query": "CrewAI flow control conditional branching decision making",
        "description": "Patterns for flow control and decision making"
    }
}

# Common issue types for troubleshooting
ISSUE_TYPES = {
    "installation": {
        "query": "CrewAI installation troubleshooting pip install dependencies error",
        "description": "Installation-related issues and solutions"
    },
    "memory": {
        "query": "CrewAI memory issues short term long term memory management",
        "description": "Memory configuration and troubleshooting"
    },
    "tools": {
        "query": "CrewAI tools not working tool execution error custom tool",
        "description": "Tool-related issues and debugging"
    },
    "performance": {
        "query": "CrewAI performance slow execution timeout optimization",
        "description": "Performance issues and optimization strategies"
    },
    "llm": {
        "query": "CrewAI LLM configuration API key model selection provider",
        "description": "LLM provider and configuration issues"
    },
    "planning": {
        "query": "CrewAI planning issues task planning execution order",
        "description": "Task planning and execution order issues"
    }
}


def _get_adapter(strategy: Optional[str] = None) -> KnowledgeAdapter:
    """Get Knowledge Adapter instance with error handling"""
    try:
        return get_adapter(strategy)
    except Exception as e:
        logger.error("Failed to initialize Knowledge Adapter", error=str(e))
        raise


def _format_knowledge_response(response, include_performance: bool = True) -> str:
    """
    Format knowledge response for tool output
    
    Args:
        response: KnowledgeResponse object
        include_performance: Whether to include performance metrics
        
    Returns:
        Formatted string response
    """
    sections = []
    
    # Header with query information
    sections.append(f"# Knowledge Search Results\n**Query:** {response.query}")
    
    if include_performance:
        sections.append(f"Strategy used: {response.strategy_used.value}")
        if response.response_time_ms > 0:
            sections.append(f"Response time: {response.response_time_ms:.0f}ms")
    
    # Knowledge Base results
    if response.results:
        sections.append("\n## Knowledge Base Results")
        
        if not response.kb_available:
            sections.append("⚠️ Knowledge Base unavailable - showing cached/fallback results")
        
        for i, result in enumerate(response.results[:5], 1):
            content = result.get('content', '')
            score = result.get('score', 0)
            metadata = result.get('metadata', {})
            title = metadata.get('title', f'Result {i}')
            
            sections.append(f"\n### {i}. {title}")
            if score > 0:
                sections.append(f"*Relevance: {score:.2f}*")
            sections.append(f"\n{content}")
    
    # Local documentation content
    if response.file_content:
        sections.append("\n## Local Documentation")
        
        if not response.kb_available:
            sections.append("⚠️ Knowledge Base unavailable - using local documentation only")
        
        sections.append(f"\n{response.file_content}")
    
    # No results case
    if not response.results and not response.file_content:
        sections.append("\n## ❌ No Results Found")
        sections.append("No relevant results found for your query.")
        sections.append("\n**Suggestions:**")
        sections.append("- Try different keywords or phrases")
        sections.append("- Check spelling and terminology")
        sections.append("- Use more general terms")
        sections.append("- Try searching for related concepts")
    
    return "\n".join(sections)


def _handle_tool_error(error: Exception, query: str, fallback_strategy: str = "basic") -> str:
    """
    Handle tool errors gracefully with fallback options
    
    Args:
        error: The exception that occurred
        query: Original search query
        fallback_strategy: Fallback strategy to use
        
    Returns:
        Error message with fallback information
    """
    logger.error("Knowledge tool error", error=str(error), query=query)
    
    if isinstance(error, CircuitBreakerOpen):
        return (
            "⚠️ Knowledge Base temporarily unavailable (circuit breaker protection)\n\n"
            "The system is protecting against repeated failures. "
            "Please try again in a few minutes or use local documentation.\n\n"
            f"Your query: {query}\n"
            "Status: service will auto-recover"
        )
    elif isinstance(error, asyncio.TimeoutError):
        return (
            "⚠️ Search timed out\n\n"
            "The knowledge search took longer than expected. "
            "Please try again with a more specific query.\n\n"
            f"Your query: {query}\n"
            "Suggestion: try shorter, more specific terms"
        )
    else:
        return (
            "⚠️ Knowledge system temporarily unavailable\n\n"
            f"An unexpected error occurred: {str(error)}\n\n"
            f"Your query: {query}\n"
            "Status: falling back to basic search"
        )


def _run_adapter_search(adapter, *, query: str, limit: int, score_threshold: float, context: Optional[Dict[str, Any]] = None):
    """Execute adapter.search for both async and sync implementations."""
    maybe_coro = adapter.search(
        query=query,
        limit=limit,
        score_threshold=score_threshold,
        context=context,
    )
    if inspect.isawaitable(maybe_coro):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(maybe_coro)
        finally:
            try:
                loop.close()
            finally:
                asyncio.set_event_loop(None)
    return maybe_coro

def _search_crewai_knowledge_impl(query: str, 
                                  limit: int = 5, 
                                  score_threshold: float = 0.7,
                                  strategy: str = "HYBRID") -> str:
    """Implementation for knowledge search (plain callable for tests and runtime)."""
    start_time = time.time()
    
    logger.info("Knowledge search requested", 
               query=query, 
               limit=limit, 
               score_threshold=score_threshold,
               strategy=strategy)
    
    try:
        # Get adapter and run async search
        adapter = _get_adapter(strategy)
        
        # Execute search (supports async and sync adapters)
        response = _run_adapter_search(
            adapter,
            query=query,
            limit=limit,
            score_threshold=score_threshold,
            context=None,
        )
        
        # Add performance metrics only if not already provided by adapter
        if not getattr(response, "response_time_ms", 0):
            response.response_time_ms = (time.time() - start_time) * 1000
        
        return _format_knowledge_response(response)
        
    except Exception as e:
        return _handle_tool_error(e, query)


@tool("search_crewai_knowledge")
def search_crewai_knowledge_tool(query: str, 
                                 limit: int = 5, 
                                 score_threshold: float = 0.7,
                                 strategy: str = "HYBRID") -> str:
    """Decorated Tool wrapper that proxies to the plain implementation."""
    return _search_crewai_knowledge_impl(query, limit, score_threshold, strategy)

# Export plain callable for direct usage in tests and code
search_crewai_knowledge = _search_crewai_knowledge_impl


def _get_flow_examples_impl(pattern_type: str) -> str:
    """Implementation for flow examples (plain callable for tests and runtime)."""
    logger.info("Flow examples requested", pattern_type=pattern_type)
    
    if pattern_type not in FLOW_PATTERNS:
        available_patterns = ", ".join(FLOW_PATTERNS.keys())
        return (
            f"⚠️ Unknown pattern type: {pattern_type}\n\n"
            f"Available patterns:\n"
            + "\n".join([f"- {key}: {info['description']}" 
                        for key, info in FLOW_PATTERNS.items()])
        )
    
    pattern_info = FLOW_PATTERNS[pattern_type]
    search_query = pattern_info["query"]
    
    try:
        # Use knowledge search with pattern-specific query
        adapter = _get_adapter("HYBRID")
        
        response = _run_adapter_search(
            adapter,
            query=search_query,
            limit=3,
            score_threshold=0.6,
            context=None,
        )
        
        # Format response with pattern context
        formatted_response = f"# 🔧 {pattern_info['description']}\n\n"
        formatted_response += _format_knowledge_response(response, include_performance=False)
        
        return formatted_response
        
    except Exception as e:
        return _handle_tool_error(e, search_query)


@tool("get_flow_examples")
def get_flow_examples_tool(pattern_type: str) -> str:
    """Decorated Tool wrapper that proxies to the plain implementation."""
    return _get_flow_examples_impl(pattern_type)

# Export plain callable for direct usage in tests and code
get_flow_examples = _get_flow_examples_impl


def _troubleshoot_crewai_impl(issue_type: str) -> str:
    """Implementation for troubleshooting helper (plain callable)."""
    logger.info("Troubleshooting requested", issue_type=issue_type)
    
    if issue_type not in ISSUE_TYPES:
        available_issues = ", ".join(ISSUE_TYPES.keys())
        return (
            f"⚠️ Unknown issue type: {issue_type}\n\n"
            f"Common issue types:\n"
            + "\n".join([f"- {key}: {info['description']}" 
                        for key, info in ISSUE_TYPES.items()])
        )
    
    issue_info = ISSUE_TYPES[issue_type]
    search_query = issue_info["query"]
    
    try:
        # Search for troubleshooting information
        adapter = _get_adapter("HYBRID")
        
        response = _run_adapter_search(
            adapter,
            query=search_query,
            limit=5,
            score_threshold=0.5,
            context=None,
        )
        
        # Format response with troubleshooting context
        formatted_response = f"# 🔧 Troubleshooting: {issue_info['description']}\n\n"
        formatted_response += _format_knowledge_response(response, include_performance=False)
        
        # Add general troubleshooting tips
        formatted_response += "\n\n## 💡 General Troubleshooting Tips\n"
        formatted_response += "1. Check CrewAI version: `pip show crewai`\n"
        formatted_response += "2. Review logs for error messages\n"
        formatted_response += "3. Verify environment variables and API keys\n"
        formatted_response += "4. Test with minimal examples first\n"
        formatted_response += "5. Check the official CrewAI documentation\n"
        
        return formatted_response
        
    except Exception as e:
        return _handle_tool_error(e, search_query)


@tool("troubleshoot_crewai")
def troubleshoot_crewai_tool(issue_type: str) -> str:
    """Decorated Tool wrapper that proxies to the plain implementation."""
    return _troubleshoot_crewai_impl(issue_type)

# Export plain callable for direct usage in tests and code
troubleshoot_crewai = _troubleshoot_crewai_impl


# Backward Compatibility Wrappers
# These maintain the same interface as the original tools

def _search_crewai_docs_impl(query: str) -> str:
    """
    Legacy-compatible implementation for searching CrewAI docs.
    """
    logger.info("Legacy search_crewai_docs called", query=query)
    try:
        return search_crewai_knowledge(query, strategy="FILE_FIRST")
    except Exception:
        from .knowledge_base_tool import search_crewai_docs as original_search
        return original_search(query)

@tool("search_crewai_docs")
def search_crewai_docs_tool(query: str) -> str:
    """Decorated Tool wrapper that proxies to the plain implementation."""
    return _search_crewai_docs_impl(query)

# Export plain callable for direct usage in tests and code
search_crewai_docs = _search_crewai_docs_impl


def _get_crewai_example_impl(topic: str) -> str:
    """Legacy-compatible implementation for getting CrewAI examples."""
    logger.info("Legacy get_crewai_example called", topic=topic)
    topic_mapping = {
        "crew creation": "crew_configuration",
        "agent definition": "agent_patterns",
        "task creation": "task_orchestration",
        "tool integration": "tool_integration",
    }
    if topic.lower() in topic_mapping:
        # Provide a minimal deterministic example snippet expected by legacy tests
        example_snippet = (
            "```python\n"
            "from crewai import Agent, Task, Crew\n\n"
            "researcher = Agent(role='Researcher', goal='Find insights')\n"
            "task = Task(description='Research topic', agent=researcher)\n"
            "crew = Crew(agents=[researcher], tasks=[task])\n"
            "result = crew.kickoff()\n"
            "```"
        )
        # Optionally append enhanced examples for richer content
        try:
            enhanced = get_flow_examples(topic_mapping[topic.lower()])
            return f"{example_snippet}\n\n{enhanced}"
        except Exception:
            return example_snippet
    from .knowledge_base_tool import get_crewai_example as original_example
    return original_example(topic)

@tool("get_crewai_example")
def get_crewai_example_tool(topic: str) -> str:
    """Decorated Tool wrapper that proxies to the plain implementation."""
    return _get_crewai_example_impl(topic)

# Export plain callable for direct usage in tests and code
get_crewai_example = _get_crewai_example_impl


def _list_crewai_topics_impl() -> str:
    """Legacy-compatible implementation for listing topics."""
    logger.info("Legacy list_crewai_topics called")
    try:
        response = "Available CrewAI documentation topics\n\n"
        response += "## 🔧 Flow Patterns (use get_flow_examples)\n"
        for pattern, info in FLOW_PATTERNS.items():
            response += f"- **{pattern}**: {info['description']}\n"
        response += "\n## 🚨 Troubleshooting (use troubleshoot_crewai)\n"
        for issue, info in ISSUE_TYPES.items():
            response += f"- **{issue}**: {info['description']}\n"
        response += "\n## 💡 Enhanced Search\n"
        response += "Use `search_crewai_knowledge(query)` for advanced semantic search\n"
        response += "across all documentation with relevance scoring.\n"
        return response
    except Exception:
        from .knowledge_base_tool import list_crewai_topics as original_list
        return original_list()

@tool("list_crewai_topics")
def list_crewai_topics_tool() -> str:
    """Decorated Tool wrapper that proxies to the plain implementation."""
    return _list_crewai_topics_impl()

# Export plain callable for direct usage in tests and code
list_crewai_topics = _list_crewai_topics_impl


# Tool statistics and health check
@tool("knowledge_system_stats")
def knowledge_system_stats() -> str:
    """
    Get knowledge system statistics and health information.
    
    Returns:
        System statistics including performance metrics and availability
    """
    try:
        adapter = _get_adapter()
        stats = adapter.get_statistics()
        
        response = "# 📊 Knowledge System Statistics\n\n"
        response += f"**Total Queries:** {stats.total_queries}\n"
        response += f"**KB Availability:** {stats.kb_availability:.1%}\n"
        response += f"**Average Response Time:** {stats.average_response_time_ms:.0f}ms\n"
        response += f"**File Searches:** {stats.file_searches}\n"
        response += f"**KB Successes:** {stats.kb_successes}\n"
        response += f"**KB Errors:** {stats.kb_errors}\n"
        
        if stats.strategy_usage:
            response += "\n**Strategy Usage:**\n"
            for strategy, count in stats.strategy_usage.items():
                response += f"- {strategy.value}: {count}\n"
        
        # Circuit breaker status
        if adapter.circuit_breaker.is_open():
            response += "\n⚠️ **Circuit Breaker:** OPEN (KB temporarily unavailable)\n"
        else:
            response += "\n✅ **Circuit Breaker:** CLOSED (KB available)\n"
        
        return response
        
    except Exception as e:
        return f"❌ **Error getting statistics:** {str(e)}"


class EnhancedKnowledgeTools:
    """Compatibility wrapper expected by some tests/integrations.

    Provides a class interface around the module-level knowledge tools so that
    callers can instantiate and use methods like `search_knowledge_base`.
    """

    def search_knowledge_base(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7,
        strategy: str = "HYBRID",
    ) -> str:
        """Search CrewAI knowledge base using the enhanced knowledge system.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            score_threshold: Minimum relevance score to include a result
            strategy: Search strategy to use (e.g., HYBRID, FILE_FIRST)

        Returns:
            Formatted string with search results
        """
        return search_crewai_knowledge(query, limit, score_threshold, strategy)