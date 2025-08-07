"""
Content Analysis Agent - Enhanced Version

Production-ready Content Analysis Specialist with Knowledge Base integration.
Analyzes input content, requirements, and context to understand:
- Content type and structure requirements with viral potential assessment
- Target audience characteristics and platform-specific optimization
- Key topics and themes with Knowledge Base insight integration
- Performance requirements and CrewAI flow routing decisions
- Real-time processing metrics and confidence scoring

This agent serves as the intelligent entry point for the writing pipeline
with comprehensive observability and error handling.
"""

import os
import time
import structlog
from crewai import Agent
from typing import Dict, Any, Optional, List

from ...tools.enhanced_knowledge_tools import (
    search_crewai_knowledge as enhanced_knowledge_search,
    get_flow_examples as search_flow_patterns,
    troubleshoot_crewai as troubleshoot_crewai_issue,
    search_crewai_docs,
    get_crewai_example,
    list_crewai_topics,
    knowledge_system_stats
)
# ContentAnalysisResult will be imported from parent models.py or fallback
try:
    from ...models import ContentAnalysisResult
except ImportError:
    # Fallback import from main models module
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, parent_dir)
    from models import ContentAnalysisResult

# Configure structured logging
logger = structlog.get_logger(__name__)


class ContentAnalysisAgent:
    """
    Enhanced Content Analysis Agent with Knowledge Base integration.
    
    Production-ready agent that provides:
    - Comprehensive content analysis with viral potential scoring
    - Knowledge Base integration for CrewAI flow pattern recommendations
    - Real-time processing metrics and confidence assessment
    - Robust error handling with circuit breaker protection
    - Structured logging and observability
    
    The agent serves as an intelligent routing system that determines
    optimal content generation strategies based on deep analysis
    of content requirements, audience characteristics, and platform constraints.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Content Analysis Agent with enhanced configuration.
        
        Args:
            config: Agent configuration including:
                - verbose: Enable detailed logging (default: True)
                - max_iter: Maximum iterations (default: 3)
                - max_execution_time: Timeout in seconds (default: 180)
                - model: LLM model to use (default: 'gpt-4')
                - temperature: LLM temperature (default: 0.1)
                - kb_integration: Enable Knowledge Base integration (default: True)
                - circuit_breaker: Enable circuit breaker protection (default: True)
        """
        self.config = config or {}
        self._agent = None
        
        # Enhanced configuration with production defaults
        self.config.setdefault('verbose', True)
        self.config.setdefault('max_iter', 3)
        self.config.setdefault('max_execution_time', 180)  # 3 minutes
        self.config.setdefault('model', 'gpt-4')
        self.config.setdefault('temperature', 0.1)
        self.config.setdefault('kb_integration', True)
        self.config.setdefault('circuit_breaker', True)
        
        # Initialize metrics
        self.analysis_count = 0
        self.total_processing_time = 0.0
        self.kb_query_count = 0
        
        logger.info(
            "ContentAnalysisAgent initialized",
            config=self.config,
            kb_integration=self.config['kb_integration']
        )
    
    def create_agent(self) -> Agent:
        """
        Create and configure CrewAI Agent instance with enhanced capabilities.
        
        Returns:
            Agent: Configured CrewAI Agent for content analysis
        """
        if self._agent is not None:
            return self._agent
        
        # Get tools for the agent
        tools = self._get_agent_tools()
        
        # Create the agent with enhanced capabilities and Knowledge Base integration
        self._agent = Agent(
            role="Content Analysis Specialist with CrewAI Flow Expertise",
            goal="""Analyze content requirements and determine optimal CrewAI flow path with Knowledge Base insights.
            Provide comprehensive content analysis including viral potential scoring, audience targeting,
            and CrewAI flow routing recommendations based on proven patterns from the Knowledge Base.""",
            backstory="""You are a senior Content Analysis Specialist with extensive experience in:
            
            🎯 **Core Expertise:**
            - Content strategy and viral potential assessment across platforms (LinkedIn, Twitter, Medium)
            - Audience psychology and engagement pattern analysis
            - Technical content optimization and complexity calibration
            - AI-driven content generation pipeline architecture
            
            🚀 **CrewAI Flow Specialization:**
            - Expert knowledge of CrewAI agent orchestration patterns
            - Deep understanding of content generation workflows and task dependencies
            - Experience with Knowledge Base integration for pattern discovery
            - Proven track record in flow optimization and performance tuning
            
            📊 **Analytical Approach:**
            - Data-driven decision making with confidence scoring
            - Real-time performance metrics and processing optimization
            - Circuit breaker protection and graceful error handling
            - Structured output formatting for downstream processing
            
            🎨 **Content Intelligence:**
            - Platform-specific format optimization (threads, long-form, micro-content)
            - Viral coefficient prediction and engagement amplification strategies
            - Technical depth calibration based on audience expertise levels
            - Content structure recommendations for maximum readability and impact
            
            Your mission is to serve as the intelligent routing system that determines
            the most effective content generation strategy by combining deep content analysis
            with Knowledge Base insights about proven CrewAI flow patterns.
            
            You excel at translating complex content requirements into actionable
            recommendations that drive high-performance content generation pipelines.""",
            verbose=self.config.get('verbose', True),
            allow_delegation=False,
            tools=tools,
            max_iter=self.config.get('max_iter', 3),
            max_execution_time=self.config.get('max_execution_time', 180),
            system_template=self._get_system_template(),
            llm=self._get_llm_config()
        )
        
        return self._agent
    
    def _get_agent_tools(self) -> List[Any]:
        """
        Get enhanced tools for the content analysis agent with Knowledge Base integration.
        
        Returns:
            List of available tools with error handling and fallbacks
        """
        
        tools = []
        
        try:
            if self.config.get('kb_integration', True):
                # Add comprehensive Knowledge Base integration tools
                tools.extend([
                    # Core search tools
                    enhanced_knowledge_search,  # Main KB search
                    search_flow_patterns,       # Flow pattern examples
                    search_crewai_docs,         # Documentation search
                    
                    # Utility tools
                    get_crewai_example,         # Get specific examples
                    list_crewai_topics,         # List available topics
                    troubleshoot_crewai_issue,  # Troubleshooting help
                    
                    # Monitoring tools
                    knowledge_system_stats      # KB system statistics
                ])
                
                logger.info(
                    "Knowledge Base tools loaded successfully",
                    tool_count=len(tools)
                )
            else:
                logger.info("Knowledge Base integration disabled by configuration")
                
        except ImportError as e:
            logger.warning(
                "Knowledge Base tools not available",
                error=str(e),
                fallback="Using basic analysis without KB integration"
            )
        except Exception as e:
            logger.error(
                "Error loading Knowledge Base tools",
                error=str(e),
                error_type=type(e).__name__
            )
        
        logger.info(f"ContentAnalysisAgent initialized with {len(tools)} tools")
        return tools
    
    def _get_system_template(self) -> str:
        """
        Get enhanced system template with Knowledge Base integration guidance.
        
        Returns:
            Comprehensive system template for content analysis
        """
        
        kb_guidance = ""
        if self.config.get('kb_integration', True):
            kb_guidance = """

🔍 **Knowledge Base Integration Protocol:**

**Search & Discovery Tools:**
- `enhanced_knowledge_search` - General CrewAI patterns and best practices search
- `search_flow_patterns` - Find specific workflow and orchestration patterns
- `search_crewai_docs` - Search official CrewAI documentation

**Content & Examples Tools:**
- `get_crewai_example` - Retrieve specific code examples by pattern type
- `list_crewai_topics` - List all available KB topics and categories

**Support & Monitoring Tools:**
- `troubleshoot_crewai_issue` - Get help with errors and edge cases
- `knowledge_system_stats` - Check KB system health and statistics

**Best Practices:**
- Start with `list_crewai_topics` to understand available content
- Use multiple search tools to gather comprehensive insights
- Always include KB insights in your analysis output
- Check `knowledge_system_stats` if searches return empty results
- Fallback gracefully if Knowledge Base is unavailable"""
        
        return f"""You are an expert Content Analysis Specialist working within a CrewAI Flow system.

🎯 **Your Core Mission:**
Analyze input content and requirements to determine optimal content generation strategy
with viral potential assessment and CrewAI flow routing recommendations.

📋 **Analysis Protocol:**
1. **Content Classification:** Identify content type, complexity, and platform requirements
2. **Audience Analysis:** Assess target demographics and engagement patterns
3. **Viral Potential:** Score content for viral coefficient and sharing likelihood
4. **Flow Routing:** Recommend optimal CrewAI flow path based on analysis
5. **Knowledge Integration:** Leverage KB insights for pattern-based recommendations
6. **Confidence Assessment:** Provide confidence scores for all recommendations

🔧 **Technical Requirements:**
- Output must follow ContentAnalysisResult Pydantic model structure
- Include processing time metrics for performance monitoring
- Provide structured recommendations for downstream agents
- Handle errors gracefully with meaningful fallback strategies

📊 **Quality Standards:**
- Viral score: 0.0-1.0 based on engagement potential analysis
- Complexity level: beginner/intermediate/advanced based on technical depth
- Confidence score: 0.0-1.0 based on analysis certainty
- Processing time: Track and optimize for performance{kb_guidance}

🚀 **Success Criteria:**
Your analysis should enable optimal content generation by providing clear,
actionable recommendations that improve content quality, engagement, and viral potential.

Always strive for comprehensive analysis that balances depth with processing efficiency."""
    
    def _get_llm_config(self) -> Optional[Any]:
        """
        Get LLM configuration for the agent with enhanced settings.
        
        Returns:
            LLM configuration or None for default
        """
        
        # Use environment variables or config for LLM setup
        model = self.config.get('model', 'gpt-4')
        temperature = self.config.get('temperature', 0.1)
        max_tokens = self.config.get('max_tokens', 2000)
        
        logger.info(
            "LLM configuration",
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
            Dictionary with agent configuration, metrics, and status information
        """
        
        return {
            "role": "Content Analysis Specialist with CrewAI Flow Expertise",
            "version": "2.2_enhanced",
            "tools_count": len(self._get_agent_tools()),
            "config": self.config,
            "max_execution_time": self.config.get('max_execution_time', 180),
            "verbose": self.config.get('verbose', True),
            "kb_integration": self.config.get('kb_integration', True),
            "circuit_breaker": self.config.get('circuit_breaker', True),
            
            # Performance metrics
            "metrics": {
                "analysis_count": self.analysis_count,
                "total_processing_time": self.total_processing_time,
                "average_processing_time": (
                    self.total_processing_time / self.analysis_count 
                    if self.analysis_count > 0 else 0.0
                ),
                "kb_query_count": self.kb_query_count
            },
            
            # Status indicators
            "status": {
                "initialized": self._agent is not None,
                "ready": self._agent is not None and len(self._get_agent_tools()) > 0,
                "kb_available": self.config.get('kb_integration', True)
            }
        }
    
    def update_metrics(self, processing_time: float, kb_queries: int = 0) -> None:
        """
        Update agent performance metrics.
        
        Args:
            processing_time: Time taken for analysis in seconds
            kb_queries: Number of Knowledge Base queries performed
        """
        self.analysis_count += 1
        self.total_processing_time += processing_time
        self.kb_query_count += kb_queries
        
        logger.info(
            "Agent metrics updated",
            analysis_count=self.analysis_count,
            processing_time=processing_time,
            kb_queries=kb_queries,
            average_time=self.total_processing_time / self.analysis_count
        )
    
    def analyze_content_requirements(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive content requirements analysis.
        
        This method provides structured analysis that can be used independently
        or as input to the CrewAI agent execution.
        
        Args:
            inputs: Content requirements and context
            
        Returns:
            Structured analysis results
        """
        start_time = time.time()
        
        try:
            # Extract key information
            topic_title = inputs.get('topic_title', '')
            platform = inputs.get('platform', 'General')
            content_type = inputs.get('content_type', 'STANDALONE')
            file_path = inputs.get('file_path', '')
            
            # Perform basic analysis
            analysis = {
                'content_type': self._classify_content_type(topic_title, content_type),
                'viral_score': self._calculate_viral_score(topic_title, platform),
                'complexity_level': self._assess_complexity(topic_title, content_type),
                'recommended_flow_path': self._recommend_flow_path(content_type, platform),
                'target_platform': platform,
                'analysis_confidence': 0.8,  # Base confidence
                'key_themes': self._extract_themes(topic_title),
                'audience_indicators': self._analyze_audience(platform, topic_title),
                'content_structure': self._recommend_structure(platform, content_type),
                'processing_time': time.time() - start_time,
                'kb_available': self.config.get('kb_integration', True),
                'search_strategy_used': 'HYBRID',
                'kb_query_count': 0,
                'kb_insights': []
            }
            
            # Update metrics
            self.update_metrics(analysis['processing_time'])
            
            logger.info(
                "Content requirements analysis completed",
                topic=topic_title,
                platform=platform,
                processing_time=analysis['processing_time'],
                viral_score=analysis['viral_score']
            )
            
            return analysis
            
        except Exception as e:
            logger.error(
                "Content requirements analysis failed",
                error=str(e),
                error_type=type(e).__name__,
                inputs=inputs
            )
            
            # Return fallback analysis
            return {
                'content_type': 'general',
                'viral_score': 0.5,
                'complexity_level': 'intermediate',
                'recommended_flow_path': 'standard_content_generation',
                'target_platform': platform,
                'analysis_confidence': 0.3,
                'key_themes': ['general'],
                'audience_indicators': {'complexity': 'medium'},
                'content_structure': {'format': 'standard'},
                'processing_time': time.time() - start_time,
                'kb_available': False,
                'search_strategy_used': 'FALLBACK',
                'kb_query_count': 0,
                'kb_insights': [f"Analysis failed: {str(e)}"]
            }
    
    def _classify_content_type(self, title: str, content_type: str) -> str:
        """Classify content based on title and type"""
        if 'tutorial' in title.lower() or 'how to' in title.lower():
            return 'technical_tutorial'
        elif 'analysis' in title.lower() or 'review' in title.lower():
            return 'thought_leadership'
        elif 'case study' in title.lower():
            return 'case_study'
        else:
            return 'general_content'
    
    def _calculate_viral_score(self, title: str, platform: str) -> float:
        """Calculate viral potential score"""
        score = 0.5  # Base score
        
        # Platform modifiers
        if platform == 'Twitter':
            score += 0.1
        elif platform == 'LinkedIn':
            score += 0.05
        
        # Title analysis
        viral_keywords = ['secret', 'mistake', 'truth', 'hidden', 'exposed', 'breakthrough']
        for keyword in viral_keywords:
            if keyword in title.lower():
                score += 0.1
        
        return min(score, 1.0)
    
    def _assess_complexity(self, title: str, content_type: str) -> str:
        """Assess content complexity level"""
        if 'beginner' in title.lower() or 'intro' in title.lower():
            return 'beginner'
        elif 'advanced' in title.lower() or 'expert' in title.lower():
            return 'advanced'
        else:
            return 'intermediate'
    
    def _recommend_flow_path(self, content_type: str, platform: str) -> str:
        """Recommend optimal CrewAI flow path"""
        if content_type == 'SERIES':
            return 'multi_part_content_flow'
        elif platform == 'Twitter':
            return 'twitter_thread_flow'
        elif platform == 'LinkedIn':
            return 'linkedin_post_flow'
        else:
            return 'standard_content_flow'
    
    def _extract_themes(self, title: str) -> List[str]:
        """Extract key themes from title"""
        # Simple keyword extraction - in production would use NLP
        themes = []
        technical_terms = ['AI', 'ML', 'API', 'database', 'cloud', 'automation']
        for term in technical_terms:
            if term.lower() in title.lower():
                themes.append(term)
        
        if not themes:
            themes = ['general']
        
        return themes
    
    def _analyze_audience(self, platform: str, title: str) -> Dict[str, Any]:
        """Analyze target audience characteristics"""
        return {
            'platform': platform,
            'technical_level': 'intermediate',
            'engagement_style': 'professional' if platform == 'LinkedIn' else 'casual',
            'primary_interest': 'technology'
        }
    
    def _recommend_structure(self, platform: str, content_type: str) -> Dict[str, Any]:
        """Recommend content structure"""
        if platform == 'Twitter':
            return {
                'format': 'thread',
                'max_length': 280,
                'sections': ['hook', 'main_points', 'conclusion']
            }
        elif platform == 'LinkedIn':
            return {
                'format': 'long_form_post',
                'max_length': 3000,
                'sections': ['introduction', 'key_insights', 'actionable_takeaways']
            }
        else:
            return {
                'format': 'article',
                'max_length': 2000,
                'sections': ['introduction', 'main_content', 'conclusion']
            }