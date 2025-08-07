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
        sections.append(f"**Strategy used:** {response.strategy_used.value}")
        if response.response_time_ms > 0:
            sections.append(f"**Response time:** {response.response_time_ms:.0f}ms")
    
    # Knowledge Base results
    if response.results:
        sections.append("\n## 📚 Knowledge Base Results")
        
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
        sections.append("\n## 📖 Local Documentation")
        
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
            "⚠️ **Knowledge Base temporarily unavailable** (circuit breaker protection)\n\n"
            "The system is protecting against repeated failures. "
            "Please try again in a few minutes or use local documentation.\n\n"
            f"**Your query:** {query}\n"
            "**Status:** Service will auto-recover"
        )
    elif isinstance(error, asyncio.TimeoutError):
        return (
            "⚠️ **Search timed out**\n\n"
            "The knowledge search took longer than expected. "
            "Please try again with a more specific query.\n\n"
            f"**Your query:** {query}\n"
            "**Suggestion:** Try shorter, more specific terms"
        )
    else:
        return (
            "⚠️ **Knowledge system temporarily unavailable**\n\n"
            f"An unexpected error occurred: {str(error)}\n\n"
            f"**Your query:** {query}\n"
            "**Status:** Falling back to basic search methods"
        )


@tool("search_crewai_knowledge")
def search_crewai_knowledge(query: str, 
                          limit: int = 5, 
                          score_threshold: float = 0.7,
                          strategy: str = "HYBRID") -> str:
    """
    Advanced search through CrewAI knowledge base and documentation.
    
    Combines multiple sources including:
    - Vector-based semantic search
    - Local documentation files
    - Cached results for performance
    
    Args:
        query: Search query (e.g., "CrewAI agent setup", "task orchestration")
        limit: Maximum number of results to return (default: 5)
        score_threshold: Minimum relevance score (0.0-1.0, default: 0.7)
        strategy: Search strategy - HYBRID, KB_FIRST, FILE_FIRST, KB_ONLY
        
    Returns:
        Formatted search results with sources and relevance scores
        
    Examples:
        search_crewai_knowledge("How to create a CrewAI agent with custom tools")
        search_crewai_knowledge("debugging CrewAI memory issues", limit=3)
        search_crewai_knowledge("task dependencies", strategy="KB_FIRST")
    """
    start_time = time.time()
    
    logger.info("Knowledge search requested", 
               query=query, 
               limit=limit, 
               score_threshold=score_threshold,
               strategy=strategy)
    
    try:
        # Get adapter and run async search
        adapter = _get_adapter(strategy)
        
        # Run async search in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                adapter.search(query, limit, score_threshold)
            )
        finally:
            loop.close()
        
        # Add performance metrics
        response.response_time_ms = (time.time() - start_time) * 1000
        
        return _format_knowledge_response(response)
        
    except Exception as e:
        return _handle_tool_error(e, query)


@tool("get_flow_examples")
def get_flow_examples(pattern_type: str) -> str:
    """
    Get specific CrewAI workflow and pattern examples.
    
    Provides curated examples for common CrewAI patterns and workflows.
    
    Args:
        pattern_type: Type of pattern to get examples for
        Available types:
        - agent_patterns: Agent creation and configuration
        - task_orchestration: Task workflow patterns  
        - crew_configuration: Crew setup and configuration
        - tool_integration: Custom tool patterns
        - error_handling: Error handling patterns
        - flow_control: Conditional flow patterns
        
    Returns:
        Detailed examples with code snippets and explanations
        
    Examples:
        get_flow_examples("agent_patterns")
        get_flow_examples("task_orchestration")
    """
    logger.info("Flow examples requested", pattern_type=pattern_type)
    
    if pattern_type not in FLOW_PATTERNS:
        available_patterns = ", ".join(FLOW_PATTERNS.keys())
        return (
            f"⚠️ **Unknown pattern type:** {pattern_type}\n\n"
            f"**Available patterns:**\n"
            + "\n".join([f"- **{key}**: {info['description']}" 
                        for key, info in FLOW_PATTERNS.items()])
        )
    
    pattern_info = FLOW_PATTERNS[pattern_type]
    search_query = pattern_info["query"]
    
    try:
        # Use knowledge search with pattern-specific query
        adapter = _get_adapter("HYBRID")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                adapter.search(search_query, limit=3, score_threshold=0.6)
            )
        finally:
            loop.close()
        
        # Format response with pattern context
        formatted_response = f"# 🔧 {pattern_info['description']}\n\n"
        formatted_response += _format_knowledge_response(response, include_performance=False)
        
        return formatted_response
        
    except Exception as e:
        return _handle_tool_error(e, search_query)


