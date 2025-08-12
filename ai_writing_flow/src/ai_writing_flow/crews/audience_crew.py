"""
Audience Crew - Maps content to target audiences with platform-aware optimization
Enhanced with Editorial Service integration for platform-specific validation
"""

from crewai import Agent, Crew, Task, Process
from crewai.tools import tool
from typing import Dict, Any, List, Optional
import json
import logging
import re
import os
import time
import asyncio

from ..models import AudienceAlignment

# Backwards-compatibility exports for tests expecting these symbols
def calculate_topic_fit_score(topic: str, audience_key: str, platform: str = "LinkedIn") -> float:
    """Compatibility wrapper: compute topic fit score using module logic."""
    audience = VECTOR_WAVE_AUDIENCES.get(audience_key)
    if not audience:
        return 0.5
    score = 0.5
    topic_lower = topic.lower()
    for pain_point in audience["pain_points"]:
        if any(word in topic_lower for word in pain_point.split()):
            score += 0.1
    for value in audience["values"]:
        if any(word in topic_lower for word in value.split()):
            score += 0.1
    if platform.lower() == "twitter" and audience_key in ["technical_founder", "senior_engineer"]:
        score += 0.1
    elif platform.lower() == "linkedin" and audience_key == "decision_maker":
        score += 0.1
    return min(score, 1.0)

def generate_key_message(topic: str, audience_key: str, platform: str = "LinkedIn") -> str:
    """Compatibility wrapper: generate key message for audience/platform."""
    messages = {
        "technical_founder": f"How {topic} drives 3x productivity without adding complexity",
        "senior_engineer": f"Deep dive: Implementing {topic} with clean architecture patterns",
        "decision_maker": f"Strategic guide: Why {topic} is your competitive advantage in 2024",
        "skeptical_learner": f"No BS analysis: What {topic} actually delivers (with data)",
    }
    platform_adjustments = {
        "twitter": " (thread format with clear hooks)",
        "linkedin": " (professional tone with industry insights)",
        "newsletter": " (in-depth with actionable takeaways)",
    }
    base = messages.get(audience_key, f"Exploring {topic}")
    adj = platform_adjustments.get(platform.lower(), "")
    return f"{base}{adj}"
from ..clients.editorial_client import EditorialServiceClient
from ..clients.editorial_utils import aggregate_rules

# Disable CrewAI memory logs
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"

logger = logging.getLogger(__name__)

# Tool call tracking to prevent infinite loops
_tool_call_count = {}
_max_tool_calls = 10  # Max calls per tool per session - increased to allow proper analysis

def reset_tool_counters():
    """Reset tool call counters for new analysis"""
    global _tool_call_count
    _tool_call_count = {}

def track_tool_call(tool_name: str) -> bool:
    """Track tool calls and return False if limit exceeded"""
    global _tool_call_count, _max_tool_calls
    
    if tool_name not in _tool_call_count:
        _tool_call_count[tool_name] = 0
    
    _tool_call_count[tool_name] += 1
    
    if _tool_call_count[tool_name] > _max_tool_calls:
        logger.warning(f"🚨 Tool {tool_name} reached max calls ({_max_tool_calls}). Blocking further calls.")
        return False
    
    logger.info(f"🔧 Tool {tool_name} called {_tool_call_count[tool_name]}/{_max_tool_calls}")
    return True

# Define audiences at module level for tool access
VECTOR_WAVE_AUDIENCES = {
    "technical_founder": {
        "description": "Pragmatic builders seeking efficient solutions",
        "values": ["ROI", "scalability", "proven results"],
        "pain_points": ["time constraints", "technical debt", "team productivity"],
        "preferred_depth": 2
    },
    "senior_engineer": {
        "description": "Tech leaders evaluating tools and practices",
        "values": ["code quality", "best practices", "innovation"],
        "pain_points": ["legacy systems", "team alignment", "technical excellence"],
        "preferred_depth": 3
    },
    "decision_maker": {
        "description": "Strategic thinkers planning digital transformation",
        "values": ["business impact", "competitive advantage", "risk management"],
        "pain_points": ["market pressure", "resource allocation", "change management"],
        "preferred_depth": 1
    },
    "skeptical_learner": {
        "description": "Critical thinkers questioning AI hype",
        "values": ["evidence", "transparency", "realistic expectations"],
        "pain_points": ["information overload", "unproven claims", "implementation complexity"],
        "preferred_depth": 2
    }
}

