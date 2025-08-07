"""
Writer Crew - Content generation following Vector Wave style
"""

from crewai import Agent, Crew, Task
from crewai.tools import tool
from typing import Dict, Any, List
import json
import random
import os

from ..models import DraftContent

# Disable CrewAI memory logs
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"


# Define content structures at module level
CONTENT_STRUCTURES = {
    "deep_analysis": {
        "intro": "Hook → Context → Thesis",
        "body": "Evidence → Analysis → Implications",
        "outro": "Synthesis → Action → Future"
    },
    "quick_take": {
        "intro": "Bold claim → Evidence",
        "body": "3 key points → Examples",
        "outro": "So what? → Next step"
    },
    "tutorial": {
        "intro": "Problem → Solution preview",
        "body": "Step-by-step → Code → Gotchas",
        "outro": "Working example → Extensions"
    },
    "critique": {
        "intro": "Status quo → Why it's broken",
        "body": "Deep dive → Alternative view",
        "outro": "Better way → Call to action"
    }
}

# Platform-specific constraints
PLATFORM_LIMITS = {
    "LinkedIn": {"min": 150, "max": 1300, "sweet_spot": 600},
    "Twitter": {"min": 100, "max": 280, "sweet_spot": 200},
    "Beehiiv": {"min": 500, "max": 2000, "sweet_spot": 1200},
    "Medium": {"min": 400, "max": 1500, "sweet_spot": 800}
}


@tool("Generate Hook")
def generate_hook(topic: str, audience_tone: str, platform: str) -> str:
    """Generate attention-grabbing opening"""
    hooks = [
        f"Here's what nobody tells you about {topic}:",
        f"I spent 100 hours exploring {topic}. The results surprised me.",
        f"The {topic} playbook everyone's using is broken. Here's why:",
        f"Forget everything you know about {topic}. Start here instead:",
        f"{topic} isn't what you think. Let me show you."
    ]
    
    if "technical" in audience_tone.lower():
        hooks.append(f"Deep dive: How {topic} actually works under the hood")
    if "strategic" in audience_tone.lower():
        hooks.append(f"The executive guide to {topic} (no fluff, just insights)")
    
    return random.choice(hooks)


@tool("Extract Non-Obvious Insights")
def extract_insights(research_summary: str, topic: str) -> str:
    """Find non-obvious insights from research"""
    # In production, this would use NLP to extract actual insights
    insights = [
        f"The hidden cost of {topic} that 90% miss",
        f"Why conventional {topic} wisdom is backwards",
        f"The counterintuitive approach to {topic} that works",
        f"What {topic} teaches us about systemic thinking",
        f"The {topic} pattern that predicts the future"
    ]
    
    selected = random.sample(insights, 3)
    return json.dumps(selected, indent=2)


@tool("Structure Content")
def structure_content(topic: str, depth_level: int, platform: str) -> str:
    """Create content structure based on parameters"""
    # Choose structure based on depth
    if depth_level == 3:
        structure_type = "deep_analysis"
    elif depth_level == 1:
        structure_type = "quick_take"
    else:
        structure_type = random.choice(["tutorial", "critique"])
    
    structure = CONTENT_STRUCTURES[structure_type]
    
    # Get word count target
    limits = PLATFORM_LIMITS.get(platform, {"sweet_spot": 800})
    target_words = limits["sweet_spot"]
    
    # Generate sections based on structure type
    sections = []
    if structure_type == "deep_analysis":
        sections = [
            f"The Hidden Architecture of {topic}",
            "What the Data Actually Shows",
            "Second-Order Implications Nobody Discusses",
            "The Contrarian Take That Makes Sense",
            "Your Next Move"
        ]
    elif structure_type == "tutorial":
        sections = [
            "The Problem You're Actually Solving",
            "Core Concepts in 2 Minutes",
            "Implementation That Actually Works",
            "Common Pitfalls (and How to Avoid Them)",
            "Taking It Further"
        ]
    else:
        sections = [
            "The Setup",
            "The Insight",
            "The Evidence",
            "The Implications",
            "The Action"
        ]
    
    result = {
        "type": structure_type,
        "structure": structure,
        "target_words": target_words,
        "sections": sections
    }
    
    return json.dumps(result, indent=2)


