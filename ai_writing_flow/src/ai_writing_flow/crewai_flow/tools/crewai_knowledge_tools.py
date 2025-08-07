"""
CrewAI Knowledge Tools

Provides Knowledge Base integration tools specifically designed for CrewAI agents.
Uses @tool decorator for CrewAI 0.152.0 compatibility.
"""

import asyncio
from crewai.tools import tool
from typing import Dict, Any, Optional, List, Annotated
from ...tools.enhanced_knowledge_tools import FLOW_PATTERNS, ISSUE_TYPES, _get_adapter, _format_knowledge_response


@tool("enhanced_knowledge_search")
def enhanced_knowledge_search(
    query: Annotated[str, "Search query for knowledge base"],
    strategy: Annotated[str, "Search strategy: KB_FIRST, FILE_FIRST, HYBRID, KB_ONLY"] = "HYBRID",
    limit: Annotated[int, "Maximum number of results to return"] = 5,
    score_threshold: Annotated[float, "Minimum score threshold for results"] = 0.7
) -> str:
    """
    Enhanced knowledge search with multiple search strategies and comprehensive results.
    
    This tool searches the Knowledge Base API and/or local documentation files
    to find relevant information for CrewAI patterns, troubleshooting, and best practices.
    
    Args:
        query: The search query (e.g., "CrewAI agent creation patterns")
        strategy: Search strategy to use (default: HYBRID)
        limit: Maximum number of results (default: 5)
        score_threshold: Minimum relevance score (default: 0.7)
        
    Returns:
        Formatted string with search results including sources and content
    """
    
    try:
        # Get knowledge adapter
        adapter = _get_adapter(strategy)
        
        # Create event loop if needed for async operation
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Perform search
        try:
            response = loop.run_until_complete(
                adapter.search(
                    query=query,
                    limit=limit,
                    score_threshold=score_threshold
                )
            )
        except Exception as e:
            # Fallback to synchronous search if async fails
            return f"Knowledge search temporarily unavailable: {str(e)}\n\nPlease try a more specific query or check system status."
        
        # Format and return results
        return _format_knowledge_response(response, include_performance=True)
        
    except Exception as e:
        return f"Knowledge search failed: {str(e)}\n\nTry checking your query format or system connectivity."


@tool("search_flow_patterns")
def search_flow_patterns(
    pattern_type: Annotated[str, "Pattern type: agent_patterns, task_orchestration, crew_configuration, tool_integration, error_handling, flow_control"],
    specific_query: Annotated[str, "Specific aspect of the pattern to search for"] = ""
) -> str:
    """
    Search for specific CrewAI Flow patterns and implementation examples.
    
    This tool searches for common CrewAI Flow patterns including agent creation,
    task orchestration, crew configuration, and error handling patterns.
    
    Args:
        pattern_type: Type of pattern to search for
        specific_query: Additional specific information to find within the pattern
        
    Returns:
        Formatted string with pattern information and examples
    """
    
    try:
        # Get pattern query
        if pattern_type not in FLOW_PATTERNS:
            available_patterns = ", ".join(FLOW_PATTERNS.keys())
            return f"Unknown pattern type '{pattern_type}'. Available patterns: {available_patterns}"
        
        pattern_info = FLOW_PATTERNS[pattern_type]
        base_query = pattern_info["query"]
        
        # Enhance query with specific request
        if specific_query:
            enhanced_query = f"{base_query} {specific_query}"
        else:
            enhanced_query = base_query
        
        # Perform enhanced knowledge search
        result = enhanced_knowledge_search(
            query=enhanced_query,
            strategy="HYBRID",
            limit=3,
            score_threshold=0.6
        )
        
        # Add pattern context
        pattern_context = f"""
## {pattern_info['description']}

**Pattern Type**: {pattern_type.replace('_', ' ').title()}
**Base Query**: {base_query}

### Search Results:
{result}
"""
        
        return pattern_context.strip()
        
    except Exception as e:
        return f"Pattern search failed: {str(e)}\n\nPlease check the pattern type and try again."


@tool("troubleshoot_crewai_issue")
def troubleshoot_crewai_issue(
    issue_type: Annotated[str, "Issue type: installation, memory, tools, performance, llm, planning"],
    error_description: Annotated[str, "Description of the specific error or problem"] = ""
) -> str:
    """
    Troubleshoot common CrewAI issues and provide solutions.
    
    This tool helps debug and resolve common CrewAI problems by searching
    for solutions and best practices based on issue type.
    
    Args:
        issue_type: Type of issue being experienced
        error_description: Detailed description of the error or problem
        
    Returns:
        Formatted troubleshooting guide with solutions and recommendations
    """
    
    try:
        # Get issue query
        if issue_type not in ISSUE_TYPES:
            available_issues = ", ".join(ISSUE_TYPES.keys())
            return f"Unknown issue type '{issue_type}'. Available types: {available_issues}"
        
        issue_info = ISSUE_TYPES[issue_type]
        base_query = issue_info["query"]
        
        # Enhance query with error description
        if error_description:
            enhanced_query = f"{base_query} {error_description}"
        else:
            enhanced_query = base_query
        
        # Search for solutions
        result = enhanced_knowledge_search(
            query=enhanced_query,
            strategy="HYBRID",
            limit=5,
            score_threshold=0.5
        )
        
        # Format troubleshooting response
        troubleshooting_guide = f"""
## Troubleshooting: {issue_info['description']}

**Issue Type**: {issue_type.replace('_', ' ').title()}
**Search Query**: {base_query}

### Potential Solutions:
{result}

### General Troubleshooting Tips:
1. Check CrewAI version compatibility: `pip show crewai`
2. Verify environment variables and API keys are set correctly
3. Review agent and task configurations for syntax errors
4. Check system resources (memory, CPU) if experiencing performance issues
5. Enable verbose logging for detailed error information

### Next Steps:
- If the issue persists, check the CrewAI GitHub repository for similar issues
- Consider updating to the latest CrewAI version
- Review the official CrewAI documentation for configuration changes
"""
        
        return troubleshooting_guide.strip()
        
    except Exception as e:
        return f"Troubleshooting search failed: {str(e)}\n\nPlease try again with a more specific issue description."


# Export tools for easy import
__all__ = [
    "enhanced_knowledge_search",
    "search_flow_patterns", 
    "troubleshoot_crewai_issue"
]