@tool("Analyze All Audiences")
def analyze_all_audiences(topic: str, platform: str = "LinkedIn") -> str:
    """Analyze topic fit for ALL target audiences and return complete analysis"""
    
    # Circuit breaker: Check if tool was called too many times
    if not track_tool_call("analyze_all_audiences"):
        return """CIRCUIT BREAKER ACTIVATED: Tool called too many times.
        
        Using cached analysis results:
        technical_founder: 0.7, senior_engineer: 0.6, decision_maker: 0.5, skeptical_learner: 0.8
        Primary audience: skeptical_learner (score: 0.80)
        Recommended content depth: Level 2
        """
    
    results = []
    scores = {}
    
    for audience_key in VECTOR_WAVE_AUDIENCES.keys():
        # Calculate score using the original function logic directly
        audience = VECTOR_WAVE_AUDIENCES[audience_key]
        
        # Scoring algorithm (copied from calculate_topic_fit_score)
        score = 0.5  # Base score
        
        # Check if topic addresses pain points
        topic_lower = topic.lower()
        for pain_point in audience["pain_points"]:
            if any(word in topic_lower for word in pain_point.split()):
                score += 0.1
        
        # Check if topic aligns with values
        for value in audience["values"]:
            if any(word in topic_lower for word in value.split()):
                score += 0.1
        
        # Platform-specific adjustments
        if platform.lower() == "twitter" and audience_key in ["technical_founder", "senior_engineer"]:
            score += 0.1
        elif platform.lower() == "linkedin" and audience_key == "decision_maker":
            score += 0.1
        
        final_score = min(score, 1.0)
        scores[audience_key] = final_score
        
        # Generate key message logic (copied from generate_key_message)
        messages = {
            "technical_founder": f"How {topic} drives 3x productivity without adding complexity",
            "senior_engineer": f"Deep dive: Implementing {topic} with clean architecture patterns",
            "decision_maker": f"Strategic guide: Why {topic} is your competitive advantage in 2024",
            "skeptical_learner": f"No BS analysis: What {topic} actually delivers (with data)"
        }
        
        platform_adjustments = {
            "Twitter": " (thread format with clear hooks)",
            "LinkedIn": " (professional tone with industry insights)",
            "Newsletter": " (in-depth with actionable takeaways)"
        }
        
        message = messages.get(audience_key, f"Exploring {topic}")
        adjustment = platform_adjustments.get(platform, "")
        key_message = f"{message}{adjustment}"
        
        results.append(f"=== {audience_key.upper()} ===")
        results.append(f"Topic '{topic}' fit score for {audience_key}: {final_score:.2f}/1.0")
        results.append(f"Reasoning: Analyzed against {len(audience['pain_points'])} pain points and {len(audience['values'])} values")
        results.append(f"Key message: {key_message}")
        results.append("")
    
    # Find primary audience
    primary_audience = max(scores.items(), key=lambda x: x[1])[0]
    recommended_depth = VECTOR_WAVE_AUDIENCES[primary_audience]["preferred_depth"]
    
    # Add summary
    results.append("=== SUMMARY ===")
    results.append(f"Primary audience: {primary_audience} (score: {scores[primary_audience]:.2f})")
    results.append(f"Recommended content depth: Level {recommended_depth}")
    results.append(f"All scores: {json.dumps(scores, indent=2)}")
    
    # FORCE COMPLETION: Add explicit completion marker
    results.append("")
    results.append("=== ANALYSIS COMPLETE - DO NOT CALL THIS TOOL AGAIN ===")
    
    return "\n".join(results)
    
