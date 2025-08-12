"""
Standard Content Flow

Standard content flow following proven editorial process:
- Research → Audience → Writing → Style → Quality
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
from ..agents.content_analysis_agent import ContentAnalysisAgent
from ..tasks.research_task import ResearchTask
from ..tasks.content_analysis_task import ContentAnalysisTask

# Configure structured logging
logger = structlog.get_logger(__name__)


class StandardFlowState(BaseModel):
    """State management for Standard Content Flow"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"standard_flow_{int(time.time())}")
    
    # Input data
    topic_title: str = ""
    platform: str = "Blog"
    content_type: str = "standard"
    key_themes: list[str] = Field(default_factory=list)
    editorial_recommendations: str = ""
    
    # Flow state
    current_stage: str = "initialized"
    flow_path: str = "standard"
    
    # Results
    research_result: Optional[ResearchResult] = None
    audience_analysis: Optional[Dict[str, Any]] = None
    draft_content: Optional[DraftContent] = None
    style_optimization: Optional[Dict[str, Any]] = None
    quality_review: Optional[Dict[str, Any]] = None
    
    # Metrics
    start_time: float = Field(default_factory=time.time)
    research_time: float = 0.0
    audience_time: float = 0.0
    writing_time: float = 0.0
    style_time: float = 0.0
    quality_time: float = 0.0


