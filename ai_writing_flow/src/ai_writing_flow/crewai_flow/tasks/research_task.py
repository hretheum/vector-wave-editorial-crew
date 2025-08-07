"""
Research Task

Defines the task for conducting comprehensive research and gathering information.
Integrates with Knowledge Base and external sources for deep content research.
"""

import structlog
from crewai import Task
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from ...models import ResearchResult

# Configure structured logging
logger = structlog.get_logger(__name__)


class ResearchTask:
    """
    Enhanced Research Task with Knowledge Base integration.
    
    Conducts comprehensive research including:
    - Multi-source information gathering
    - Fact verification and validation
    - Context enrichment from Knowledge Base
    - Trend analysis and current relevance checking
    - Source credibility assessment
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Research Task with configuration.
        
        Args:
            config: Task configuration including:
                - timeout: Task timeout in seconds (default: 300)
                - retry_count: Number of retries on failure (default: 2)
                - require_sources: Require source citations (default: True)
                - min_sources: Minimum number of sources (default: 3)
                - verify_facts: Enable fact verification (default: True)
                - async_execution: Enable async execution (default: False)
                - human_input: Allow human input (default: False)
        """
        self.config = config or {}
        
        # Enhanced configuration with research defaults
        self.config.setdefault('timeout', 300)  # 5 minutes for thorough research
        self.config.setdefault('retry_count', 2)
        self.config.setdefault('require_sources', True)
        self.config.setdefault('min_sources', 3)
        self.config.setdefault('verify_facts', True)
        self.config.setdefault('async_execution', False)
        self.config.setdefault('human_input', False)
        
        logger.info(
            "ResearchTask initialized",
            config=self.config
        )
    
    def create_task(self, agent, inputs: Dict[str, Any]) -> Task:
        """
        Create CrewAI Task instance for research.
        
        Args:
            agent: CrewAI Agent to execute the task
            inputs: Research requirements including:
                - topic_title: Main topic to research
                - content_type: Type of content being created
                - platform: Target platform for context
                - key_themes: Specific themes to explore
                - editorial_recommendations: Editorial guidance
                - kb_insights: Previous KB insights to build upon
                
        Returns:
            Task: Configured CrewAI Task for research
        """
        
        if not agent:
            raise ValueError("Agent is required for task creation")
        
        # Build comprehensive research task description
        task_description = self._build_task_description(inputs)
        
        try:
            # Create the task with research configuration
            task = Task(
                description=task_description,
                agent=agent,
                expected_output=self._get_expected_output_description(),
                output_pydantic=ResearchResult,
                tools=agent.tools if hasattr(agent, 'tools') else [],
                async_execution=self.config.get('async_execution', False),
                human_input=self.config.get('human_input', False)
            )
            
            logger.info(
                "ResearchTask created successfully",
                agent_role=getattr(agent, 'role', 'Unknown'),
                topic=inputs.get('topic_title', 'Unknown'),
                tools_count=len(agent.tools) if hasattr(agent, 'tools') else 0
            )
            
            return task
            
        except Exception as e:
            logger.error(
                "Failed to create ResearchTask",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _build_task_description(self, inputs: Dict[str, Any]) -> str:
        """Build detailed research task description based on inputs"""
        
        topic_title = inputs.get('topic_title', 'Unknown Topic')
        content_type = inputs.get('content_type', 'general')
        platform = inputs.get('platform', 'General')
        key_themes = inputs.get('key_themes', [])
        editorial_recommendations = inputs.get('editorial_recommendations', '')
        kb_insights = inputs.get('kb_insights', [])
        
        # Format key themes
        themes_list = '\n'.join([f"   - {theme}" for theme in key_themes]) if key_themes else "   - No specific themes identified"
        
        # Format KB insights
        kb_context = ""
        if kb_insights:
            kb_context = f"""
**Previous Knowledge Base Insights:**
{chr(10).join([f"   - {insight}" for insight in kb_insights[:5]])}
Build upon these insights in your research.
"""
        
        description = f"""
Conduct comprehensive research for the following content creation task:

**Primary Research Focus:**
- Topic: {topic_title}
- Content Type: {content_type}
- Target Platform: {platform}

**Key Themes to Explore:**
{themes_list}

**Editorial Context:**
{editorial_recommendations if editorial_recommendations else 'No specific editorial guidance provided'}
{kb_context}

**Research Requirements:**

1. **Information Gathering:**
   - Find at least {self.config.get('min_sources', 3)} authoritative sources
   - Prioritize recent and relevant information (last 2 years unless historical context needed)
   - Look for unique angles and non-obvious insights
   - Gather supporting data, statistics, and concrete examples

2. **Source Diversity:**
   - Academic/research papers for depth
   - Industry reports for current trends
   - Expert opinions and thought leader perspectives
   - Case studies and real-world applications
   - Counter-arguments and alternative viewpoints

3. **Fact Verification:**
   - Cross-reference key claims across multiple sources
   - Verify statistics and data points
   - Check publication dates for currency
   - Assess source credibility and potential biases

4. **Knowledge Base Integration:**
   - Use search tools to find relevant CrewAI patterns and examples
   - Look for similar content implementations
   - Identify best practices from the knowledge base
   - Find technical documentation if needed

5. **Insight Extraction:**
   - Identify surprising or counterintuitive findings
   - Find compelling stories and narratives
   - Discover connections between disparate pieces of information
   - Highlight practical applications and implications

6. **Gap Analysis:**
   - Identify what information is missing
   - Note areas where sources disagree
   - Flag topics that need expert consultation
   - Suggest areas for original research or investigation

Provide comprehensive research findings that will enable the creation of authoritative, 
insightful, and valuable content. Focus on depth over breadth, and always prioritize 
accuracy and relevance.
"""
        
        return description.strip()
    
    def _get_expected_output_description(self) -> str:
        """Get description of expected research output format"""
        
        return """
Provide comprehensive research findings using the ResearchResult model:

**Research Report Structure:**

REQUIRED FIELDS:
1. **sources**: List of sources with complete citation information:
   - url: Source URL (if applicable)
   - title: Source title or headline
   - author: Author name(s)
   - date: Publication date
   - type: Source type (article, research, video, etc.)
   - credibility_score: Your assessment (0.0-1.0)
   - key_points: Main takeaways from this source

2. **summary**: Executive summary of all research findings (500-800 words):
   - Overview of the topic landscape
   - Main consensus points across sources
   - Key debates or disagreements
   - Most important insights for content creation

3. **key_insights**: Bullet-point list of actionable insights:
   - Unique angles discovered
   - Surprising findings
   - Practical applications
   - Content opportunities identified

4. **data_points**: Specific facts, statistics, and evidence:
   - statistic: The specific data point
   - source: Which source it came from
   - context: Why it's relevant
   - verification_status: Verified/Unverified/Conflicting

5. **methodology**: How the research was conducted:
   - Search strategies used
   - Source selection criteria
   - Verification methods applied
   - Limitations or biases acknowledged

RESEARCH QUALITY STANDARDS:
- Minimum {self.config.get('min_sources', 3)} credible sources required
- All claims must be attributed to sources
- Conflicting information must be noted
- Recency and relevance must be considered
- Knowledge Base insights should be integrated where relevant

The research should provide a solid foundation for creating authoritative, 
accurate, and insightful content that adds genuine value to the audience.
"""
    
    def get_task_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the task configuration"""
        
        return {
            "task_type": "research",
            "version": "2.0_enhanced",
            "config": self.config,
            
            # Research-specific settings
            "research_requirements": {
                "min_sources": self.config.get('min_sources', 3),
                "require_sources": self.config.get('require_sources', True),
                "verify_facts": self.config.get('verify_facts', True),
                "timeout": self.config.get('timeout', 300)
            },
            
            # Features
            "features": {
                "kb_integration": True,
                "source_verification": self.config.get('verify_facts', True),
                "multi_perspective": True,
                "fact_checking": True,
                "insight_extraction": True,
                "gap_analysis": True
            }
        }