@tool("troubleshoot_crewai")
def troubleshoot_crewai(issue_type: str) -> str:
    """
    Get troubleshooting help for common CrewAI issues.
    
    Provides solutions and debugging steps for common problems.
    
    Args:
        issue_type: Type of issue to troubleshoot
        Available types:
        - installation: Installation and dependency issues
        - memory: Memory configuration problems
        - tools: Tool-related issues and errors
        - performance: Performance and optimization issues
        - llm: LLM provider and configuration issues
        - planning: Task planning and execution issues
        
    Returns:
        Troubleshooting guide with step-by-step solutions
        
    Examples:
        troubleshoot_crewai("installation")
        troubleshoot_crewai("memory")
    """
    logger.info("Troubleshooting requested", issue_type=issue_type)
    
    if issue_type not in ISSUE_TYPES:
        available_issues = ", ".join(ISSUE_TYPES.keys())
        return (
            f"⚠️ **Unknown issue type:** {issue_type}\n\n"
            f"**Common issue types:**\n"
            + "\n".join([f"- **{key}**: {info['description']}" 
                        for key, info in ISSUE_TYPES.items()])
        )
    
    issue_info = ISSUE_TYPES[issue_type]
    search_query = issue_info["query"]
    
    try:
        # Search for troubleshooting information
        adapter = _get_adapter("HYBRID")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                adapter.search(search_query, limit=5, score_threshold=0.5)
            )
        finally:
            loop.close()
        
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


# Backward Compatibility Wrappers
# These maintain the same interface as the original tools

@tool("search_crewai_docs")
def search_crewai_docs(query: str) -> str:
    """
    Search CrewAI documentation for relevant information.
    
    DEPRECATED: Use search_crewai_knowledge for enhanced functionality.
    This is a compatibility wrapper that uses the new knowledge system.
    
    Args:
        query: Search query string
        
    Returns:
        Relevant documentation content
    """
    logger.info("Legacy search_crewai_docs called", query=query)
    
    try:
        # Use new system with file-first strategy for backward compatibility
        return search_crewai_knowledge(query, strategy="FILE_FIRST")
    except Exception as e:
        # Fallback to basic file search if new system fails
        from .knowledge_base_tool import search_crewai_docs as original_search
        return original_search(query)


@tool("get_crewai_example") 
def get_crewai_example(topic: str) -> str:
    """
    Get specific CrewAI code examples.
    
    DEPRECATED: Use get_flow_examples for enhanced functionality.
    This is a compatibility wrapper with the original examples.
    
    Args:
        topic: Topic to get examples for (e.g., "crew creation", "agent definition")
        
    Returns:
        Example code and explanation
    """
    logger.info("Legacy get_crewai_example called", topic=topic)
    
    # Map legacy topics to new pattern types
    topic_mapping = {
        "crew creation": "crew_configuration",
        "agent definition": "agent_patterns", 
        "task creation": "task_orchestration",
        "tool integration": "tool_integration"
    }
    
    if topic.lower() in topic_mapping:
        return get_flow_examples(topic_mapping[topic.lower()])
    
    # Fallback to original implementation
    from .knowledge_base_tool import get_crewai_example as original_example
    return original_example(topic)


@tool("list_crewai_topics")
def list_crewai_topics() -> str:
    """
    List available CrewAI documentation topics.
    
    DEPRECATED: Enhanced search provides better topic discovery.
    This is a compatibility wrapper.
    
    Returns:
        List of available topics in the documentation
    """
    logger.info("Legacy list_crewai_topics called")
    
    try:
        # Provide enhanced topic listing
        response = "# Available CrewAI Documentation Topics\n\n"
        
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
        # Fallback to original implementation
        from .knowledge_base_tool import list_crewai_topics as original_list
        return original_list()


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