class StandardContentFlow(BaseFlow):
    """
    Standard Content Flow following proven editorial process:
    
    Flow stages:
    1. Comprehensive research
    2. Audience analysis
    3. Structured writing
    4. Style optimization
    5. Quality review
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Standard Content Flow
        
        Args:
            config: Flow configuration including:
                - verbose: Enable detailed logging
                - min_sources: Minimum sources required
                - quality_threshold: Minimum quality score
        """
        super().__init__()
        # Ensure state exists without CrewAI runtime
        try:
            self.state  # type: ignore[attr-defined]
        except Exception:
            self.state = StandardFlowState()
        self.config = config or {}
        
        # Default configuration
        self.config.setdefault('verbose', True)
        self.config.setdefault('min_sources', 3)
        self.config.setdefault('quality_threshold', 0.8)
        
        # Initialize standard agents
        self.research_agent = ResearchAgent(config={
            'verbose': self.config.get('verbose', True),
            'search_depth': 'standard',  # Balanced research depth
            'verify_sources': True,
            'min_sources': self.config.get('min_sources', 3)
        })
        
        logger.info(
            "StandardContentFlow initialized",
            flow_id=self.state.flow_id,
            config=self.config
        )
    
    def comprehensive_research(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point: Conduct comprehensive research
        
        Args:
            inputs: Flow inputs including topic, themes
            
        Returns:
            Comprehensive research results
        """
        start_time = time.time()
        
        # Update state with inputs
        self.state.topic_title = inputs.get('topic_title', '')
        self.state.platform = inputs.get('platform', 'Blog')
        self.state.key_themes = inputs.get('key_themes', [])
        self.state.editorial_recommendations = inputs.get('editorial_recommendations', '')
        self.state.current_stage = "research"
        
        logger.info(
            "Starting comprehensive research",
            flow_id=self.state.flow_id,
            topic=self.state.topic_title,
            platform=self.state.platform
        )
        
        try:
            # Create research agent and task
            agent = self.research_agent.create_agent()
            task_creator = ResearchTask(config={
                'min_sources': self.config.get('min_sources', 3),
                'verify_facts': True,
                'require_sources': True,
                'search_depth': 'standard',
                'timeout': 300  # 5 minutes for standard research
            })
            
            # Standard research inputs
            research_inputs = {
                'topic_title': self.state.topic_title,
                'content_type': 'standard_research',
                'platform': self.state.platform,
                'key_themes': self.state.key_themes + [
                    "comprehensive overview",
                    "key concepts",
                    "practical applications",
                    "expert opinions"
                ],
                'editorial_recommendations': self.state.editorial_recommendations,
                'kb_insights': []
            }
            
            # Create and execute task (mock for testing)
            task = task_creator.create_task(agent, research_inputs)
            
            # Mock standard research result
            research_result = ResearchResult(
                sources=[
                    {
                        "url": "https://expert.example.com/analysis",
                        "title": "Expert Analysis of the Topic",
                        "author": "Industry Expert",
                        "date": "2025-01",
                        "type": "expert_analysis",
                        "credibility_score": "0.9",
                        "key_points": "Comprehensive overview, Key insights, Future trends"
                    },
                    {
                        "url": "https://research.example.com/study",
                        "title": "Recent Research Study",
                        "author": "Research Institute",
                        "date": "2024-12",
                        "type": "research_paper",
                        "credibility_score": "0.95",
                        "key_points": "Data-driven insights, Statistical analysis, Methodology"
                    },
                    {
                        "url": "https://practical.example.com/guide",
                        "title": "Practical Implementation Guide",
                        "author": "Practitioner",
                        "date": "2024-11",
                        "type": "practical_guide",
                        "credibility_score": "0.85",
                        "key_points": "Step-by-step approach, Real-world examples, Common pitfalls"
                    }
                ],
                summary="""Comprehensive research reveals:
                
                1. Current State: The field is rapidly evolving with new developments
                2. Key Concepts: Understanding fundamental principles is crucial
                3. Practical Applications: Real-world implementations show promising results
                4. Expert Consensus: Industry leaders agree on key directions
                5. Future Outlook: Significant growth and innovation expected""",
                key_insights=[
                    "Foundation understanding is critical for proper implementation",
                    "Balance between theory and practice yields best results",
                    "Community feedback drives continuous improvement",
                    "Measurable outcomes validate approach effectiveness",
                    "Scalability considerations from the start"
                ],
                data_points=[
                    {
                        "statistic": "85% adoption rate among early adopters",
                        "source": "Industry survey",
                        "context": "Market acceptance",
                        "verification_status": "Verified"
                    }
                ],
                methodology="Standard comprehensive research with source verification"
            )
            
            # Update state
            self.state.research_result = research_result
            self.state.research_time = time.time() - start_time
            
            # Update agent metrics
            self.research_agent.update_metrics(
                processing_time=self.state.research_time,
                sources=len(research_result.sources),
                kb_queries=5  # Mock value
            )
            
            logger.info(
                "Comprehensive research completed",
                flow_id=self.state.flow_id,
                sources_found=len(research_result.sources),
                insights=len(research_result.key_insights),
                duration=self.state.research_time
            )
            
            return {
                "research": research_result,
                "quality": "comprehensive",
                "next_stage": "audience_analysis"
            }
            
        except Exception as e:
            logger.error(
                "Comprehensive research failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def audience_analysis(self, research_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze target audience based on research
        
        Args:
            research_output: Output from comprehensive research
            
        Returns:
            Audience analysis results
        """
        start_time = time.time()
        self.state.current_stage = "audience_analysis"
        
        logger.info(
            "Starting audience analysis",
            flow_id=self.state.flow_id,
            platform=self.state.platform
        )
        
        try:
            # Mock audience analysis
            audience_analysis = {
                "primary_audience": {
                    "profile": "Tech-savvy professionals",
                    "expertise_level": "Intermediate to Advanced",
                    "interests": ["Innovation", "Practical solutions", "ROI"],
                    "pain_points": ["Implementation complexity", "Resource constraints", "Change management"]
                },
                "secondary_audience": {
                    "profile": "Decision makers and stakeholders",
                    "expertise_level": "Business-focused",
                    "interests": ["Business value", "Risk mitigation", "Success stories"]
                },
                "content_preferences": {
                    "format": "Structured with clear sections",
                    "depth": "Comprehensive but accessible",
                    "examples": "Real-world case studies preferred",
                    "visuals": "Diagrams and infographics helpful"
                },
                "engagement_patterns": {
                    "best_time": "Weekday mornings",
                    "reading_time": "10-15 minutes",
                    "sharing_likelihood": "High with practical value"
                }
            }
            
            # Update state
            self.state.audience_analysis = audience_analysis
            self.state.audience_time = time.time() - start_time
            
            logger.info(
                "Audience analysis completed",
                flow_id=self.state.flow_id,
                primary_audience=audience_analysis["primary_audience"]["profile"],
                duration=self.state.audience_time
            )
            
            return {
                "audience": audience_analysis,
                "next_stage": "structured_writing"
            }
            
        except Exception as e:
            logger.error(
                "Audience analysis failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def structured_writing(self, audience_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create structured content based on audience needs
        
        Args:
            audience_output: Output from audience analysis
            
        Returns:
            Structured draft content
        """
        start_time = time.time()
        self.state.current_stage = "writing"
        
        logger.info(
            "Starting structured writing",
            flow_id=self.state.flow_id
        )
        
        try:
            # Create structured draft
            draft = DraftContent(
                title=f"Complete Guide: {self.state.topic_title}",
                draft=self._generate_standard_draft(),
                word_count=1500,  # Standard length
                structure_type="comprehensive_guide",
                key_sections=[
                    "Executive Summary",
                    "Introduction",
                    "Key Concepts",
                    "Implementation Guide",
                    "Best Practices",
                    "Common Challenges",
                    "Success Metrics",
                    "Conclusion"
                ],
                non_obvious_insights=[
                    "Balance theory with practical application",
                    "Start small and scale gradually",
                    "Measure outcomes consistently",
                    "Iterate based on feedback"
                ]
            )
            
            # Update state
            self.state.draft_content = draft
            self.state.writing_time = time.time() - start_time
            
            logger.info(
                "Structured writing completed",
                flow_id=self.state.flow_id,
                word_count=draft.word_count,
                sections=len(draft.key_sections),
                duration=self.state.writing_time
            )
            
            return {
                "draft": draft,
                "structure": "comprehensive",
                "next_stage": "style_optimization"
            }
            
        except Exception as e:
            logger.error(
                "Structured writing failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def style_optimization(self, writing_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize content style for target audience
        
        Args:
            writing_output: Output from structured writing
            
        Returns:
            Style-optimized content
        """
        start_time = time.time()
        self.state.current_stage = "style_optimization"
        
        logger.info(
            "Starting style optimization",
            flow_id=self.state.flow_id
        )
        
        try:
            # Mock style optimization
            style_optimization = {
                "readability_score": 0.85,
                "tone": "Professional yet accessible",
                "improvements_made": [
                    "Simplified complex sentences",
                    "Added transition phrases",
                    "Enhanced clarity of key points",
                    "Improved flow between sections",
                    "Optimized for scanning"
                ],
                "platform_optimization": {
                    self.state.platform: {
                        "formatting": "Proper headers and bullet points",
                        "length": "Optimal for platform",
                        "engagement_elements": "Questions and CTAs added"
                    }
                }
            }
            
            # Update state
            self.state.style_optimization = style_optimization
            self.state.style_time = time.time() - start_time
            
            logger.info(
                "Style optimization completed",
                flow_id=self.state.flow_id,
                readability=style_optimization["readability_score"],
                improvements=len(style_optimization["improvements_made"]),
                duration=self.state.style_time
            )
            
            return {
                "style": style_optimization,
                "next_stage": "quality_review"
            }
            
        except Exception as e:
            logger.error(
                "Style optimization failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def quality_review_final(self, style_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Final quality review and polish
        
        Args:
            style_output: Output from style optimization
            
        Returns:
            Final quality-reviewed content
        """
        start_time = time.time()
        self.state.current_stage = "quality_review"
        
        logger.info(
            "Starting final quality review",
            flow_id=self.state.flow_id
        )
        
        try:
            # Mock quality review
            quality_review = {
                "overall_quality_score": 0.88,
                "criteria_scores": {
                    "accuracy": 0.9,
                    "completeness": 0.85,
                    "clarity": 0.9,
                    "engagement": 0.85,
                    "value": 0.9
                },
                "final_checks": {
                    "fact_verification": True,
                    "source_validation": True,
                    "grammar_spelling": True,
                    "formatting": True,
                    "platform_requirements": True
                },
                "recommendations": [
                    "Consider adding more visuals",
                    "Include additional case study",
                    "Update with latest statistics"
                ],
                "approval_status": "ready_to_publish"
            }
            
            # Update state
            self.state.quality_review = quality_review
            self.state.quality_time = time.time() - start_time
            
            # Calculate total execution time
            total_time = time.time() - self.state.start_time
            
            logger.info(
                "Quality review completed",
                flow_id=self.state.flow_id,
                quality_score=quality_review["overall_quality_score"],
                approval_status=quality_review["approval_status"],
                total_execution_time=total_time
            )
            
            return {
                "review": quality_review,
                "final_draft": self.state.draft_content,
                "flow_summary": self.get_flow_summary(),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(
                "Quality review failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _generate_standard_draft(self) -> str:
        """Generate standard content draft"""
        
        insights = self.state.research_result.key_insights if self.state.research_result else []
        
        draft = f"""# Complete Guide: {self.state.topic_title}

## Executive Summary

This comprehensive guide explores {self.state.topic_title}, providing actionable insights 
and practical strategies for implementation. Based on extensive research and expert analysis, 
this guide offers a balanced approach suitable for {self.state.audience_analysis['primary_audience']['profile'] if self.state.audience_analysis else 'professionals'}.

## Introduction

{self.state.editorial_recommendations}

In today's rapidly evolving landscape, understanding {self.state.topic_title} has become 
crucial for success. This guide provides a structured approach to mastering the key concepts 
and implementing effective strategies.

## Key Concepts

{chr(10).join([f'### {i+1}. {insight}' + chr(10) + 'Detailed explanation and context...' + chr(10) for i, insight in enumerate(insights[:3])])}

## Implementation Guide

### Phase 1: Foundation
- Assess current state
- Define objectives
- Gather resources

### Phase 2: Execution
- Implement core components
- Monitor progress
- Iterate based on feedback

### Phase 3: Optimization
- Analyze results
- Scale successful elements
- Continuous improvement

## Best Practices

1. **Start with Clear Goals**: Define measurable objectives
2. **Iterate Frequently**: Regular feedback loops ensure success
3. **Document Everything**: Maintain comprehensive records
4. **Engage Stakeholders**: Keep all parties informed and involved

## Common Challenges and Solutions

### Challenge 1: Resource Constraints
**Solution**: Prioritize high-impact activities and phase implementation

### Challenge 2: Resistance to Change
**Solution**: Demonstrate quick wins and communicate benefits clearly

### Challenge 3: Technical Complexity
**Solution**: Break down into manageable components and provide training

## Success Metrics

Track these key performance indicators:
- Implementation progress (% complete)
- User adoption rate
- Performance improvements
- ROI measurements

## Conclusion

Success with {self.state.topic_title} requires a balanced approach combining strategic 
planning with practical execution. By following this guide and adapting strategies to 
your specific context, you can achieve sustainable results.

### Next Steps:
1. Review your current situation
2. Select applicable strategies
3. Create an implementation timeline
4. Begin with pilot projects
5. Scale based on results

## Resources and References

{chr(10).join([f"- [{source['title']}]({source['url']})" for source in (self.state.research_result.sources if self.state.research_result else [])])}
"""
        
        return draft
    
    def get_flow_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive flow execution summary
        
        Returns:
            Standard flow execution details and metrics
        """
        total_time = time.time() - self.state.start_time
        
        return {
            "flow_id": self.state.flow_id,
            "flow_type": "standard_content",
            "topic": self.state.topic_title,
            "platform": self.state.platform,
            "current_stage": self.state.current_stage,
            "metrics": {
                "total_execution_time": total_time,
                "research_time": self.state.research_time,
                "audience_time": self.state.audience_time,
                "writing_time": self.state.writing_time,
                "style_time": self.state.style_time,
                "quality_time": self.state.quality_time,
                "sources_found": len(self.state.research_result.sources) if self.state.research_result else 0
            },
            "quality_indicators": {
                "research_quality": "comprehensive",
                "audience_alignment": True,
                "content_structure": "optimized",
                "quality_score": self.state.quality_review["overall_quality_score"] if self.state.quality_review else 0
            }
        }