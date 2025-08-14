"""
Linear Draft Generation Execution - replaces listen("generate_draft") pattern

This module implements draft generation stage execution without circular dependencies,
with human review checkpoint and draft versioning.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os
from pathlib import Path

from ai_writing_flow.models.flow_stage import FlowStage
from ai_writing_flow.managers.stage_manager import StageManager
from ai_writing_flow.utils.circuit_breaker import StageCircuitBreaker, CircuitBreakerError
from ai_writing_flow.flow_inputs import FlowPathConfig
# Moved StandardContentFlow import to function level to avoid circular import

logger = logging.getLogger(__name__)


class DraftGenerationResult:
    """Draft generation execution result"""
    
    def __init__(self):
        self.draft_content: str = ""
        self.version_number: int = 1
        self.word_count: int = 0
        self.platform_optimized: bool = False
        self.audience_targeted: bool = False
        self.generation_metadata: Dict[str, Any] = {}
        self.completion_time: Optional[datetime] = None
        self.fallback_used: bool = False
        self.requires_human_review: bool = True


class HumanReviewCheckpoint:
    """Human review checkpoint data"""
    
    def __init__(self):
        self.review_required: bool = True
        self.auto_approve_eligible: bool = False
        self.quality_score: float = 0.0
        self.review_criteria: List[str] = []
        self.checkpoint_time: Optional[datetime] = None


class LinearDraftExecutor:
    """
    Linear draft generation execution replacing legacy listen("generate_draft") pattern
    
    Features:
    - No circular dependencies or loops
    - Clean retry logic with version tracking
    - Human review checkpoint integration
    - Draft versioning system
    - Circuit breaker protection
    """
    
    def __init__(
        self,
        stage_manager: StageManager,
        circuit_breaker: StageCircuitBreaker,
        config: FlowPathConfig
    ):
        self.stage_manager = stage_manager
        self.circuit_breaker = circuit_breaker
        self.config = config
        self._draft_versions: Dict[str, List[str]] = {}
        self._review_checkpoints: Dict[str, HumanReviewCheckpoint] = {}
    
    def should_execute_draft_generation(self, writing_state) -> bool:
        """
        Determine if draft generation should be executed
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            True if draft generation should be executed
        """
        
        # Always execute if no current draft exists
        if not writing_state.current_draft:
            logger.info("📝 Draft generation will be executed - no existing draft")
            return True
        
        # Check if we need a new version due to changes
        if self._requires_new_draft_version(writing_state):
            logger.info("📝 Draft generation will be executed - new version needed")
            return True
        
        logger.info("⏭️ Draft generation not needed - current draft exists")
        return False
    
    def execute_draft_generation(self, writing_state) -> DraftGenerationResult:
        """
        Execute draft generation with retry logic and versioning
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            DraftGenerationResult with generated content
        """
        
        logger.info("📝 Executing draft generation...")
        
        try:
            # Execute with circuit breaker protection
            result = self.circuit_breaker.call(
                self._execute_draft_core,
                writing_state=writing_state
            )
            
            # Version the draft
            self._version_draft(writing_state, result)
            
            # Update state with results
            self._update_writing_state(writing_state, result)
            
            # Create human review checkpoint
            checkpoint = self._create_review_checkpoint(writing_state, result)
            self._store_review_checkpoint(writing_state, checkpoint)
            
            # Mark completion
            self._mark_draft_completed(writing_state, result)
            
            logger.info("✅ Draft generation completed successfully")
            return result
            
        except CircuitBreakerError as e:
            logger.error(f"🔌 Draft generation circuit breaker open: {e}")
            
            # Use fallback
            fallback_result = self._draft_fallback(writing_state, str(e))
            self._version_draft(writing_state, fallback_result)
            self._update_writing_state(writing_state, fallback_result)
            self._mark_draft_completed(writing_state, fallback_result)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Draft generation failed: {str(e)}", exc_info=True)
            
            # Use fallback
            fallback_result = self._draft_fallback(writing_state, str(e))
            self._version_draft(writing_state, fallback_result)
            self._update_writing_state(writing_state, fallback_result)
            self._mark_draft_completed(writing_state, fallback_result)
            
            return fallback_result
    
    def _execute_draft_core(self, writing_state) -> DraftGenerationResult:
        """
        Core draft generation logic (mocked for now)
        
        Args:
            writing_state: Current WritingFlowState
            
        Returns:
            DraftGenerationResult with generated content
        """
        
        result = DraftGenerationResult()
        
        logger.info(f"📝 Generating draft for: {writing_state.topic_title}")
        logger.info(f"🎯 Platform: {writing_state.platform}")
        logger.info(f"👥 Target depth: {writing_state.target_depth_level}")
        
        # Mock draft generation (replace with actual crew execution)
        
        # Generate content based on platform
        if writing_state.platform == "Twitter":
            result.draft_content = self._generate_twitter_draft(writing_state)
        elif writing_state.platform == "LinkedIn":
            result.draft_content = self._generate_linkedin_draft(writing_state)
        elif writing_state.platform == "Blog":
            result.draft_content = self._generate_blog_draft(writing_state)
        else:
            result.draft_content = self._generate_default_draft(writing_state)
        
        # Calculate metadata
        result.word_count = len(result.draft_content.split())
        result.platform_optimized = True
        result.audience_targeted = bool(writing_state.audience_scores)
        
        result.generation_metadata = {
            "research_sources_used": len(writing_state.research_sources),
            "audience_scores": writing_state.audience_scores,
            "depth_level": writing_state.target_depth_level,
            "platform": writing_state.platform,
            "viral_score": writing_state.viral_score
        }
        
        result.completion_time = datetime.now(timezone.utc)
        result.requires_human_review = self._determine_review_requirement(writing_state, result)
        
        logger.info(f"📊 Draft generated: {result.word_count} words, review required: {result.requires_human_review}")
        
        return result
    
    def _generate_twitter_draft(self, writing_state) -> str:
        """Generate Twitter-optimized draft using source content as input"""
        
        # Read source content to use as input for AI processing
        source_content = self._read_source_content(writing_state)
        
        if source_content:
            logger.info("📄 Processing original source content with CrewAI StandardContentFlow for Twitter draft")
            return self._process_with_crewai_flow(source_content, writing_state)
        
        # Fallback to template generation if no source content
        logger.info("📝 Generating template Twitter draft")
        
        # Twitter format: concise, thread-friendly
        draft = f"🧵 Thread about {writing_state.topic_title}\n\n"
        draft += f"1/ {writing_state.topic_title} - let me break this down in a thread.\n\n"
        
        tweet_number = 2
        
        # Add research insight if available (for EXTERNAL content)
        if writing_state.research_summary and not writing_state.skip_research:
            draft += f"{tweet_number}/ Key insight: {writing_state.research_summary[:100]}...\n\n"
            tweet_number += 1
        
        # Add audience insight if available 
        if writing_state.audience_insights:
            draft += f"{tweet_number}/ Why this matters: {writing_state.audience_insights}\n\n"
            tweet_number += 1
        
        # For ORIGINAL content without research, add content-specific insight
        if writing_state.skip_research and writing_state.content_ownership == "ORIGINAL":
            draft += f"{tweet_number}/ Here's what I've learned from working with {writing_state.topic_title}...\n\n"
            tweet_number += 1
        
        draft += f"{tweet_number}/ What's your take on {writing_state.topic_title}? Share your thoughts! 👇"
        
        return draft
    
    def _generate_linkedin_draft(self, writing_state) -> str:
        """Generate LinkedIn-optimized draft using source content"""
        
        # Try to read actual source content first
        source_content = self._read_source_content(writing_state)
        
        if source_content:
            logger.info("📄 Processing original source content with CrewAI StandardContentFlow for LinkedIn draft")
            return self._process_with_crewai_flow(source_content, writing_state)
        
        # Fallback to template generation if no source content
        logger.info("📝 Generating template LinkedIn draft")
        
        # LinkedIn format: professional, detailed
        draft = f"# {writing_state.topic_title}: Industry Insights\n\n"
        
        if writing_state.research_summary:
            draft += f"## Research Findings\n{writing_state.research_summary}\n\n"
        
        if writing_state.audience_insights:
            draft += f"## Industry Impact\n{writing_state.audience_insights}\n\n"
        
        draft += f"## Key Takeaways\n"
        draft += f"• Innovation in {writing_state.topic_title} is accelerating\n"
        draft += f"• Market implications are significant\n"
        draft += f"• Leaders should consider strategic adoption\n\n"
        
        draft += f"What's your experience with {writing_state.topic_title}? Let's discuss in the comments.\n\n"
        draft += f"#innovation #technology #business"
        
        return draft
    
    def _generate_blog_draft(self, writing_state) -> str:
        """Generate Blog-optimized draft using source content"""
        
        # Try to read actual source content first
        source_content = self._read_source_content(writing_state)
        
        if source_content:
            logger.info("📄 Processing original source content with CrewAI StandardContentFlow for Blog draft")
            return self._process_with_crewai_flow(source_content, writing_state)
        
        # Fallback to template generation if no source content
        logger.info("📝 Generating template Blog draft")
        
        # Blog format: comprehensive, structured
        draft = f"# {writing_state.topic_title}: A Comprehensive Analysis\n\n"
        draft += f"## Introduction\n\n"
        draft += f"In this article, we'll explore {writing_state.topic_title} and its implications for the industry.\n\n"
        
        if writing_state.research_summary:
            draft += f"## Background Research\n\n{writing_state.research_summary}\n\n"
        
        if writing_state.audience_insights:
            draft += f"## Audience Analysis\n\n{writing_state.audience_insights}\n\n"
        
        draft += f"## Technical Deep Dive\n\n"
        draft += f"Technical analysis: This development in {writing_state.topic_title} shows significant potential for industry transformation.\n\n"
        
        draft += f"## Business Implications\n\n"
        draft += f"Business impact: Organizations should evaluate how {writing_state.topic_title} fits into their strategic roadmap.\n\n"
        
        draft += f"## Conclusion\n\n"
        draft += f"{writing_state.topic_title} represents a significant opportunity for innovation and growth.\n\n"
        
        return draft
    
    def _generate_default_draft(self, writing_state) -> str:
        """Generate default format draft"""
        
        draft = f"# {writing_state.topic_title}\n\n"
        
        if writing_state.research_summary:
            draft += f"## Overview\n{writing_state.research_summary}\n\n"
        
        if writing_state.audience_insights:
            draft += f"## Analysis\n{writing_state.audience_insights}\n\n"
        
        draft += f"## Summary\n"
        draft += f"This analysis of {writing_state.topic_title} provides valuable insights for stakeholders.\n"
        
        return draft
    
    def _read_source_content(self, writing_state) -> Optional[str]:
        """Read content from source files"""
        
        try:
            # Check if we have source files to read from
            if hasattr(writing_state, 'source_files') and writing_state.source_files:
                source_files = writing_state.source_files
            elif hasattr(writing_state, 'file_path') and writing_state.file_path:
                source_files = [writing_state.file_path]
            else:
                logger.warning("No source files found in writing_state")
                return None
            
            logger.info(f"📁 Reading from {len(source_files)} source file(s)")
            
            content_parts = []
            
            for file_path in source_files:
                try:
                    path = Path(file_path)
                    if not path.exists():
                        logger.warning(f"Source file not found: {file_path}")
                        continue
                    
                    # Read file content (prefer Path.read_text so tests can mock it)
                    try:
                        file_content = path.read_text(encoding='utf-8').strip()
                    except Exception:
                        with open(path, 'r', encoding='utf-8') as f:
                            file_content = f.read().strip()
                    
                    if file_content:
                        logger.info(f"📄 Read {len(file_content)} characters from {path.name}")
                        
                        # For platform-specific content, look for matching platform
                        if writing_state.platform.lower() in path.name.lower():
                            logger.info(f"🎯 Found platform-specific content for {writing_state.platform}")
                            # Return this content directly as it matches the platform
                            return file_content
                        
                        content_parts.append(file_content)
                    
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
                    continue
            
            # If we found platform-specific content, it was already returned
            # Otherwise, combine all content or return the first one
            if content_parts:
                if len(content_parts) == 1:
                    return content_parts[0]
                else:
                    # Multiple files - combine them
                    combined = "\n\n---\n\n".join(content_parts)
                    logger.info(f"📚 Combined {len(content_parts)} files into single draft")
                    return combined
            
            logger.warning("No readable content found in source files")
            return None
            
        except Exception as e:
            logger.error(f"Error reading source content: {str(e)}")
            return None
    
    def _process_with_crewai_flow(self, source_content: str, writing_state) -> str:
        """Process source content using CrewAI agents"""
        
        try:
            logger.info("🤖 Processing source content with CrewAI agents")
            
            # CI-light: avoid heavy CrewAI processing during tests/CI
            if (
                os.getenv('CI', '0') in ('1', 'true', 'TRUE')
                or os.getenv('CI_LIGHT', '1') in ('1', 'true', 'TRUE')
                or os.getenv('GITHUB_ACTIONS', '0') in ('1', 'true', 'TRUE')
            ):
                logger.info("🧪 CI-light mode: skipping CrewAI flow, returning formatted source content")
                return f"# {writing_state.topic_title}\n\n{source_content}\n\n---\n\n*Generated in CI-light mode*"

            # For ORIGINAL content with skip_research, use direct agent approach
            if writing_state.skip_research and writing_state.content_ownership == "ORIGINAL":
                logger.info("📝 Using direct agent processing for ORIGINAL content (skip_research=True)")
                return self._process_with_writing_agent(source_content, writing_state)
            
            # For other content, use full StandardContentFlow
            logger.info("🔄 Using StandardContentFlow for full pipeline processing")
            
            # Import here to avoid circular dependency
            from ai_writing_flow.crewai_flow.flows.standard_content_flow import StandardContentFlow
            
            # Initialize StandardContentFlow - prawdziwy multi-agent CrewAI Flow
            content_flow = StandardContentFlow(config={
                'verbose': True,
                'min_sources': 1,  # Source content counts as one source
                'quality_threshold': 0.7
            })
            
            # Prepare flow inputs based on source content and writing state
            flow_inputs = {
                'topic_title': writing_state.topic_title,
                'platform': writing_state.platform,
                'key_themes': self._extract_themes_from_source(source_content),
                'editorial_recommendations': f"Process existing source content: {source_content[:200]}...",
                'source_content': source_content,  # Pass source content as additional context
                'content_type': 'standard'
            }
            
            logger.info(f"🎯 Executing CrewAI Flow: {flow_inputs['topic_title']} for {flow_inputs['platform']}")
            
            # Execute real CrewAI Flow with start/listen decorators (legacy nomenclature)
            # To uruchomi cały pipeline: research → audience → writing → style → quality
            result = content_flow.kickoff(inputs=flow_inputs)
            
            # Extract final draft from flow result
            if result and 'final_content' in result:
                final_draft = result['final_content']
                logger.info(f"✅ CrewAI Flow completed successfully - generated content")
                return final_draft
            elif result and 'draft_content' in result:
                draft_content = result['draft_content']
                logger.info(f"✅ CrewAI Flow completed - using draft content")
                return draft_content.draft if hasattr(draft_content, 'draft') else str(draft_content)
            else:
                logger.warning("⚠️ CrewAI Flow completed but no content found in result")
                # Fallback to processed source content
                return f"# {writing_state.topic_title}\n\n{source_content}\n\n---\n\n*Processed by CrewAI Flow*"
            
        except Exception as e:
            logger.error(f"❌ CrewAI StandardContentFlow failed: {str(e)}")
            # Fallback to source content with basic formatting
            return f"# {writing_state.topic_title}\n\n{source_content}\n\n---\n\n*Source content preserved due to CrewAI Flow error: {str(e)}*"
    
    def _extract_themes_from_source(self, source_content: str) -> List[str]:
        """Extract key themes from source content for CrewAI Flow"""
        
        themes = []
        content_lower = source_content.lower()
        
        # Extract themes based on content analysis
        if 'adhd' in content_lower:
            themes.extend(['adhd', 'neurodiversity', 'productivity'])
        if 'ai' in content_lower or 'artificial intelligence' in content_lower:
            themes.extend(['artificial_intelligence', 'automation'])
        if 'tech' in content_lower or 'development' in content_lower:
            themes.extend(['technology', 'software_development'])
        if 'system' in content_lower:
            themes.extend(['systems_thinking', 'optimization'])
        if 'twitter' in content_lower or 'thread' in content_lower:
            themes.extend(['social_media', 'content_strategy'])
        
        return themes if themes else ['general_content']
    
    def _process_with_writing_agent(self, source_content: str, writing_state) -> str:
        """Process content directly with writing agent (skip research)"""
        
        try:
            logger.info("✍️ Processing with direct writing agent")
            
            # For now, use simple processing without full CrewAI
            # TODO: Implement proper agent after fixing imports
            logger.info("📝 Using simplified processing for ORIGINAL content")
            
            # Use existing agents from crewai_flow
            from ai_writing_flow.crewai_flow.agents.writer_agent import WriterAgent
            from ai_writing_flow.crewai_flow.tasks.writing_task import WritingTask
            
            # Create writer agent with configuration
            writer_agent = WriterAgent(config={
                'platform': writing_state.platform,
                'verbose': True,
                'style': 'engaging',
                'tone': 'conversational' if writing_state.platform == 'Twitter' else 'professional'
            })
            
            # Create writing task
            writing_task = WritingTask(
                agent=writer_agent.agent,
                config={
                    'platform': writing_state.platform,
                    'word_count': 1500 if writing_state.platform == 'Blog' else 500,
                    'include_cta': True
                }
            )
            
            # Execute task with source content
            task_result = writing_task.execute(
                topic_title=writing_state.topic_title,
                source_content=source_content,
                platform=writing_state.platform,
                editorial_recommendations=getattr(writing_state, 'editorial_recommendations', 'Transform source content maintaining all key points')
            )
            
            # Extract result
            if hasattr(task_result, 'draft'):
                final_content = task_result.draft
            elif hasattr(task_result, 'content'):
                final_content = task_result.content
            else:
                final_content = str(task_result)
            
            logger.info(f"✅ Writing agent completed - generated {len(final_content)} characters")
            return final_content
            
        except Exception as e:
            logger.error(f"❌ Writing agent failed: {str(e)}")
            # Fallback to formatted source content
            return f"# {writing_state.topic_title}\n\n{source_content}\n\n---\n\n*Writing agent error: {str(e)}*"
    
    def _determine_review_requirement(self, writing_state, result: DraftGenerationResult) -> bool:
        """Determine if human review is required"""
        
        # Always require review if configured
        if self.config.require_human_approval:
            return True
        
        # Auto-approve for low-risk content
        if (writing_state.viral_score <= 3.0 and 
            result.word_count < 100 and 
            writing_state.platform == "Twitter"):
            return False
        
        # High viral score always needs review
        if writing_state.viral_score >= 8.0:
            return True
        
        # Series content needs review
        if writing_state.content_type == "SERIES":
            return True
        
        return True
    
    def _create_review_checkpoint(self, writing_state, result: DraftGenerationResult) -> HumanReviewCheckpoint:
        """Create human review checkpoint"""
        
        checkpoint = HumanReviewCheckpoint()
        checkpoint.review_required = result.requires_human_review
        checkpoint.auto_approve_eligible = (
            writing_state.viral_score < self.config.auto_approve_threshold and
            result.word_count < 500
        )
        
        # Mock quality score calculation
        checkpoint.quality_score = min(10.0, 
            (writing_state.viral_score * 0.4) + 
            (len(writing_state.research_sources) * 0.5) +
            (5.0 if result.audience_targeted else 0.0)
        )
        
        checkpoint.review_criteria = [
            "Content accuracy and factual verification",
            "Audience targeting alignment",
            "Platform optimization compliance",
            "Brand voice and tone consistency"
        ]
        
        if writing_state.viral_score >= 8.0:
            checkpoint.review_criteria.append("High viral potential - extra scrutiny required")
        
        checkpoint.checkpoint_time = datetime.now(timezone.utc)
        
        return checkpoint
    
    def _version_draft(self, writing_state, result: DraftGenerationResult) -> None:
        """Add draft to version history"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        
        if cache_key not in self._draft_versions:
            self._draft_versions[cache_key] = []
        
        self._draft_versions[cache_key].append(result.draft_content)
        result.version_number = len(self._draft_versions[cache_key])
        
        # Also update writing state draft versions
        writing_state.draft_versions.append(result.draft_content)
        
        logger.info(f"📝 Draft versioned: v{result.version_number}")
    
    def _store_review_checkpoint(self, writing_state, checkpoint: HumanReviewCheckpoint) -> None:
        """Store human review checkpoint"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        self._review_checkpoints[cache_key] = checkpoint
        
        logger.info(f"🔍 Review checkpoint created: quality_score={checkpoint.quality_score:.1f}")
    
    def _requires_new_draft_version(self, writing_state) -> bool:
        """Check if a new draft version is needed"""
        
        # Need new version if audience or research data changed
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        
        if cache_key not in self._draft_versions:
            return True
        
        # Check if we have feedback requiring new version
        if writing_state.human_feedback_type in ["major", "pivot"]:
            return True
        
        return False
    
    def _draft_fallback(self, writing_state, error: str) -> DraftGenerationResult:
        """Fallback draft when main generation fails"""
        
        logger.info("🔄 Using draft generation fallback strategy")
        
        result = DraftGenerationResult()
        result.fallback_used = True
        result.requires_human_review = True
        
        # Generate minimal fallback content
        result.draft_content = f"# {writing_state.topic_title}\n\n"
        result.draft_content += f"Draft generation experienced issues - please review and expand the content above.\n\n"
        result.draft_content += f"Topic: {writing_state.topic_title}\n"
        result.draft_content += f"Platform: {writing_state.platform}\n"
        result.draft_content += f"Fallback reason: {error}\n\n"
        result.draft_content += f"Please create content manually and review before publication."
        
        result.word_count = len(result.draft_content.split())
        result.platform_optimized = False
        result.audience_targeted = False
        result.completion_time = datetime.now(timezone.utc)
        
        return result
    
    def _update_writing_state(self, writing_state, result: DraftGenerationResult) -> None:
        """Update WritingFlowState with draft generation results"""
        
        writing_state.current_draft = result.draft_content
        
        # Add to execution history
        if "writer_agent" not in writing_state.agents_executed:
            writing_state.agents_executed.append("writer_agent")
        
        # Update current stage
        writing_state.current_stage = "draft_generation"
        
        logger.info("📝 WritingFlowState updated with draft generation results")
    
    def _mark_draft_completed(self, writing_state, result: DraftGenerationResult) -> None:
        """Mark draft generation as completed in stage manager"""
        
        self.stage_manager.complete_stage(
            FlowStage.DRAFT_GENERATION,
            success=True,
            result={
                "word_count": result.word_count,
                "version_number": result.version_number,
                "requires_review": result.requires_human_review,
                "completion_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info("✅ Draft generation stage marked as completed")
    
    def get_review_checkpoint(self, writing_state) -> Optional[HumanReviewCheckpoint]:
        """Get human review checkpoint for current draft"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._review_checkpoints.get(cache_key)
    
    def get_draft_versions(self, writing_state) -> List[str]:
        """Get all draft versions for current content"""
        
        cache_key = f"{writing_state.topic_title}_{writing_state.platform}"
        return self._draft_versions.get(cache_key, [])
    
    def get_draft_status(self, writing_state) -> Dict[str, Any]:
        """Get comprehensive draft generation status"""
        
        stage_result = self.stage_manager.get_stage_result(FlowStage.DRAFT_GENERATION)
        checkpoint = self.get_review_checkpoint(writing_state)
        
        return {
            "should_execute": self.should_execute_draft_generation(writing_state),
            "current_draft_exists": bool(writing_state.current_draft),
            "draft_word_count": len(writing_state.current_draft.split()) if writing_state.current_draft else 0,
            "version_count": len(self.get_draft_versions(writing_state)),
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "stage_result": stage_result.dict() if stage_result else None,
            "review_checkpoint": {
                "exists": checkpoint is not None,
                "review_required": checkpoint.review_required if checkpoint else True,
                "quality_score": checkpoint.quality_score if checkpoint else 0.0
            } if checkpoint else None
        }


# Export main classes
__all__ = [
    "LinearDraftExecutor",
    "DraftGenerationResult",
    "HumanReviewCheckpoint"
]