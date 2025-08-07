"""
Style Crew - Validates content against Vector Wave styleguide
"""

from crewai import Agent, Crew, Task
from crewai.tools import tool
from typing import Dict, Any, List, Tuple
import re
import os

from ..models import StyleValidation

# Disable CrewAI memory logs
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"


class StyleCrew:
    """Crew responsible for style validation and compliance"""
    
    def __init__(self):
        # Forbidden phrases from Vector Wave styleguide
        self.forbidden_phrases = [
            "leveraging", "utilize", "synergy", "paradigm shift",
            "cutting-edge", "revolutionary", "game-changing", "disruptive",
            "best practices", "industry-leading", "world-class", "next-gen",
            "seamless", "robust", "scalable solution", "enterprise-grade",
            "unlock", "empower", "transform your business", "drive innovation",
            "at the end of the day", "low-hanging fruit", "move the needle",
            "dive into", "dive deep", "deep dive", "unpack",
            "crushing it", "AI guru", "coding ninja", "10x developer"
        ]
        
        # Required elements
        self.required_elements = {
            "evidence": ["statistic", "study", "research", "data", "%", "survey"],
            "specificity": ["example", "for instance", "specifically", "case study"],
            "conclusion": ["therefore", "so", "which means", "the result", "in practice"]
        }
        
        # Style patterns to check
        self.style_patterns = {
            "passive_voice": r'\b(was|were|been|being|is|are|am)\s+\w+ed\b',
            "weasel_words": r'\b(many|some|often|usually|typically|generally)\b',
            "weak_verbs": r'\b(make|do|get|have|take|give)\b',
            "redundancy": r'\b(very|really|actually|basically|simply|just)\s+\w+',
        }
    
    @tool("Check Forbidden Phrases")
    def check_forbidden_phrases(self, draft: str) -> List[str]:
        """Identify forbidden phrases in the draft"""
        found_phrases = []
        draft_lower = draft.lower()
        
        for phrase in self.forbidden_phrases:
            if phrase in draft_lower:
                # Find actual occurrences with context
                pattern = re.compile(r'.{0,20}' + re.escape(phrase) + r'.{0,20}', re.IGNORECASE)
                matches = pattern.findall(draft)
                for match in matches:
                    found_phrases.append(f"'{phrase}' in: ...{match.strip()}...")
        
        return found_phrases
    
    @tool("Validate Required Elements")
    def validate_required_elements(self, draft: str) -> Dict[str, bool]:
        """Check if draft contains required elements"""
        validation = {}
        draft_lower = draft.lower()
        
        for element_type, keywords in self.required_elements.items():
            validation[element_type] = any(keyword in draft_lower for keyword in keywords)
        
        # Additional checks
        validation["non_obvious_insight"] = any(
            phrase in draft_lower 
            for phrase in ["what nobody tells you", "counterintuitive", "surprising", 
                          "hidden", "overlooked", "myth", "actually"]
        )
        
        validation["clear_value"] = any(
            phrase in draft_lower
            for phrase in ["which means", "this matters because", "the result", 
                          "you can", "here's how", "this helps"]
        )
        
        return validation
    
    @tool("Analyze Style Patterns")
    def analyze_style_patterns(self, draft: str) -> Dict[str, List[str]]:
        """Analyze writing style patterns"""
        issues = {}
        
        for pattern_name, pattern_regex in self.style_patterns.items():
            matches = re.findall(pattern_regex, draft, re.IGNORECASE)
            if matches:
                issues[pattern_name] = matches[:5]  # First 5 examples
        
        # Check sentence structure
        sentences = draft.split('.')
        long_sentences = [s.strip() for s in sentences if len(s.split()) > 25]
        if long_sentences:
            issues["long_sentences"] = long_sentences[:3]
        
        # Check for varied sentence beginnings
        sentence_starts = [s.strip().split()[0] if s.strip() else "" for s in sentences]
        repeated_starts = {word: count for word, count in 
                          {w: sentence_starts.count(w) for w in set(sentence_starts)}.items() 
                          if count > 2}
        if repeated_starts:
            issues["repeated_sentence_starts"] = repeated_starts
        
        return issues
    
    @tool("Generate Style Suggestions")
    def generate_suggestions(self, violations: List[Dict[str, str]], 
                           forbidden_phrases: List[str]) -> List[str]:
        """Generate specific improvement suggestions"""
        suggestions = []
        
        # Forbidden phrase replacements
        replacements = {
            "leveraging": "using",
            "utilize": "use",
            "seamless": "smooth",
            "robust": "reliable",
            "dive deep": "explore",
            "unpack": "explain",
            "game-changing": "significant",
            "revolutionary": "innovative"
        }
        
        for phrase in forbidden_phrases:
            for forbidden, replacement in replacements.items():
                if forbidden in phrase.lower():
                    suggestions.append(f"Replace '{forbidden}' with '{replacement}'")
                    break
        
        # Style improvements
        if any("passive_voice" in v for v in violations):
            suggestions.append("Convert passive voice to active: 'X was done by Y' → 'Y did X'")
        
        if any("weak_verbs" in v for v in violations):
            suggestions.append("Use stronger verbs: 'make better' → 'improve', 'have impact' → 'impact'")
        
        if any("weasel_words" in v for v in violations):
            suggestions.append("Be specific: 'many users' → '73% of users', 'often fails' → 'fails 3/10 times'")
        
        return suggestions[:10]  # Top 10 suggestions
    
    def style_validator_agent(self) -> Agent:
        """Create the style validation agent"""
        return Agent(
            role="Editorial Style Guardian",
            goal="Ensure all content meets Vector Wave's exacting style standards",
            backstory="""You are the guardian of Vector Wave's distinctive voice. With years 
            of editorial experience at top tech publications, you have an eagle eye for 
            corporate jargon, passive constructions, and vague claims. You believe that 
            great writing is clear, specific, and evidence-based. You're not just a critic—
            you help writers find better ways to express their ideas while maintaining 
            authenticity and impact.""",
            tools=[
                self.check_forbidden_phrases,
                self.validate_required_elements,
                self.analyze_style_patterns,
                self.generate_suggestions
            ],
            verbose=True,
            allow_delegation=False
        )
    
    def create_validation_task(self, draft: str, styleguide_context: Dict[str, Any]) -> Task:
        """Create a style validation task"""
        return Task(
            description=f"""
            Validate this draft against Vector Wave style standards:
            
            {draft}
            
            Validation Checklist:
            1. ❌ Forbidden Phrases: Check for all banned corporate jargon
            2. ✅ Required Elements: Verify evidence, specificity, clear value
            3. 📝 Style Patterns: Analyze passive voice, weak verbs, redundancy
            4. 🎯 Voice & Tone: Ensure direct, active, specific writing
            5. 💡 Suggestions: Provide specific, actionable improvements
            
            Key Style Rules:
            - No buzzwords or corporate speak
            - Every claim needs evidence
            - Specific > Generic always
            - Active voice preferred
            - Short, punchy sentences
            - Non-obvious insights required
            - Clear value proposition
            
            Be thorough but constructive. The goal is better content, not perfection.
            """,
            agent=self.style_validator_agent(),
            expected_output="Complete style validation report with violations and improvement suggestions"
        )
    
    def execute(self, draft: str, styleguide_context: Dict[str, Any]) -> StyleValidation:
        """Execute style validation crew"""
        crew = Crew(
            agents=[self.style_validator_agent()],
            tasks=[self.create_validation_task(draft, styleguide_context)],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Run validation tools
        forbidden_phrases = self.check_forbidden_phrases(draft)
        required_elements = self.validate_required_elements(draft)
        style_issues = self.analyze_style_patterns(draft)
        
        # Create violations list
        violations = []
        
        for phrase in forbidden_phrases:
            violations.append({
                "type": "forbidden_phrase",
                "severity": "high",
                "description": phrase
            })
        
        for element, present in required_elements.items():
            if not present:
                violations.append({
                    "type": "missing_element",
                    "severity": "medium",
                    "description": f"Missing {element}"
                })
        
        for issue_type, examples in style_issues.items():
            violations.append({
                "type": issue_type,
                "severity": "low",
                "description": f"{issue_type}: {', '.join(examples[:3])}"
            })
        
        # Calculate compliance score
        base_score = 100
        high_violations = len([v for v in violations if v["severity"] == "high"])
        medium_violations = len([v for v in violations if v["severity"] == "medium"])
        low_violations = len([v for v in violations if v["severity"] == "low"])
        
        compliance_score = max(0, base_score - (high_violations * 15) - 
                              (medium_violations * 10) - (low_violations * 5))
        
        # Generate suggestions
        suggestions = self.generate_suggestions(violations, forbidden_phrases)
        
        return StyleValidation(
            is_compliant=compliance_score >= 70,
            violations=violations,
            forbidden_phrases=[phrase.split("'")[1] for phrase in forbidden_phrases 
                             if "'" in phrase],
            suggestions=suggestions,
            compliance_score=compliance_score
        )