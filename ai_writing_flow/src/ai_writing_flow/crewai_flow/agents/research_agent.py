"""
Research Agent

Conducts research and gathers relevant information for content creation:
- Knowledge base integration and search
- External data gathering and validation
- Context enrichment and fact verification
- Source credibility assessment

Integrates with Knowledge Base adapter for comprehensive research capabilities.
"""

import time
import structlog
from crewai import Agent
from typing import Dict, Any, Optional, List

from ...tools.enhanced_knowledge_tools import (
    search_crewai_knowledge,
    search_crewai_docs,
    get_crewai_example,
    list_crewai_topics
)

# Configure structured logging
logger = structlog.get_logger(__name__)

class ResearchAgent:
    """
    Enhanced Research Agent with Knowledge Base integration.
    
    Conducts comprehensive research for content creation:
    - Deep topic analysis with multiple search strategies
    - Source validation and credibility assessment
    - Context enrichment from Knowledge Base
    - Fact verification and accuracy checking
    - Trend analysis and current relevance
    - Multi-perspective information gathering
    
    Optimized for high-quality content research with structured output.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Research Agent with enhanced configuration.
        
        Args:
            config: Agent configuration including:
                - verbose: Enable detailed logging (default: True)
                - max_iter: Maximum iterations (default: 5)
                - max_execution_time: Timeout in seconds (default: 300)
                - model: LLM model to use (default: 'gpt-4')
                - temperature: LLM temperature (default: 0.2)
                - search_depth: Research depth level (default: 'comprehensive')
                - verify_sources: Enable source verification (default: True)
        """
        self.config = config or {}
        self._agent = None
        
        # Enhanced configuration with research-specific defaults
        self.config.setdefault('verbose', True)
        self.config.setdefault('max_iter', 5)  # More iterations for thorough research
        self.config.setdefault('max_execution_time', 300)  # 5 minutes
        self.config.setdefault('model', 'gpt-4')
        self.config.setdefault('temperature', 0.2)  # Lower for factual accuracy
        self.config.setdefault('search_depth', 'comprehensive')
        self.config.setdefault('verify_sources', True)
        
        # Initialize metrics
        self.research_count = 0
        self.total_processing_time = 0.0
        self.sources_found = 0
        self.kb_queries = 0
        
        logger.info(
            "ResearchAgent initialized",
            config=self.config,
            search_depth=self.config['search_depth']
        )
    
    def create_agent(self) -> Agent:
        """
        Create and configure CrewAI Agent instance with research tools.
        
        Returns:
            Agent: Configured CrewAI Agent for research tasks
        """
        if self._agent is not None:
            return self._agent
        
        # Get research tools
        tools = self._get_research_tools()
        
        # Create the agent with research expertise
        self._agent = Agent(
            role="Senior Research Specialist with Deep Knowledge Mining Expertise",
            goal="""Conduct comprehensive research to gather accurate, relevant, and insightful 
            information that forms the foundation for high-quality content creation. Focus on:
            - Finding authoritative sources and verified information
            - Identifying unique angles and non-obvious insights
            - Gathering supporting data, examples, and case studies
            - Ensuring factual accuracy and current relevance
            - Building a rich context for content development""",
            backstory="""You are a veteran Research Specialist with expertise spanning:
            
            🔍 **Research Excellence:**
            - 15+ years in investigative research and fact-checking
            - Expert in academic, technical, and industry research methodologies
            - Skilled in distinguishing reliable sources from misinformation
            - Deep understanding of research ethics and citation standards
            
            📚 **Knowledge Synthesis:**
            - Master at connecting disparate pieces of information
            - Ability to identify patterns and trends across sources
            - Expert in contextualizing information for different audiences
            - Skilled in extracting actionable insights from complex data
            
            🧪 **Verification Methods:**
            - Rigorous fact-checking and cross-referencing protocols
            - Source credibility assessment frameworks
            - Data validation and accuracy verification techniques
            - Bias detection and balanced perspective gathering
            
            💡 **Value Addition:**
            - Finding unique angles that others miss
            - Discovering compelling stories in data
            - Identifying expert voices and authoritative sources
            - Building comprehensive knowledge foundations
            
            Your research forms the bedrock of exceptional content. You understand that 
            great content starts with great research, and you never compromise on accuracy 
            or depth. You excel at finding not just information, but insights that make 
            content truly valuable and differentiated.""",
            verbose=self.config.get('verbose', True),
            allow_delegation=False,
            tools=tools,
            max_iter=self.config.get('max_iter', 5),
            max_execution_time=self.config.get('max_execution_time', 300),
            system_template=self._get_system_template(),
            llm=self._get_llm_config()
        )
        
        logger.info(
            "Research agent created successfully",
            tools_count=len(tools),
            max_iter=self.config.get('max_iter', 5)
        )
        
        return self._agent
    
    def _get_research_tools(self) -> List[Any]:
        """
        Get specialized research tools with Knowledge Base integration.
        
        Returns:
            List of research-optimized tools
        """
        tools = []
        
        try:
            # Core research tools from Knowledge Base
            tools.extend([
                search_crewai_knowledge,  # General knowledge search
                search_crewai_docs,       # Documentation deep dive
                get_crewai_example,       # Find relevant examples
                list_crewai_topics        # Discover related topics
            ])
            
            logger.info(
                "Research tools loaded successfully",
                tool_count=len(tools)
            )
            
        except ImportError as e:
            logger.warning(
                "Some research tools not available",
                error=str(e),
                fallback="Using available tools only"
            )
        except Exception as e:
            logger.error(
                "Error loading research tools",
                error=str(e),
                error_type=type(e).__name__
            )
        
        return tools
    
    def _get_system_template(self) -> str:
        """
        Get research-optimized system template.
        
        Returns:
            System template for research tasks
        """
        return f"""You are an expert Research Specialist conducting deep research for content creation.

🎯 **Research Mission:**
Gather comprehensive, accurate, and insightful information that will form the foundation 
for exceptional content. Focus on depth, accuracy, and unique perspectives.

📋 **Research Protocol:**

1. **Initial Discovery:**
   - Use `list_crewai_topics` to understand the knowledge landscape
   - Identify key themes and related concepts
   - Map out research territories to explore

2. **Deep Dive Research:**
   - Use `search_crewai_knowledge` for comprehensive topic exploration
   - Use `search_crewai_docs` for technical documentation and details
   - Cross-reference multiple sources for accuracy
   - Look for patterns, trends, and connections

3. **Evidence Gathering:**
   - Use `get_crewai_example` to find concrete examples and case studies
   - Collect supporting data, statistics, and proof points
   - Identify expert quotes and authoritative voices
   - Document all sources for proper attribution

4. **Insight Extraction:**
   - Identify non-obvious insights and unique angles
   - Find compelling stories and narratives in the data
   - Highlight surprising facts or counterintuitive findings
   - Connect dots that others might miss

5. **Quality Assurance:**
   - Verify facts through multiple sources
   - Check currency and relevance of information
   - Assess source credibility and potential biases
   - Ensure balanced perspective representation

🔧 **Research Depth Level: {self.config.get('search_depth', 'comprehensive')}**
- Basic: Quick facts and surface-level information
- Comprehensive: Deep dive with multiple perspectives
- Exhaustive: Leave no stone unturned

📊 **Output Requirements:**
- Organized findings by theme or importance
- Clear source attribution for all claims
- Confidence levels for different pieces of information
- Identified knowledge gaps or areas needing clarification
- Actionable insights for content creation

⚡ **Research Standards:**
- Accuracy above all - never compromise on facts
- Depth over breadth when sources conflict
- Recent information preferred unless historical context needed
- Primary sources preferred over secondary when available
- Always note limitations or caveats in findings

Your research excellence directly impacts content quality. Be thorough, be accurate, be insightful."""
    
    def _get_llm_config(self) -> Optional[Any]:
        """
        Get LLM configuration optimized for research tasks.
        
        Returns:
            LLM configuration or None for default
        """
        model = self.config.get('model', 'gpt-4')
        temperature = self.config.get('temperature', 0.2)  # Lower for accuracy
        max_tokens = self.config.get('max_tokens', 3000)  # More for comprehensive research
        
        logger.info(
            "Research LLM configuration",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Return None to use default LLM configuration
        # In production, this would return a configured LLM instance
        return None
    
    @property
    def agent(self) -> Agent:
        """Get the CrewAI Agent instance."""
        if self._agent is None:
            self._agent = self.create_agent()
        return self._agent
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the agent configuration and performance.
        
        Returns:
            Dictionary with agent configuration, metrics, and status
        """
        return {
            "role": "Senior Research Specialist",
            "version": "2.0_enhanced",
            "tools_count": len(self._get_research_tools()),
            "config": self.config,
            "search_depth": self.config.get('search_depth', 'comprehensive'),
            "verify_sources": self.config.get('verify_sources', True),
            
            # Performance metrics
            "metrics": {
                "research_count": self.research_count,
                "total_processing_time": self.total_processing_time,
                "average_processing_time": (
                    self.total_processing_time / self.research_count 
                    if self.research_count > 0 else 0.0
                ),
                "sources_found": self.sources_found,
                "kb_queries": self.kb_queries,
                "avg_sources_per_research": (
                    self.sources_found / self.research_count
                    if self.research_count > 0 else 0.0
                )
            },
            
            # Status indicators  
            "status": {
                "initialized": self._agent is not None,
                "ready": self._agent is not None and len(self._get_research_tools()) > 0
            }
        }
    
    def update_metrics(self, processing_time: float, sources: int = 0, kb_queries: int = 0) -> None:
        """
        Update agent performance metrics.
        
        Args:
            processing_time: Time taken for research in seconds
            sources: Number of sources found
            kb_queries: Number of KB queries performed
        """
        self.research_count += 1
        self.total_processing_time += processing_time
        self.sources_found += sources
        self.kb_queries += kb_queries
        
        logger.info(
            "Research metrics updated",
            research_count=self.research_count,
            processing_time=processing_time,
            sources=sources,
            avg_time=self.total_processing_time / self.research_count
        )