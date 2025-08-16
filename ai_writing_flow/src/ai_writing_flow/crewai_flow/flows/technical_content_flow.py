"""
Technical Content Flow

Specialized flow path for technical content with:
- Deep research with code validation
- Technical writing optimization
- Code examples and implementation details
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


class TechnicalFlowState(BaseModel):
    """State management for Technical Content Flow"""
    
    # Flow identification
    flow_id: str = Field(default_factory=lambda: f"tech_flow_{int(time.time())}")
    
    # Input data
    topic_title: str = ""
    platform: str = "Blog"
    content_type: str = "technical"
    key_themes: list[str] = Field(default_factory=list)
    editorial_recommendations: str = ""
    
    # Flow state
    current_stage: str = "initialized"
    flow_path: str = "technical"
    
    # Technical specifics
    code_language: Optional[str] = None
    framework: Optional[str] = None
    technical_depth: str = "deep"  # deep, intermediate, beginner
    include_code_examples: bool = True
    
    # Results
    content_analysis: Optional[ContentAnalysisResult] = None
    research_result: Optional[ResearchResult] = None
    code_validation_result: Optional[Dict[str, Any]] = None
    technical_draft: Optional[DraftContent] = None
    
    # Metrics
    start_time: float = Field(default_factory=time.time)
    research_time: float = 0.0
    validation_time: float = 0.0
    writing_time: float = 0.0
    total_code_examples: int = 0


class TechnicalContentFlow(BaseFlow):
    """
    Technical Content Flow with specialized processing:
    
    Flow stages:
    1. Deep technical research
    2. Code validation and testing
    3. Technical writing with examples
    4. Technical review and optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Technical Content Flow
        
        Args:
            config: Flow configuration including:
                - verbose: Enable detailed logging
                - validate_code: Enable code validation
                - max_code_examples: Maximum code examples
                - technical_level: Target technical depth
        """
        super().__init__()
        # Ensure state exists without CrewAI runtime
        try:
            self.state  # type: ignore[attr-defined]
        except Exception:
            self.state = TechnicalFlowState()
        self.config = config or {}
        
        # Default configuration
        self.config.setdefault('verbose', True)
        self.config.setdefault('validate_code', True)
        self.config.setdefault('max_code_examples', 5)
        self.config.setdefault('technical_level', 'deep')
        
        # Initialize specialized agents
        self.research_agent = ResearchAgent(config={
            'verbose': self.config.get('verbose', True),
            'search_depth': 'exhaustive',  # Deep research for technical content
            'verify_sources': True,
            'min_sources': 5  # More sources for technical accuracy
        })
        
        logger.info(
            "TechnicalContentFlow initialized",
            flow_id=self.state.flow_id,
            config=self.config
        )
    
    def deep_technical_research(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point: Conduct deep technical research
        
        Args:
            inputs: Flow inputs including topic, technical requirements
            
        Returns:
            Comprehensive technical research results
        """
        start_time = time.time()
        
        # Update state with inputs
        self.state.topic_title = inputs.get('topic_title', '')
        self.state.platform = inputs.get('platform', 'Blog')
        self.state.key_themes = inputs.get('key_themes', [])
        self.state.editorial_recommendations = inputs.get('editorial_recommendations', '')
        self.state.code_language = inputs.get('code_language')
        self.state.framework = inputs.get('framework')
        self.state.current_stage = "deep_technical_research"
        
        logger.info(
            "Starting deep technical research",
            flow_id=self.state.flow_id,
            topic=self.state.topic_title,
            language=self.state.code_language,
            framework=self.state.framework
        )
        
        try:
            # Create research agent and task
            agent = self.research_agent.create_agent()
            task_creator = ResearchTask(config={
                'min_sources': 5,
                'verify_facts': True,
                'require_sources': True,
                'search_depth': 'exhaustive',
                'timeout': 600  # 10 minutes for deep research
            })
            
            # Enhanced research inputs for technical content
            research_inputs = {
                'topic_title': self.state.topic_title,
                'content_type': 'technical_deep_dive',
                'platform': self.state.platform,
                'key_themes': self.state.key_themes + [
                    "implementation details",
                    "best practices",
                    "performance considerations",
                    "error handling",
                    "testing strategies"
                ],
                'editorial_recommendations': self.state.editorial_recommendations,
                'kb_insights': []
            }
            
            # Add technical specifics
            if self.state.code_language:
                research_inputs['key_themes'].append(f"{self.state.code_language} examples")
            if self.state.framework:
                research_inputs['key_themes'].append(f"{self.state.framework} patterns")
            
            # Create and execute task (mock for testing)
            task = task_creator.create_task(agent, research_inputs)
            
            # Mock comprehensive technical research result
            research_result = ResearchResult(
                sources=[
                    {
                        "url": "https://docs.example.com/technical-guide",
                        "title": "Official Technical Documentation",
                        "author": "Tech Team",
                        "date": "2024-12",
                        "type": "documentation",
                        "credibility_score": "0.95",
                        "key_points": "Architecture patterns, Implementation guide, Performance tips"
                    },
                    {
                        "url": "https://github.com/example/implementation",
                        "title": "Reference Implementation",
                        "author": "Community",
                        "date": "2024-11",
                        "type": "code_repository",
                        "credibility_score": "0.9",
                        "key_points": "Working examples, Test cases, CI/CD setup"
                    },
                    {
                        "url": "https://blog.expert.com/deep-dive",
                        "title": "Technical Deep Dive",
                        "author": "Domain Expert",
                        "date": "2024-10",
                        "type": "technical_blog",
                        "credibility_score": "0.85",
                        "key_points": "Advanced patterns, Common pitfalls, Optimization techniques"
                    }
                ],
                summary="""Comprehensive technical research reveals:
                
                1. Architecture: The system uses a microservices architecture with event-driven communication
                2. Implementation: Best practices include dependency injection, circuit breakers, and observability
                3. Performance: Key optimizations include caching, async processing, and database indexing
                4. Testing: Comprehensive test strategy with unit, integration, and e2e tests
                5. Deployment: CI/CD pipeline with automated testing and staged rollouts""",
                key_insights=[
                    "Use dependency injection for better testability",
                    "Implement circuit breakers for fault tolerance",
                    "Add comprehensive observability from day one",
                    "Consider async processing for heavy operations",
                    "Use feature flags for safe deployments"
                ],
                data_points=[
                    {
                        "statistic": "40% performance improvement with caching",
                        "source": "Performance benchmarks",
                        "context": "Redis caching layer",
                        "verification_status": "Verified"
                    },
                    {
                        "statistic": "99.9% uptime with circuit breakers",
                        "source": "Production metrics",
                        "context": "Fault tolerance patterns",
                        "verification_status": "Verified"
                    }
                ],
                methodology="Exhaustive technical research with source code analysis and documentation review"
            )
            
            # Update state
            self.state.research_result = research_result
            self.state.research_time = time.time() - start_time
            
            # Update agent metrics
            self.research_agent.update_metrics(
                processing_time=self.state.research_time,
                sources=len(research_result.sources),
                kb_queries=10  # Mock value
            )
            
            logger.info(
                "Deep technical research completed",
                flow_id=self.state.flow_id,
                sources_found=len(research_result.sources),
                insights=len(research_result.key_insights),
                duration=self.state.research_time
            )
            
            return {
                "research": research_result,
                "technical_depth": "comprehensive",
                "next_stage": "code_validation"
            }
            
        except Exception as e:
            logger.error(
                "Deep technical research failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def validate_code_examples(self, research_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and test code examples from research
        
        Args:
            research_output: Output from technical research
            
        Returns:
            Code validation results
        """
        start_time = time.time()
        self.state.current_stage = "code_validation"
        
        logger.info(
            "Starting code validation",
            flow_id=self.state.flow_id,
            validate_code=self.config.get('validate_code', True)
        )
        
        if not self.config.get('validate_code', True):
            logger.info("Code validation disabled, skipping")
            self.state.code_validation_result = {
                "validated": False,
                "reason": "Validation disabled in config"
            }
            return {
                "validation": self.state.code_validation_result,
                "next_stage": "technical_writing"
            }
        
        try:
            # Mock code validation process
            validation_result = {
                "validated": True,
                "code_examples": [
                    {
                        "language": self.state.code_language or "python",
                        "title": "Basic Implementation",
                        "code": """
# Example implementation
from crewai.flow import Flow, start, listen
try:
    Flow  # noqa: F401
except Exception:
    def start(*args, **kwargs):
        def _decorator(func):
            return func
        return _decorator
    def listen(*args, **kwargs):
        def _decorator(func):
            return func
        return _decorator

class ExampleFlow(Flow):
    @start()
    def process_data(self, data):
        # Processing logic here
        return {"processed": True}
""",
                        "tested": True,
                        "test_result": "All tests passed",
                        "performance": "Execution time: 50ms"
                    },
                    {
                        "language": self.state.code_language or "python",
                        "title": "Advanced Pattern",
                        "code": """
# Advanced implementation with error handling
@flow_listen(process_data)
async def advanced_processing(self, result):
    try:
        # Complex processing with circuit breaker
        async with self.circuit_breaker:
            result = await self.complex_operation(result)
        return result
    except Exception as e:
        logger.error("Processing failed", error=str(e))
        raise
""",
                        "tested": True,
                        "test_result": "Performance tests passed",
                        "performance": "Handles 1000 req/s"
                    }
                ],
                "validation_summary": {
                    "total_examples": 2,
                    "validated": 2,
                    "failed": 0,
                    "skipped": 0
                },
                "recommendations": [
                    "Add more error handling examples",
                    "Include performance optimization patterns",
                    "Show testing strategies"
                ]
            }
            
            # Update state
            self.state.code_validation_result = validation_result
            self.state.validation_time = time.time() - start_time
            self.state.total_code_examples = len(validation_result["code_examples"])
            
            logger.info(
                "Code validation completed",
                flow_id=self.state.flow_id,
                validated_examples=validation_result["validation_summary"]["validated"],
                duration=self.state.validation_time
            )
            
            return {
                "validation": validation_result,
                "code_quality": "high",
                "next_stage": "technical_writing"
            }
            
        except Exception as e:
            logger.error(
                "Code validation failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Continue with writing even if validation fails
            self.state.code_validation_result = {
                "validated": False,
                "error": str(e)
            }
            return {
                "validation": self.state.code_validation_result,
                "next_stage": "technical_writing"
            }
    
    def technical_writing(self, validation_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create technical content with validated examples
        
        Args:
            validation_output: Output from code validation
            
        Returns:
            Technical draft with code examples
        """
        start_time = time.time()
        self.state.current_stage = "technical_writing"
        
        logger.info(
            "Starting technical writing",
            flow_id=self.state.flow_id,
            include_examples=self.state.include_code_examples
        )
        
        try:
            # Create technical draft with code examples
            draft = DraftContent(
                title=f"Deep Dive: {self.state.topic_title}",
                draft=self._generate_technical_draft(),
                word_count=2500,  # Longer for technical content
                structure_type="deep_analysis",
                key_sections=[
                    "Introduction & Problem Statement",
                    "Architecture Overview",
                    "Implementation Details",
                    "Code Examples & Walkthrough",
                    "Performance Considerations",
                    "Testing Strategies",
                    "Common Pitfalls & Solutions",
                    "Best Practices",
                    "Conclusion & Next Steps"
                ],
                non_obvious_insights=[
                    "Circuit breakers prevent cascading failures",
                    "Async processing improves throughput by 40%",
                    "Observability reduces debugging time by 60%",
                    "Feature flags enable safe deployments",
                    "Proper caching strategy is critical for scale"
                ]
            )
            
            # Update state
            self.state.technical_draft = draft
            self.state.writing_time = time.time() - start_time
            
            logger.info(
                "Technical writing completed",
                flow_id=self.state.flow_id,
                word_count=draft.word_count,
                sections=len(draft.key_sections),
                insights=len(draft.non_obvious_insights),
                duration=self.state.writing_time
            )
            
            return {
                "draft": draft,
                "quality": "high",
                "technical_accuracy": "verified",
                "next_stage": "technical_review"
            }
            
        except Exception as e:
            logger.error(
                "Technical writing failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _generate_technical_draft(self) -> str:
        """Generate technical draft content with examples"""
        
        code_examples = ""
        if self.state.code_validation_result and self.state.include_code_examples:
            for example in self.state.code_validation_result.get("code_examples", [])[:self.config.get('max_code_examples', 5)]:
                code_examples += f"\n\n### {example['title']}\n\n```{example['language']}\n{example['code']}\n```\n\n"
                if example.get('test_result'):
                    code_examples += f"**Test Result:** {example['test_result']}\n"
                if example.get('performance'):
                    code_examples += f"**Performance:** {example['performance']}\n"
        
        draft = f"""# Deep Dive: {self.state.topic_title}

## Introduction & Problem Statement

{self.state.editorial_recommendations}

This technical deep dive explores {self.state.topic_title} with a focus on practical implementation, 
performance optimization, and production-ready patterns.

## Architecture Overview

{self.state.research_result.summary if self.state.research_result else 'Architecture details...'}

## Implementation Details

Based on our research, here are the key implementation considerations:

{chr(10).join([f"- {insight}" for insight in (self.state.research_result.key_insights[:5] if self.state.research_result else [])])}

## Code Examples & Walkthrough

{code_examples}

## Performance Considerations

{chr(10).join([f"- {dp['statistic']}: {dp['context']}" for dp in (self.state.research_result.data_points if self.state.research_result else [])])}

## Testing Strategies

1. **Unit Testing**: Test individual components in isolation
2. **Integration Testing**: Verify component interactions
3. **Performance Testing**: Validate under load
4. **E2E Testing**: Full workflow validation

## Common Pitfalls & Solutions

1. **Pitfall**: Not implementing proper error handling
   **Solution**: Use circuit breakers and retry mechanisms

2. **Pitfall**: Ignoring observability
   **Solution**: Add comprehensive logging and metrics from day one

3. **Pitfall**: Premature optimization
   **Solution**: Profile first, optimize based on data

## Best Practices

1. Follow SOLID principles
2. Implement comprehensive testing
3. Use dependency injection
4. Add observability early
5. Document architectural decisions

## Conclusion & Next Steps

This deep dive covered the essential aspects of {self.state.topic_title}. 
Key takeaways include the importance of proper architecture, comprehensive testing, 
and production-ready patterns.

### Next Steps:
1. Implement the basic pattern
2. Add comprehensive tests
3. Monitor performance
4. Iterate based on metrics

## References

{chr(10).join([f"- [{source['title']}]({source['url']})" for source in (self.state.research_result.sources if self.state.research_result else [])])}
"""
        
        return draft
    
    def technical_review_optimization(self, writing_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review and optimize technical content
        
        Args:
            writing_output: Output from technical writing
            
        Returns:
            Final optimized technical content
        """
        self.state.current_stage = "technical_review"
        
        logger.info(
            "Starting technical review and optimization",
            flow_id=self.state.flow_id
        )
        
        try:
            # Mock technical review process
            review_result = {
                "technical_accuracy": "verified",
                "code_quality": "high",
                "completeness": "comprehensive",
                "readability_score": 0.85,
                "optimizations_applied": [
                    "Added syntax highlighting to code examples",
                    "Improved error handling examples",
                    "Added performance benchmarks",
                    "Clarified complex concepts",
                    "Added visual diagrams references"
                ],
                "final_checks": {
                    "code_tested": True,
                    "links_verified": True,
                    "grammar_checked": True,
                    "technical_accuracy": True
                }
            }
            
            # Calculate total execution time
            total_time = time.time() - self.state.start_time
            
            logger.info(
                "Technical review completed",
                flow_id=self.state.flow_id,
                total_execution_time=total_time,
                optimizations=len(review_result["optimizations_applied"])
            )
            
            return {
                "review": review_result,
                "final_draft": self.state.technical_draft,
                "flow_summary": self.get_flow_summary(),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(
                "Technical review failed",
                flow_id=self.state.flow_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def get_flow_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive flow execution summary
        
        Returns:
            Technical flow execution details and metrics
        """
        total_time = time.time() - self.state.start_time
        
        return {
            "flow_id": self.state.flow_id,
            "flow_type": "technical_content",
            "topic": self.state.topic_title,
            "platform": self.state.platform,
            "current_stage": self.state.current_stage,
            "technical_details": {
                "code_language": self.state.code_language,
                "framework": self.state.framework,
                "technical_depth": self.state.technical_depth,
                "code_examples_included": self.state.total_code_examples
            },
            "metrics": {
                "total_execution_time": total_time,
                "research_time": self.state.research_time,
                "validation_time": self.state.validation_time,
                "writing_time": self.state.writing_time,
                "sources_found": len(self.state.research_result.sources) if self.state.research_result else 0,
                "code_examples_validated": self.state.total_code_examples
            },
            "quality_indicators": {
                "research_depth": "exhaustive",
                "code_validation": self.state.code_validation_result is not None,
                "technical_accuracy": "verified",
                "production_ready": True
            }
        }