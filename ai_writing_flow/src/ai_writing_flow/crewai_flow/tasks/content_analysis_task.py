"""
Content Analysis Task

Defines the task for analyzing input content and requirements.
Creates detailed analysis of content needs, audience, and strategy.
"""

import structlog
from crewai import Task
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ...models import ContentAnalysisResult

# Configure structured logging
logger = structlog.get_logger(__name__)

# Backward compatibility - deprecated
class ContentAnalysisOutput(BaseModel):
    """DEPRECATED: Use ContentAnalysisResult from models.py instead"""
    
    content_type: str = Field(..., description="Identified content type")
    target_platform: str = Field(..., description="Target platform for content")
    analysis_confidence: float = Field(..., description="Confidence score for analysis (0-1)")
    recommended_approach: str = Field(..., description="Recommended content generation approach")
    key_themes: list = Field(..., description="Key themes identified in content")
    audience_indicators: Dict[str, Any] = Field(..., description="Audience analysis results")
    content_structure: Dict[str, Any] = Field(..., description="Recommended content structure")
    
class ContentAnalysisTask:
    """
    Enhanced Content Analysis Task with Knowledge Base integration.
    
    Production-ready task for analyzing input content and determining
    optimal processing strategy with comprehensive error handling,
    structured logging, and performance monitoring.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Content Analysis Task with enhanced configuration.
        
        Args:
            config: Task configuration including:
                - timeout: Task timeout in seconds (default: 60)
                - retry_count: Number of retries on failure (default: 3)
                - use_new_model: Use ContentAnalysisResult model (default: True)
                - async_execution: Enable async execution (default: False)
                - human_input: Allow human input (default: False)
        """
        self.config = config or {}
        
        # Enhanced configuration with production defaults
        self.config.setdefault('timeout', 60)
        self.config.setdefault('retry_count', 3)
        self.config.setdefault('use_new_model', True)
        self.config.setdefault('async_execution', False)
        self.config.setdefault('human_input', False)
        
        logger.info(
            "ContentAnalysisTask initialized", 
            config=self.config
        )
    
    def create_task(self, agent, inputs: Dict[str, Any]) -> Task:
        """
        Create CrewAI Task instance for content analysis.
        
        Args:
            agent: CrewAI Agent to execute the task
            inputs: Input data for analysis
            
        Returns:
            Task: Configured CrewAI Task for content analysis
        """
        
        if not agent:
            raise ValueError("Agent is required for task creation")
        
        # Build comprehensive task description
        task_description = self._build_task_description(inputs)
        
        # Choose output model based on configuration
        output_model = ContentAnalysisResult if self.config.get('use_new_model', True) else ContentAnalysisOutput
        
        try:
            # Create the task with enhanced configuration
            task = Task(
                description=task_description,
                agent=agent,
                expected_output=self._get_expected_output_description(),
                output_pydantic=output_model,
                tools=agent.tools if hasattr(agent, 'tools') else [],
                async_execution=self.config.get('async_execution', False),
                human_input=self.config.get('human_input', False)
            )
            
            logger.info(
                "ContentAnalysisTask created successfully",
                agent_role=getattr(agent, 'role', 'Unknown'),
                output_model=output_model.__name__,
                tools_count=len(agent.tools) if hasattr(agent, 'tools') else 0
            )
            
            return task
            
        except Exception as e:
            logger.error(
                "Failed to create ContentAnalysisTask",
                error=str(e),
                error_type=type(e).__name__,
                agent_available=agent is not None
            )
            raise
    
    def _build_task_description(self, inputs: Dict[str, Any]) -> str:
        """Build detailed task description based on inputs"""
        
        topic_title = inputs.get('topic_title', 'Unknown Topic')
        platform = inputs.get('platform', 'General')
        content_type = inputs.get('content_type', 'STANDALONE')
        file_path = inputs.get('file_path', '')
        editorial_recommendations = inputs.get('editorial_recommendations', '')
        
        description = f"""
Analyze the following content requirements and provide comprehensive strategic recommendations:

**Primary Analysis Target:**
- Topic: {topic_title}
- Target Platform: {platform}  
- Content Type: {content_type}
- Source Material: {file_path if file_path else 'No source material provided'}

**Editorial Context:**
{editorial_recommendations if editorial_recommendations else 'No specific editorial recommendations provided'}

**Required Analysis:**

1. **Content Classification:**
   - Identify the primary content category and format requirements
   - Assess technical complexity level and audience expertise requirements
   - Determine optimal content length and structure

2. **Platform Optimization:**
   - Analyze platform-specific requirements and constraints
   - Identify optimal posting formats and engagement strategies
   - Recommend hashtags, mentions, and promotional elements

3. **Audience Analysis:**
   - Profile target audience demographics and interests
   - Identify engagement patterns and content preferences
   - Assess viral potential and sharing likelihood

4. **Content Strategy:**
   - Recommend content generation approach and methodology
   - Identify key themes and topics to emphasize
   - Suggest content structure and information hierarchy

5. **Performance Optimization:**
   - Identify opportunities for engagement enhancement
   - Recommend SEO and discoverability improvements
   - Suggest A/B testing strategies

Provide actionable, specific recommendations that can guide the content generation pipeline.
Focus on practical insights that improve content quality and audience engagement.
"""
        
        return description.strip()
    
    def _get_expected_output_description(self) -> str:
        """Get description of expected output format based on model selection"""
        
        if self.config.get('use_new_model', True):
            return """
Provide a comprehensive content analysis using the ContentAnalysisResult model:

**Enhanced Content Analysis Report with Knowledge Base Integration:**

REQUIRED FIELDS:
1. **content_type**: Primary content category (e.g., "technical_tutorial", "thought_leadership", "case_study")
2. **viral_score**: Viral potential score (0.0-1.0) based on engagement analysis
3. **complexity_level**: Content complexity ("beginner", "intermediate", "advanced")
4. **recommended_flow_path**: Optimal CrewAI flow path for content generation
5. **target_platform**: Target platform for content publication
6. **analysis_confidence**: Confidence score (0.0-1.0) for analysis quality
7. **processing_time**: Time taken for analysis in seconds

OPTIONAL FIELDS WITH DEFAULTS:
8. **kb_insights**: Array of insights from Knowledge Base searches
9. **key_themes**: Array of main themes to emphasize
10. **audience_indicators**: Target audience analysis object
11. **content_structure**: Recommended content structure and format
12. **kb_available**: Whether Knowledge Base was available (boolean)
13. **search_strategy_used**: KB search strategy used
14. **kb_query_count**: Number of KB queries performed

KNOWLEDGE BASE INTEGRATION:
- Use enhanced_knowledge_search for CrewAI patterns and best practices
- Use search_flow_patterns for workflow orchestration recommendations
- Include relevant KB insights in kb_insights array
- Track KB usage metrics for monitoring

All recommendations must be specific, actionable, and optimized for viral potential and audience engagement.
"""
        else:
            return """
Provide a comprehensive content analysis in the following structured format:

**Content Analysis Report:**

1. **content_type**: Primary content category (e.g., "technical_tutorial", "thought_leadership", "case_study")
2. **target_platform**: Confirmed target platform with specific format recommendations
3. **analysis_confidence**: Confidence score (0.0-1.0) for the analysis quality
4. **recommended_approach**: Strategic approach for content generation
5. **key_themes**: Array of main themes to emphasize
6. **audience_indicators**: Object containing audience analysis
7. **content_structure**: Object containing content structure recommendations

All recommendations should be specific, actionable, and optimized for the target platform and audience.
"""
    
    def _build_task_context(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build context information for the task"""
        
        return {
            "task_type": "content_analysis",
            "priority": "high",
            "timeout": self.config.get('timeout', 30),
            "retry_count": self.config.get('retry_count', 3),
            "platform_context": self._get_platform_context(inputs.get('platform', '')),
            "content_context": self._get_content_context(inputs.get('content_type', ''))
        }
    
    def _get_platform_context(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific context and requirements"""
        
        platform_contexts = {
            "LinkedIn": {
                "max_length": 3000,
                "optimal_length": 1500,
                "hashtag_limit": 5,
                "engagement_style": "professional",
                "content_types": ["thought_leadership", "industry_insights", "professional_tips"]
            },
            "Twitter": {
                "max_length": 280,
                "thread_length": 10,
                "hashtag_limit": 3,
                "engagement_style": "casual",
                "content_types": ["quick_tips", "observations", "threads"]
            },
            "Blog": {
                "max_length": 5000,
                "optimal_length": 2000,
                "structure": "hierarchical",
                "engagement_style": "educational",
                "content_types": ["tutorials", "deep_dives", "case_studies"]
            }
        }
        
        return platform_contexts.get(platform, {
            "max_length": 2000,
            "engagement_style": "adaptive",
            "content_types": ["general"]
        })
    
    def _get_content_context(self, content_type: str) -> Dict[str, Any]:
        """Get content type-specific context"""
        
        content_contexts = {
            "STANDALONE": {
                "independence": "high",
                "context_required": "minimal",
                "structure": "self_contained"
            },
            "SERIES": {
                "independence": "medium", 
                "context_required": "moderate",
                "structure": "connected"
            },
            "REFERENCE": {
                "independence": "low",
                "context_required": "high", 
                "structure": "supplementary"
            }
        }
        
        return content_contexts.get(content_type, {
            "independence": "medium",
            "context_required": "moderate",
            "structure": "flexible"
        })
    
    def get_task_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the task configuration"""
        
        output_model = "ContentAnalysisResult" if self.config.get('use_new_model', True) else "ContentAnalysisOutput"
        
        return {
            "task_type": "content_analysis", 
            "version": "2.2_enhanced",
            "output_format": output_model,
            "timeout": self.config.get('timeout', 60),
            "retry_count": self.config.get('retry_count', 3),
            "async_execution": self.config.get('async_execution', False),
            "human_input": self.config.get('human_input', False),
            "use_new_model": self.config.get('use_new_model', True),
            
            # Enhanced features
            "features": {
                "kb_integration": True,
                "viral_scoring": self.config.get('use_new_model', True),
                "flow_routing": self.config.get('use_new_model', True),
                "performance_metrics": True,
                "structured_logging": True,
                "error_handling": True
            }
        }