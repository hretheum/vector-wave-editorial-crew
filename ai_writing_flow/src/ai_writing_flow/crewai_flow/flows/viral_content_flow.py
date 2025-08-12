"""
Viral Content Flow

Specialized flow path for viral content with:
- Trend research and timing optimization
- Viral writing techniques
- Engagement optimization
"""

import time
import structlog
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
try:
    from crewai.flow import Flow as _CrewFlow
    BaseFlow = _CrewFlow
except Exception:
    BaseFlow = object

from ...models import (
    ContentAnalysisResult,
    ResearchResult,
    DraftContent
)
from ..agents.research_agent import ResearchAgent
from ..tasks.research_task import ResearchTask

# Configure structured logging
logger = structlog.get_logger(__name__)


class ViralFlowState(BaseModel):
    """State management for Viral Content Flow"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"viral_flow_{int(time.time())}")
    
    # Input data
    topic_title: str = ""
    platform: str = "Twitter"
    content_type: str = "viral"
    key_themes: list[str] = Field(default_factory=list)
    editorial_recommendations: str = ""
    
    # Flow state
    current_stage: str = "initialized"
    flow_path: str = "viral"
    
    # Viral specifics
    trend_keywords: List[str] = Field(default_factory=list)
    viral_score: float = 0.0
    urgency_level: str = "high"  # high, medium, low
    target_emotion: str = "excitement"  # excitement, curiosity, controversy, humor
    
    # Results
    trend_analysis: Optional[Dict[str, Any]] = None
    research_result: Optional[ResearchResult] = None
    viral_draft: Optional[DraftContent] = None
    engagement_optimization: Optional[Dict[str, Any]] = None
    
    # Metrics
    start_time: float = Field(default_factory=time.time)
    research_time: float = 0.0
    writing_time: float = 0.0
    optimization_time: float = 0.0
    estimated_reach: int = 0


class ViralContentFlow(BaseFlow):
    """
    Viral Content Flow with specialized processing:
    
    Flow stages:
    1. Trend research and timing analysis
    2. Viral writing with hooks
    3. Engagement optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Viral Content Flow
        
        Args:
            config: Flow configuration including:
                - verbose: Enable detailed logging
                - platform_specific: Enable platform optimizations
                - max_hashtags: Maximum hashtags to include
                - viral_threshold: Minimum viral score
        """
        super().__init__()
        # Ensure state exists without CrewAI runtime
        try:
            self.state  # type: ignore[attr-defined]
        except Exception:
            self.state = ViralFlowState()
        self.config = config or {}
        
        # Default configuration
        self.config.setdefault('verbose', True)
        self.config.setdefault('platform_specific', True)
        self.config.setdefault('max_hashtags', 5)
        self.config.setdefault('viral_threshold', 0.7)
        
        # Initialize specialized agents for viral content
        self.research_agent = ResearchAgent(config={
            'verbose': self.config.get('verbose', True),
            'search_depth': 'surface',  # Quick research for viral content
            'verify_sources': False,  # Speed over deep verification
            'min_sources': 2  # Fewer sources for quick turnaround
        })
        
        logger.info(
            "ViralContentFlow initialized",
            flow_id=self.state.flow_id,
            config=self.config
        )
    
    def trend_research_timing(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point: Quick trend research and timing analysis
        
        Args:
            inputs: Flow inputs including topic, platform
            
        Returns:
            Trend analysis and timing recommendations
        """
        start_time = time.time()
        
        # Update state with inputs
        self.state.topic_title = inputs.get('topic_title', '')
        self.state.platform = inputs.get('platform', 'Twitter')
        self.state.key_themes = inputs.get('key_themes', [])
        self.state.editorial_recommendations = inputs.get('editorial_recommendations', '')
        self.state.trend_keywords = inputs.get('trend_keywords', [])
        self.state.current_stage = "trend_research"
        
        logger.info(
            "Starting trend research and timing analysis",
            flow_id=self.state.flow_id,
            topic=self.state.topic_title,
            platform=self.state.platform
        )
        
        try:
            # Create research agent and task for trend analysis
            agent = self.research_agent.create_agent()
            task_creator = ResearchTask(config={
                'min_sources': 2,
                'verify_facts': False,
                'require_sources': True,
                'search_depth': 'surface',
                'timeout': 180  # 3 minutes for quick research
            })
            
            # Trend-focused research inputs
            research_inputs = {
                'topic_title': self.state.topic_title,
                'content_type': 'viral_trend_analysis',
                'platform': self.state.platform,
                'key_themes': self.state.key_themes + [
                    "trending topics",
                    "viral patterns",
                    "engagement triggers",
                    "timing optimization",
                    "current buzz"
                ],
                'editorial_recommendations': self.state.editorial_recommendations,
                'kb_insights': []
            }
            
            # Create and execute task (mock for testing)
            task = task_creator.create_task(agent, research_inputs)
            
            # Mock trend research result
            research_result = ResearchResult(
                sources=[
                    {
                        "url": "https://trends.example.com/current",
                        "title": "Current Viral Trends Analysis",
                        "author": "TrendWatch",
                        "date": "2025-01",
                        "type": "trend_analysis",
                        "credibility_score": "0.8",
                        "key_points": "Peak engagement times, Viral triggers, Platform algorithms"
                    },
                    {
                        "url": "https://viral.example.com/patterns",
                        "title": "Viral Content Patterns",
                        "author": "ViralMetrics",
                        "date": "2025-01",
                        "type": "analytics",
                        "credibility_score": "0.85",
                        "key_points": "Hook formulas, Engagement patterns, Share triggers"
                    }
                ],
                summary="""Trend analysis reveals:
                
                1. Peak engagement window: Next 4-6 hours
                2. Related trending topics: #AI, #Innovation, #TechTrends
                3. Viral triggers: Controversy + Practical value
                4. Platform algorithm favoring: Short, punchy content with visuals
                5. Competition analysis: Low saturation in this niche""",
                key_insights=[
                    "Post within next 2 hours for maximum reach",
                    "Use controversy hook with practical payoff",
                    "Include data visualization for shares",
                    "Target emotion: Curiosity + FOMO",
                    "Optimal length: 280 chars with thread"
                ],
                data_points=[
                    {
                        "statistic": "73% higher engagement with visual content",
                        "source": "Platform analytics",
                        "context": "Image or video inclusion",
                        "verification_status": "Verified"
                    }
                ],
                methodology="Quick trend scanning and viral pattern analysis"
            )
            
            # Mock trend analysis
            trend_analysis = {
                "timing": {
                    "optimal_post_time": "Within 2 hours",
                    "urgency": "high",
                    "competition_level": "low",
                    "trending_window": "6-8 hours"
                },
                "viral_factors": {
                    "controversy_level": 0.7,
                    "practical_value": 0.8,
                    "emotional_trigger": 0.9,
                    "shareability": 0.85
                },
                "platform_optimization": {
                    "Twitter": {
                        "use_thread": True,
                        "include_poll": True,
                        "optimal_hashtags": ["#AI", "#Innovation", "#TechTrends"],
                        "media": "infographic recommended"
                    }
                },
                "predicted_reach": 50000,
                "viral_score": 0.82
            }
            
            # Update state
            self.state.research_result = research_result
            self.state.trend_analysis = trend_analysis
            self.state.viral_score = trend_analysis["viral_score"]
            self.state.research_time = time.time() - start_time
            self.state.estimated_reach = trend_analysis["predicted_reach"]
            
            # Update agent metrics
            self.research_agent.update_metrics(
                processing_time=self.state.research_time,
                sources=len(research_result.sources),
                kb_queries=3  # Mock value
            )
            
            logger.info(
                "Trend research completed",
                flow_id=self.state.flow_id,
                viral_score=self.state.viral_score,
                urgency=trend_analysis["timing"]["urgency"],
                predicted_reach=self.state.estimated_reach,
                duration=self.state.research_time
            )
            
            return {
                "research": research_result,
                "trend_analysis": trend_analysis,
                "viral_score": self.state.viral_score,
                "next_stage": "viral_writing"
            }
            
        except Exception as e:
            logger.error(
                "Trend research failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def viral_writing_optimization(self, research_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create viral content with engagement hooks
        
        Args:
            research_output: Output from trend research
            
        Returns:
            Viral-optimized content draft
        """
        start_time = time.time()
        self.state.current_stage = "viral_writing"
        
        logger.info(
            "Starting viral content writing",
            flow_id=self.state.flow_id,
            platform=self.state.platform,
            viral_score=self.state.viral_score
        )
        
        try:
            # Create viral-optimized draft
            draft = DraftContent(
                title=f"🔥 {self.state.topic_title}",  # Emoji for attention
                draft=self._generate_viral_draft(),
                word_count=280,  # Twitter optimized
                structure_type="quick_take",
                key_sections=[
                    "Hook",
                    "Controversy/Problem",
                    "Unexpected Solution",
                    "Call to Action",
                    "Thread Continuation"
                ],
                non_obvious_insights=[
                    "AI can now predict viral content with 82% accuracy",
                    "The best time to post is NOW (algorithm change)",
                    "Controversy + Value = Viral formula",
                    "Visual content gets 73% more shares"
                ]
            )
            
            # Update state
            self.state.viral_draft = draft
            self.state.writing_time = time.time() - start_time
            
            logger.info(
                "Viral writing completed",
                flow_id=self.state.flow_id,
                word_count=draft.word_count,
                sections=len(draft.key_sections),
                duration=self.state.writing_time
            )
            
            return {
                "draft": draft,
                "viral_elements": {
                    "hook_strength": 0.9,
                    "shareability": 0.85,
                    "emotion_trigger": 0.8
                },
                "next_stage": "engagement_optimization"
            }
            
        except Exception as e:
            logger.error(
                "Viral writing failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _generate_viral_draft(self) -> str:
        """Generate viral-optimized content"""
        
        platform_specific = ""
        if self.state.platform == "Twitter":
            hashtags = " ".join([f"#{tag}" for tag in self.state.trend_analysis["platform_optimization"]["Twitter"]["optimal_hashtags"][:self.config.get('max_hashtags', 5)]])
            platform_specific = f"\n\n{hashtags}"
        
        # Main tweet/post
        main_content = f"""🚨 BREAKING: {self.state.topic_title}

Here's what nobody is talking about:

{self.state.research_result.key_insights[0] if self.state.research_result else 'Revolutionary insight...'}

But here's the plot twist... 🧵👇

(A thread){platform_specific}"""
        
        # Thread continuation for Twitter
        if self.state.platform == "Twitter":
            thread = f"""

--- THREAD ---

2/ The problem everyone misses:
{self.state.research_result.key_insights[1] if self.state.research_result and len(self.state.research_result.key_insights) > 1 else 'Hidden problem...'}

3/ The solution that changes everything:
{self.state.research_result.key_insights[2] if self.state.research_result and len(self.state.research_result.key_insights) > 2 else 'Game-changing solution...'}

4/ Why this matters NOW:
- {self.state.trend_analysis['timing']['optimal_post_time'] if self.state.trend_analysis else 'Time-sensitive'}
- Competition is sleeping on this
- Algorithm changes favor this approach

5/ What you can do TODAY:
✅ Save this thread
✅ Try it yourself
✅ Share if this blew your mind

Follow for more insights like this 🚀"""
            
            main_content += thread
        
        return main_content
    
    def engagement_optimization_final(self, writing_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize content for maximum engagement
        
        Args:
            writing_output: Output from viral writing
            
        Returns:
            Final engagement-optimized content
        """
        start_time = time.time()
        self.state.current_stage = "engagement_optimization"
        
        logger.info(
            "Starting engagement optimization",
            flow_id=self.state.flow_id
        )
        
        try:
            # Mock engagement optimization
            optimization_result = {
                "optimizations_applied": [
                    "Added power words for emotional impact",
                    "Optimized hook for 3-second attention grab",
                    "Added visual content recommendation",
                    "Included viral sharing triggers",
                    "Optimized posting time recommendation"
                ],
                "platform_specific": {
                    "Twitter": {
                        "thread_optimized": True,
                        "character_count": 278,
                        "hashtag_relevance": 0.9,
                        "reply_bait_included": True
                    }
                },
                "engagement_predictions": {
                    "likes": "5K-10K",
                    "shares": "1K-2K",
                    "comments": "200-500",
                    "reach": "50K-100K"
                },
                "posting_strategy": {
                    "primary_post": "Now",
                    "follow_up": "+2 hours",
                    "peak_window": "Next 6 hours"
                },
                "final_viral_score": 0.85
            }
            
            # Update state
            self.state.engagement_optimization = optimization_result
            self.state.optimization_time = time.time() - start_time
            
            # Calculate total execution time
            total_time = time.time() - self.state.start_time
            
            logger.info(
                "Engagement optimization completed",
                flow_id=self.state.flow_id,
                final_viral_score=optimization_result["final_viral_score"],
                optimizations=len(optimization_result["optimizations_applied"]),
                total_execution_time=total_time
            )
            
            return {
                "optimization": optimization_result,
                "final_draft": self.state.viral_draft,
                "flow_summary": self.get_flow_summary(),
                "ready_to_post": True,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(
                "Engagement optimization failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def get_flow_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive flow execution summary
        
        Returns:
            Viral flow execution details and metrics
        """
        total_time = time.time() - self.state.start_time
        
        return {
            "flow_id": self.state.flow_id,
            "flow_type": "viral_content",
            "topic": self.state.topic_title,
            "platform": self.state.platform,
            "current_stage": self.state.current_stage,
            "viral_details": {
                "viral_score": self.state.viral_score,
                "urgency_level": self.state.urgency_level,
                "target_emotion": self.state.target_emotion,
                "trend_keywords": self.state.trend_keywords,
                "estimated_reach": self.state.estimated_reach
            },
            "metrics": {
                "total_execution_time": total_time,
                "research_time": self.state.research_time,
                "writing_time": self.state.writing_time,
                "optimization_time": self.state.optimization_time,
                "sources_found": len(self.state.research_result.sources) if self.state.research_result else 0
            },
            "quality_indicators": {
                "viral_potential": "high" if self.state.viral_score > 0.8 else "medium",
                "timing_optimal": self.state.urgency_level == "high",
                "platform_optimized": True,
                "ready_to_post": True
            }
        }