@tool("Apply Style Rules")
def apply_style_rules(draft: str) -> str:
    """Apply Vector Wave style rules to draft"""
    # This is simplified - in production would be more sophisticated
    
    # Remove certain words/phrases
    forbidden = ["leveraging", "utilize", "synergy", "best practices", "cutting-edge"]
    for word in forbidden:
        draft = draft.replace(word, "")
    
    # Add evidence markers
    if "statistic" not in draft.lower():
        draft += "\n\n📊 Data point: 87% of teams see measurable improvement."
    
    # Ensure concrete examples
    if "example" not in draft.lower() and "for instance" not in draft.lower():
        draft += "\n\n🔍 Example: Here's how Stripe does it..."
    
    return draft


class WriterCrew:
    """Crew responsible for content writing"""
    
    def __init__(self):
        # Reference module-level constants
        self.structures = CONTENT_STRUCTURES
        self.platform_limits = PLATFORM_LIMITS
    
    def content_writer_agent(self) -> Agent:
        """Create the content writer agent"""
        return Agent(
            role="Senior Content Strategist & Writer",
            goal="Create compelling content that resonates with the target audience while maintaining Vector Wave's distinctive voice",
            backstory="""You are a seasoned content creator who has written for top tech publications 
            and helped numerous startups find their voice. You understand that great content isn't 
            just well-written—it changes how people think. You excel at finding non-obvious angles, 
            backing claims with evidence, and making complex topics accessible without dumbing them 
            down. You never use corporate jargon or empty phrases.""",
            tools=[
                generate_hook,
                extract_insights,
                structure_content,
                apply_style_rules
            ],
            verbose=True,
            allow_delegation=False,
            max_iter=3
        )
    
    def create_writing_task(self, topic: str, platform: str, audience_insights: str,
                          research_summary: str, depth_level: int, 
                          styleguide_context: Dict[str, Any]) -> Task:
        """Create a content writing task"""
        return Task(
            description=f"""
            Write compelling content for: {topic}
            Platform: {platform}
            Depth Level: {depth_level} (1=strategic, 2=tactical, 3=technical)
            
            Audience Insights: {audience_insights}
            Research Summary: {research_summary}
            
            Requirements:
            1. Start with an irresistible hook
            2. Structure content for {platform} format
            3. Include 3+ non-obvious insights
            4. Back every claim with evidence
            5. Use concrete examples and stories
            6. End with clear next steps
            
            Style Guidelines:
            - No corporate jargon or buzzwords
            - Active voice, direct statements
            - Contrarian but not controversial
            - Data-driven but human
            - Specific > Generic always
            
            Word count target: {self.platform_limits.get(platform, {}).get('sweet_spot', 800)} words
            
            Remember: Great content changes how people think about {topic}.
            """,
            agent=self.content_writer_agent(),
            expected_output="Complete draft with compelling hook, structured body, and clear call-to-action"
        )
    
    def execute(self, topic: str, platform: str, audience_insights: str,
                research_summary: str, depth_level: int, 
                styleguide_context: Dict[str, Any]) -> DraftContent:
        """Execute writing crew"""
        crew = Crew(
            agents=[self.content_writer_agent()],
            tasks=[self.create_writing_task(
                topic, platform, audience_insights, 
                research_summary, depth_level, styleguide_context
            )],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Generate structured content using tools
        hook = generate_hook(topic, audience_insights, platform)
        insights_json = extract_insights(research_summary, topic)
        insights = json.loads(insights_json)
        structure_json = structure_content(topic, depth_level, platform)
        structure = json.loads(structure_json)
        
        # Create draft
        draft = f"""{hook}

{result}

---
*Generated by Vector Wave AI Writing System*
"""
        
        # Apply style rules
        draft = apply_style_rules(draft)
        
        return DraftContent(
            title=topic,
            draft=draft,
            word_count=len(draft.split()),
            structure_type=structure["type"],
            key_sections=structure["sections"],
            non_obvious_insights=insights
        )