"""
Styleguide Loader - Loads and parses Vector Wave styleguide
"""

from typing import Dict, Any
from pathlib import Path
import yaml
import json


def load_styleguide_context() -> Dict[str, Any]:
    """Load Vector Wave styleguide context for agents"""
    
    # Hardcoded styleguide rules for now
    # In production, would load from actual styleguide files
    
    context = {
        "forbidden_phrases": [
            "leveraging", "utilize", "synergy", "paradigm shift",
            "cutting-edge", "revolutionary", "game-changing", "disruptive",
            "best practices", "industry-leading", "world-class", "next-gen",
            "seamless", "robust", "scalable solution", "enterprise-grade",
            "unlock", "empower", "transform your business", "drive innovation"
        ],
        
        "writing_principles": {
            "clarity": "Simple words > Complex jargon",
            "specificity": "Concrete examples > Abstract concepts",
            "evidence": "Data-backed claims > Unsupported opinions",
            "voice": "Active voice > Passive voice",
            "value": "Reader benefit > Writer ego"
        },
        
        "content_rules": {
            "hooks": "Start with intrigue, not throat-clearing",
            "evidence": "Every claim needs proof",
            "examples": "Show, don't just tell",
            "conclusions": "Clear next steps, not vague inspiration"
        },
        
        "target_audiences": {
            "technical_founder": {
                "wants": "Practical solutions that work",
                "avoids": "Theory without application",
                "tone": "Direct, no-BS, ROI-focused"
            },
            "senior_engineer": {
                "wants": "Technical depth and best practices",
                "avoids": "Superficial overviews",
                "tone": "Technically accurate but accessible"
            },
            "decision_maker": {
                "wants": "Strategic insights and outcomes",
                "avoids": "Implementation details",
                "tone": "Visionary but grounded"
            },
            "skeptical_learner": {
                "wants": "Honest assessment and evidence",
                "avoids": "Hype and unproven claims",
                "tone": "Balanced and transparent"
            }
        },
        
        "platform_guidelines": {
            "LinkedIn": {
                "format": "Professional thought leadership",
                "length": "300-1300 words",
                "style": "Authoritative but approachable"
            },
            "Twitter": {
                "format": "Punchy insights and threads",
                "length": "100-280 chars per tweet",
                "style": "Provocative but substantive"
            },
            "Newsletter": {
                "format": "In-depth analysis",
                "length": "800-2000 words",
                "style": "Comprehensive but scannable"
            }
        },
        
        "quality_standards": {
            "minimum_evidence": 2,  # At least 2 sources/examples
            "readability_target": "8th grade level",
            "originality_threshold": 0.8,  # 80% original insights
            "controversy_limit": 0.3  # Max 30% controversy score
        }
    }
    
    # Try to load actual styleguide files if available
    styleguide_path = Path("/Users/hretheum/dev/bezrobocie/vector-wave/styleguides")
    if styleguide_path.exists():
        # Load kolegium mapping if exists
        mapping_file = styleguide_path / "kolegium-styleguide-mapping.md"
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping_content = f.read()
                # Parse mapping content and update context
                # This is simplified - would parse actual mapping
                context["styleguide_mapping"] = mapping_content[:500]
    
    return context


def get_platform_constraints(platform: str) -> Dict[str, Any]:
    """Get specific constraints for a platform"""
    constraints = {
        "LinkedIn": {
            "min_words": 150,
            "max_words": 1300,
            "optimal_words": 600,
            "allows_formatting": True,
            "allows_links": True,
            "hashtag_limit": 5
        },
        "Twitter": {
            "min_words": 20,
            "max_words": 50,  # For single tweet
            "optimal_words": 40,
            "allows_formatting": False,
            "allows_links": True,
            "hashtag_limit": 2
        },
        "Beehiiv": {
            "min_words": 500,
            "max_words": 2000,
            "optimal_words": 1200,
            "allows_formatting": True,
            "allows_links": True,
            "hashtag_limit": 0
        },
        "Medium": {
            "min_words": 400,
            "max_words": 1500,
            "optimal_words": 800,
            "allows_formatting": True,
            "allows_links": True,
            "hashtag_limit": 5
        }
    }
    
    return constraints.get(platform, constraints["LinkedIn"])


def validate_against_styleguide(content: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Quick validation against styleguide rules"""
    issues = []
    
    content_lower = content.lower()
    
    # Check forbidden phrases
    for phrase in context.get("forbidden_phrases", []):
        if phrase in content_lower:
            issues.append(f"Forbidden phrase found: {phrase}")
    
    # Check for evidence
    evidence_keywords = ["study", "research", "data", "%", "survey", "according to"]
    has_evidence = any(keyword in content_lower for keyword in evidence_keywords)
    if not has_evidence:
        issues.append("No evidence or data points found")
    
    # Check for examples
    example_keywords = ["for example", "for instance", "such as", "like", "e.g."]
    has_examples = any(keyword in content_lower for keyword in example_keywords)
    if not has_examples:
        issues.append("No concrete examples found")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "score": max(0, 100 - (len(issues) * 20))
    }