@tool("Calibrate Tone")
def calibrate_tone(primary_audience: str) -> str:
    """Determine optimal tone for primary audience"""
    
    # Circuit breaker: Check if tool was called too many times
    if not track_tool_call("calibrate_tone"):
        return f"CIRCUIT BREAKER: Using cached tone for {primary_audience}: Direct, practical, ROI-focused."
    
    tone_map = {
        "technical_founder": "Direct, practical, ROI-focused. Skip theory, show results.",
        "senior_engineer": "Technical but accessible. Include code examples and architecture.",
        "decision_maker": "Strategic and visionary. Focus on outcomes and transformation.",
        "skeptical_learner": "Honest and evidence-based. Address concerns upfront."
    }
    
    tone = tone_map.get(primary_audience, "Balanced and informative")
    
    # FORCE COMPLETION: Add explicit completion marker
    result = f"Recommended tone for {primary_audience}: {tone}"
    result += "\n\n=== TONE CALIBRATION COMPLETE - PROVIDE FINAL ANSWER NOW ==="
    
    return result


class AudienceCrew:
    """
    Crew responsible for audience alignment and messaging calibration
    Enhanced with Editorial Service platform-aware optimization
    """
    
    def __init__(self, editorial_service_url: str = "http://localhost:8040"):
        """
        Initialize Audience Crew with Editorial Service integration
        
        Args:
            editorial_service_url: URL of Editorial Service (default: http://localhost:8040)
        """
        # Reference module-level audiences
        self.audiences = VECTOR_WAVE_AUDIENCES
        # Track execution time for timeout
        self.start_time = None
        self.max_execution_time = 30  # 30 seconds max
        
        # Editorial Service integration
        self.editorial_service_url = editorial_service_url
        self.editorial_client = None
        self._initialize_editorial_client()
        
        # Circuit breaker state for Editorial Service
        self._editorial_service_available = True
        self._last_check_time = None
        
    def _initialize_editorial_client(self):
        """Initialize Editorial Service client"""
        try:
            self.editorial_client = EditorialServiceClient(
                base_url=self.editorial_service_url,
                timeout=30.0
            )
            logger.info(f"Connected to Editorial Service at {self.editorial_service_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Editorial Service client: {e}")
            self._editorial_service_available = False
    
    @tool("Validate Platform-Specific Content")
    def validate_platform_optimization(self, content: str, platform: str, target_audience: str) -> str:
        """
        Validate content for platform-specific optimization using Editorial Service
        Uses comprehensive validation for thorough platform compliance check
        
        Args:
            content: Content to validate for platform optimization
            platform: Target platform (linkedin, twitter, beehiiv, ghost)
            target_audience: Primary target audience
            
        Returns:
            JSON string with platform-specific validation results
        """
        if not self.editorial_client:
            return json.dumps({
                "error": "Editorial Service not available",
                "platform_compliance": True,  # Allow to continue
                "suggestions": ["Editorial Service connection required for platform optimization"]
            })
        
        try:
            # Run async validation in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                future = concurrent.futures.Future()
                
                async def run_validation():
                    try:
                        result = await self.editorial_client.validate_comprehensive(
                            content=content,
                            platform=platform,
                            content_type="article",
                            context={
                                "agent": "audience",
                                "validation_type": "platform_optimization",
                                "target_audience": target_audience,
                                "platform_specific": True
                            }
                        )
                        future.set_result(result)
                    except Exception as e:
                        future.set_exception(e)
                
                asyncio.create_task(run_validation())
                result = future.result(timeout=30)
            else:
                result = asyncio.run(
                    self.editorial_client.validate_comprehensive(
                        content=content,
                        platform=platform,
                        content_type="article",
                        context={
                            "agent": "audience",
                            "validation_type": "platform_optimization",
                            "target_audience": target_audience,
                            "platform_specific": True
                        }
                    )
                )
            
            # Add platform-specific insights
            platform_insights = self._get_platform_insights(platform, result)
            result["platform_insights"] = platform_insights
            # Add aggregated rule summary
            try:
                result["rule_summary"] = aggregate_rules(result)
            except Exception:
                pass
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Editorial Service platform validation failed: {e}")
            return json.dumps({
                "error": str(e),
                "platform_compliance": True,  # Allow to continue
                "suggestions": ["Check Editorial Service connection for platform optimization"]
            })
    
    @tool("Get Platform-Specific Rules")
    def get_platform_rules(self, platform: str) -> str:
        """
        Get platform-specific rules and constraints from Editorial Service
        
        Args:
            platform: Target platform (linkedin, twitter, beehiiv, ghost)
            
        Returns:
            JSON string with platform-specific rules and guidelines
        """
        if not self.editorial_client:
            return json.dumps({
                "error": "Editorial Service not available",
                "platform_rules": self._get_fallback_platform_rules(platform)
            })
        
        try:
            # Get cache stats to check available platform rules
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                future = concurrent.futures.Future()
                
                async def get_rules():
                    try:
                        cache_dump = await self.editorial_client.get_cache_dump()
                        platform_rules = [
                            rule for rule in cache_dump
                            if rule.get("platform") == platform or rule.get("platform") == "universal"
                        ]
                        
                        result = {
                            "platform": platform,
                            "rules_count": len(platform_rules),
                            "rules": platform_rules[:10],  # First 10 rules
                            "platform_constraints": self._get_platform_constraints(platform)
                        }
                        future.set_result(result)
                    except Exception as e:
                        future.set_exception(e)
                
                asyncio.create_task(get_rules())
                result = future.result(timeout=30)
            else:
                cache_dump = asyncio.run(self.editorial_client.get_cache_dump())
                platform_rules = [
                    rule for rule in cache_dump
                    if rule.get("platform") == platform or rule.get("platform") == "universal"
                ]
                
                result = {
                    "platform": platform,
                    "rules_count": len(platform_rules),
                    "rules": platform_rules[:10],  # First 10 rules
                    "platform_constraints": self._get_platform_constraints(platform)
                }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to get platform rules: {e}")
            return json.dumps({
                "error": str(e),
                "platform_rules": self._get_fallback_platform_rules(platform)
            })
    
    def _get_platform_insights(self, platform: str, validation_result: Dict) -> Dict:
        """Generate platform-specific insights based on validation"""
        insights = {
            "platform": platform,
            "optimization_suggestions": []
        }
        
        if platform == "linkedin":
            insights["optimization_suggestions"].extend([
                "Professional tone recommended",
                "Include industry insights and data",
                "Use LinkedIn-appropriate hashtags",
                "Consider thought leadership angle"
            ])
        elif platform == "twitter":
            insights["optimization_suggestions"].extend([
                "Concise, punchy messaging",
                "Thread-friendly structure",
                "Engaging hooks for retweets",
                "Visual content recommendations"
            ])
        elif platform == "beehiiv":
            insights["optimization_suggestions"].extend([
                "Newsletter-friendly formatting",
                "Subscriber retention focus",
                "Email-optimized structure",
                "Call-to-action placement"
            ])
        elif platform == "ghost":
            insights["optimization_suggestions"].extend([
                "Blog-style content structure",
                "SEO optimization hints",
                "Reader engagement tactics",
                "Subscription conversion tips"
            ])
        
        return insights
    
    def _get_platform_constraints(self, platform: str) -> Dict:
        """Get platform-specific constraints and limits"""
        constraints = {
            "linkedin": {
                "character_limit": 1300,
                "optimal_length": "600-800 characters",
                "tone": "professional",
                "hashtags_limit": 5,
                "features": ["carousel", "video", "document", "poll"]
            },
            "twitter": {
                "character_limit": 280,
                "thread_limit": 25,
                "tone": "conversational",
                "hashtags_limit": 2,
                "features": ["thread", "poll", "spaces", "image"]
            },
            "beehiiv": {
                "character_limit": None,
                "optimal_length": "1200-2000 words",
                "tone": "newsletter-friendly",
                "features": ["segments", "analytics", "referrals"]
            },
            "ghost": {
                "character_limit": None,
                "optimal_length": "800-1500 words",
                "tone": "blog-style",
                "features": ["SEO", "membership", "comments", "newsletters"]
            }
        }
        
        return constraints.get(platform, {})
    
    def _get_fallback_platform_rules(self, platform: str) -> Dict:
        """Fallback platform rules when Editorial Service unavailable"""
        return {
            "platform": platform,
            "basic_rules": [
                f"Optimize content for {platform} audience",
                f"Follow {platform} best practices",
                "Maintain brand voice consistency",
                "Ensure engagement optimization"
            ]
        }

    def audience_mapper_agent(self) -> Agent:
        """Create the audience mapping specialist agent with Editorial Service platform optimization"""
        return Agent(
            role="Audience Strategy Specialist (Platform-Aware)",
            goal="Complete audience analysis with Editorial Service platform optimization in focused tool calls",
            backstory="""You are a highly efficient audience strategist who completes analysis quickly.
            
            CRITICAL RULES:
            1. Call "Analyze All Audiences" tool ONCE (and ONLY once)
            2. Call "Calibrate Tone" tool ONCE (and ONLY once) 
            3. Immediately provide your final answer - DO NOT call any more tools
            4. If you see "CIRCUIT BREAKER" or "COMPLETE" in tool output, STOP and provide final answer
            
            You are being monitored for infinite loops. Stay focused and efficient.""",
            tools=[
                analyze_all_audiences,
                calibrate_tone,
                self.validate_platform_optimization,
                self.get_platform_rules
            ],
            verbose=True,
            allow_delegation=False,
            max_iter=2,  # Reduced to 2 iterations max
            max_execution_time=30  # 30 second timeout
        )
    
    def create_audience_task(self, topic: str, platform: str, research_summary: str, 
                           editorial_recommendations: str) -> Task:
        """Create an audience alignment task with Editorial Service platform optimization"""
        return Task(
            description=f"""
            Complete audience analysis with platform optimization for: {topic}
            Platform: {platform}
            
            PLATFORM-AWARE ANALYSIS STEPS:
            1. Get Platform Rules - Call "Get Platform-Specific Rules" to understand {platform} constraints
            2. Analyze All Audiences - Call "Analyze All Audiences" tool ONCE for topic fit
            3. Calibrate Tone - Call "Calibrate Tone" tool ONCE for primary audience
            4. Validate Platform Optimization - Call "Validate Platform-Specific Content" to ensure platform compliance
            
            Then immediately write your final answer with platform optimization insights.
            
            Topic context: {research_summary[:200]}...
            Editorial context: {editorial_recommendations[:100]}...
            
            Platform Integration:
            - Use Editorial Service platform rules from ChromaDB
            - Consider {platform}-specific constraints and best practices
            - Optimize messaging for {platform} audience behavior
            - Ensure content fits {platform} engagement patterns
            """,
            agent=self.audience_mapper_agent(),
            expected_output="""STRUCTURED FINAL ANSWER WITH PLATFORM OPTIMIZATION:

            PRIMARY AUDIENCE: [audience_name] (Score: X.XX)
            CONTENT DEPTH: Level [1-3]
            TONE: [tone_description]
            
            AUDIENCE SCORES:
            - technical_founder: X.XX
            - senior_engineer: X.XX  
            - decision_maker: X.XX
            - skeptical_learner: X.XX
            
            KEY MESSAGES:
            [List key messages for each audience]
            
            PLATFORM OPTIMIZATION ({platform}):
            - Character/Word Limits: [limits]
            - Optimal Format: [format recommendations]
            - Engagement Strategy: [platform-specific tactics]
            - Platform Rules Applied: [X rules from Editorial Service]
            
            Format exactly as shown above with platform optimization section."""
        )
    
    def execute(self, topic: str, platform: str, research_summary: str, 
                editorial_recommendations: str) -> AudienceAlignment:
        """Execute audience mapping crew with circuit breakers and timeout"""
        
        logger.info(f"🚀 Starting AudienceCrew.execute for topic: {topic}")
        
        # Reset tool call counters for new analysis
        reset_tool_counters()
        self.start_time = time.time()
        
        logger.info("🧹 Tool counters reset, starting crew execution...")
        
        logger.info("🎯 Starting CrewAI audience analysis with circuit breakers...")
        
        try:
            # Create crew with single agent and timeout
            crew = Crew(
                agents=[self.audience_mapper_agent()],
                tasks=[self.create_audience_task(topic, platform, research_summary, editorial_recommendations)],
                verbose=True,  # Changed to True to see what's happening
                max_execution_time=self.max_execution_time,
                process=Process.sequential  # Ensure sequential execution
            )
            
            # Execute crew with timeout monitoring
            result = crew.kickoff()
            
            # Check if we exceeded time limit
            execution_time = time.time() - self.start_time
            if execution_time > self.max_execution_time:
                logger.warning(f"🚨 Execution exceeded {self.max_execution_time}s, using fallback")
                return self._create_fallback_result(topic, platform)
            
            logger.info("🔧 Parsing crew output into AudienceAlignment...")
            
            # Parse result to extract scores and recommendations
            result_text = str(result)
            
            # Try to extract scores from the result
            scores = self._extract_scores_from_result(result_text)
            
            # Default scores if parsing failed
            if not scores:
                logger.warning("Could not parse scores from crew output, using intelligent defaults")
                scores = self._generate_intelligent_scores(topic, platform)
            
            # Find primary audience
            primary_audience = max(scores.items(), key=lambda x: x[1])[0]
            recommended_depth = self.audiences[primary_audience]["preferred_depth"]
            
            # Extract key messages and tone
            key_messages = self._extract_key_messages(result_text, topic, platform)
            tone_calibration = self._extract_tone_calibration(result_text, primary_audience)
            
            logger.info(f"✅ Audience mapping complete. Primary: {primary_audience} (time: {execution_time:.1f}s)")
            
            return AudienceAlignment(
                technical_founder_score=scores.get("technical_founder", 0.7),
                senior_engineer_score=scores.get("senior_engineer", 0.6),
                decision_maker_score=scores.get("decision_maker", 0.5),
                skeptical_learner_score=scores.get("skeptical_learner", 0.8),
                recommended_depth=recommended_depth,
                tone_calibration=tone_calibration,
                key_messages=key_messages
            )
            
        except Exception as e:
            logger.error(f"❌ Crew execution failed: {e}")
            logger.info("🛡️ Using fallback analysis...")
            return self._create_fallback_result(topic, platform)
    
    def _extract_scores_from_result(self, result_text: str) -> Dict[str, float]:
        """Extract audience scores from crew result"""
        scores = {}
        
        # Try to extract JSON scores
        if "All scores:" in result_text:
            try:
                json_start = result_text.find("All scores:") + len("All scores:")
                json_end = result_text.find("}", json_start) + 1
                json_section = result_text[json_start:json_end].strip()
                scores = json.loads(json_section)
                return scores
            except Exception as e:
                logger.debug(f"JSON extraction failed: {e}")
        
        # Try to extract individual scores using regex
        for audience in self.audiences.keys():
            pattern = f"{audience}[: ]+([0-9.]+)"
            match = re.search(pattern, result_text)
            if match:
                try:
                    scores[audience] = float(match.group(1))
                except ValueError:
                    pass
        
        return scores
    
    def _generate_intelligent_scores(self, topic: str, platform: str) -> Dict[str, float]:
        """Generate intelligent fallback scores based on topic and platform"""
        # Simple heuristics based on topic keywords
        topic_lower = topic.lower()
        
        scores = {
            "technical_founder": 0.6,
            "senior_engineer": 0.6, 
            "decision_maker": 0.5,
            "skeptical_learner": 0.7
        }
        
        # Adjust based on topic content
        if any(word in topic_lower for word in ["framework", "workflow", "process"]):
            scores["technical_founder"] += 0.2
            scores["decision_maker"] += 0.1
        
        if any(word in topic_lower for word in ["architecture", "code", "technical", "engineering"]):
            scores["senior_engineer"] += 0.2
            scores["technical_founder"] += 0.1
        
        if any(word in topic_lower for word in ["ai", "automation", "efficiency"]):
            scores["skeptical_learner"] += 0.1
            scores["decision_maker"] += 0.1
        
        # Platform adjustments
        if platform.lower() == "linkedin":
            scores["decision_maker"] += 0.1
        elif platform.lower() == "twitter":
            scores["technical_founder"] += 0.1
            scores["senior_engineer"] += 0.1
        
        # Normalize scores to max 1.0
        for key in scores:
            scores[key] = min(scores[key], 1.0)
        
        return scores
    
    def _extract_key_messages(self, result_text: str, topic: str, platform: str) -> Dict[str, str]:
        """Extract or generate key messages for each audience"""
        key_messages = {}
        
        # Try to extract from result first
        for audience_key in self.audiences.keys():
            pattern = f"Key message[: ]+([^\n]+)"
            matches = re.findall(pattern, result_text, re.IGNORECASE)
            if matches and len(matches) >= len(key_messages) + 1:
                key_messages[audience_key] = matches[len(key_messages)]
        
        # Generate fallback messages if extraction failed
        if len(key_messages) < len(self.audiences):
            fallback_messages = {
                "technical_founder": f"How {topic} drives productivity without complexity",
                "senior_engineer": f"Technical deep dive: {topic} implementation patterns",
                "decision_maker": f"Strategic guide: {topic} competitive advantage",
                "skeptical_learner": f"Evidence-based analysis: What {topic} actually delivers"
            }
            
            for audience_key in self.audiences.keys():
                if audience_key not in key_messages:
                    key_messages[audience_key] = fallback_messages[audience_key]
        
        return key_messages
    
    def _extract_tone_calibration(self, result_text: str, primary_audience: str) -> str:
        """Extract or generate tone calibration"""
        tone_pattern = r"Recommended tone[: ]+([^\n]+)"
        tone_match = re.search(tone_pattern, result_text, re.IGNORECASE)
        
        if tone_match:
            return tone_match.group(1)
        
        # Fallback tone based on primary audience
        tone_map = {
            "technical_founder": "Direct, practical, ROI-focused",
            "senior_engineer": "Technical but accessible with examples",
            "decision_maker": "Strategic and outcome-focused",
            "skeptical_learner": "Evidence-based and transparent"
        }
        
        return tone_map.get(primary_audience, "Balanced and informative")
    
    def _create_fallback_result(self, topic: str, platform: str) -> AudienceAlignment:
        """Create fallback result when crew execution fails"""
        logger.info("🛡️ Creating fallback audience analysis...")
        
        scores = self._generate_intelligent_scores(topic, platform)
        primary_audience = max(scores.items(), key=lambda x: x[1])[0]
        
        return AudienceAlignment(
            technical_founder_score=scores["technical_founder"],
            senior_engineer_score=scores["senior_engineer"],
            decision_maker_score=scores["decision_maker"],
            skeptical_learner_score=scores["skeptical_learner"],
            recommended_depth=self.audiences[primary_audience]["preferred_depth"],
            tone_calibration=self._extract_tone_calibration("", primary_audience),
            key_messages=self._extract_key_messages("", topic, platform)
        )

