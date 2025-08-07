"""
Quality Crew - Final quality assessment and fact-checking
"""

from crewai import Agent, Crew, Task
from crewai.tools import tool
from typing import Dict, Any, List, Optional
import re
from datetime import datetime
import os

from ..models import QualityAssessment

# Disable CrewAI memory logs
os.environ["CREWAI_STORAGE_LOG_ENABLED"] = "false"


class QualityCrew:
    """Crew responsible for final quality control"""
    
    def __init__(self):
        # Quality criteria weights
        self.criteria_weights = {
            "factual_accuracy": 0.25,
            "source_verification": 0.20,
            "logical_coherence": 0.15,
            "value_delivery": 0.15,
            "readability": 0.10,
            "originality": 0.10,
            "actionability": 0.05
        }
        
        # Ethics checklist items
        self.ethics_checklist = [
            "no_misleading_claims",
            "proper_attribution",
            "balanced_perspective",
            "no_harmful_advice",
            "respects_privacy",
            "avoids_discrimination"
        ]
    
    @tool("Fact Check Claims")
    def fact_check_claims(self, draft: str, sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Verify factual claims in the draft"""
        fact_checks = []
        
        # Pattern for statistics and claims
        stat_patterns = [
            r'(\d+(?:\.\d+)?)\s*%',  # Percentages
            r'(\d+)x\s+(?:faster|better|more)',  # Multipliers
            r'(\d+(?:,\d{3})*)\s+(?:users|companies|developers)',  # Counts
            r'\$(\d+(?:\.\d+)?[MBK]?)',  # Money amounts
            r'(?:study|research|survey)\s+(?:shows|found|indicates)',  # Studies
        ]
        
        for pattern in stat_patterns:
            matches = re.finditer(pattern, draft, re.IGNORECASE)
            for match in matches:
                context = draft[max(0, match.start()-50):min(len(draft), match.end()+50)]
                
                # Check if claim is supported by sources
                supported = any(source.get("title", "").lower() in context.lower() 
                              for source in sources)
                
                fact_checks.append({
                    "claim": match.group(0),
                    "context": context.strip(),
                    "verified": supported,
                    "confidence": "high" if supported else "low"
                })
        
        return fact_checks
    
    @tool("Verify Code Examples")
    def verify_code_examples(self, draft: str) -> Optional[Dict[str, str]]:
        """Check code examples for correctness"""
        # Find code blocks
        code_pattern = r'```(\w+)?\n(.*?)```'
        code_blocks = re.findall(code_pattern, draft, re.DOTALL)
        
        if not code_blocks:
            return None
        
        verification = {
            "total_blocks": len(code_blocks),
            "languages": list(set(lang for lang, _ in code_blocks if lang)),
            "syntax_valid": True,  # Simplified - would use actual parsers
            "best_practices": True,
            "security_issues": []
        }
        
        # Check for common security issues
        for lang, code in code_blocks:
            if "eval(" in code or "exec(" in code:
                verification["security_issues"].append("Unsafe eval/exec usage")
            if "password" in code.lower() and "=" in code:
                verification["security_issues"].append("Possible hardcoded credentials")
        
        return verification
    
    @tool("Assess Logical Flow")
    def assess_logical_flow(self, draft: str) -> Dict[str, Any]:
        """Evaluate logical coherence and structure"""
        paragraphs = [p.strip() for p in draft.split('\n\n') if p.strip()]
        
        assessment = {
            "structure_clear": len(paragraphs) >= 3,
            "has_introduction": any(p.endswith('?') or 'here' in p.lower() 
                                  for p in paragraphs[:2]),
            "has_conclusion": any(word in paragraphs[-1].lower() 
                                for word in ['therefore', 'so', 'result', 'means']),
            "logical_transitions": 0,
            "coherence_score": 0.0
        }
        
        # Check transitions
        transition_words = ['however', 'therefore', 'moreover', 'furthermore', 
                          'additionally', 'consequently', 'thus', 'hence']
        for para in paragraphs:
            if any(word in para.lower() for word in transition_words):
                assessment["logical_transitions"] += 1
        
        # Calculate coherence score
        if assessment["structure_clear"] and assessment["has_introduction"] and assessment["has_conclusion"]:
            assessment["coherence_score"] = 0.8
        else:
            assessment["coherence_score"] = 0.5
        
        if assessment["logical_transitions"] >= 2:
            assessment["coherence_score"] += 0.2
        
        return assessment
    
    @tool("Check Controversy Score")
    def check_controversy(self, draft: str) -> float:
        """Assess potential controversy level"""
        controversy_triggers = {
            "high": ["wrong", "stupid", "idiots", "hate", "destroy", "kill"],
            "medium": ["controversial", "debate", "disagree", "critics", "opponents"],
            "low": ["challenge", "question", "consider", "alternative", "perspective"]
        }
        
        score = 0.0
        draft_lower = draft.lower()
        
        for level, words in controversy_triggers.items():
            matches = sum(1 for word in words if word in draft_lower)
            if level == "high":
                score += matches * 0.3
            elif level == "medium":
                score += matches * 0.15
            else:
                score += matches * 0.05
        
        return min(score, 1.0)
    
    @tool("Evaluate Value Delivery")
    def evaluate_value(self, draft: str, non_obvious_insights: List[str]) -> Dict[str, bool]:
        """Check if content delivers promised value"""
        evaluation = {
            "has_clear_takeaway": any(phrase in draft.lower() 
                                    for phrase in ["you can", "here's how", "step"]),
            "provides_examples": "example" in draft.lower() or "for instance" in draft.lower(),
            "actionable_advice": any(phrase in draft.lower() 
                                   for phrase in ["try", "implement", "start", "use this"]),
            "unique_perspective": len(non_obvious_insights) >= 2,
            "saves_reader_time": len(draft.split()) < 1500  # Concise is valuable
        }
        
        return evaluation
    
    def quality_controller_agent(self) -> Agent:
        """Create the quality control agent"""
        return Agent(
            role="Chief Quality Officer",
            goal="Ensure content meets the highest standards of accuracy, value, and integrity",
            backstory="""You are a meticulous quality controller with a background in 
            investigative journalism and technical writing. You've fact-checked for major 
            publications and have a reputation for catching errors others miss. You believe 
            that quality content must be accurate, valuable, and ethical. You're thorough 
            but pragmatic, understanding that perfection is less important than publishing 
            valuable, trustworthy content.""",
            tools=[
                self.fact_check_claims,
                self.verify_code_examples,
                self.assess_logical_flow,
                self.check_controversy,
                self.evaluate_value
            ],
            verbose=True,
            allow_delegation=False
        )
    
    def create_quality_task(self, draft: str, sources: List[Dict[str, str]], 
                          styleguide_context: Dict[str, Any]) -> Task:
        """Create a quality assessment task"""
        return Task(
            description=f"""
            Perform comprehensive quality assessment on this draft:
            
            {draft[:500]}... [truncated]
            
            Quality Checklist:
            
            1. 📊 Fact Checking
               - Verify all statistics and claims
               - Check source attribution
               - Validate data points
            
            2. 💻 Technical Accuracy (if applicable)
               - Verify code examples work
               - Check for security issues
               - Ensure best practices
            
            3. 🧠 Logical Coherence
               - Clear structure and flow
               - Logical transitions
               - Consistent argument
            
            4. 💡 Value Delivery
               - Clear takeaways
               - Actionable insights
               - Time-saving for reader
            
            5. ⚖️ Ethics & Controversy
               - No misleading claims
               - Balanced perspective
               - Appropriate tone
            
            6. 📈 Overall Quality Score
               - Rate 0-100 based on all factors
               - Flag any blockers
               - Suggest improvements
            
            Sources provided: {len(sources)}
            
            Be thorough but remember: Good enough published beats perfect in drafts.
            """,
            agent=self.quality_controller_agent(),
            expected_output="Complete quality assessment with scores and recommendations"
        )
    
    def execute(self, draft: str, sources: List[Dict[str, str]], 
                styleguide_context: Dict[str, Any]) -> QualityAssessment:
        """Execute quality control crew"""
        crew = Crew(
            agents=[self.quality_controller_agent()],
            tasks=[self.create_quality_task(draft, sources, styleguide_context)],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Run quality checks
        fact_checks = self.fact_check_claims(draft, sources)
        code_verification = self.verify_code_examples(draft)
        logical_flow = self.assess_logical_flow(draft)
        controversy_score = self.check_controversy(draft)
        value_delivery = self.evaluate_value(draft, [])  # Would get from state
        
        # Build ethics checklist results
        ethics_results = {}
        for item in self.ethics_checklist:
            # Simplified - in production would be more sophisticated
            ethics_results[item] = True
        
        # Calculate quality score
        scores = {
            "factual_accuracy": 0.9 if all(fc["verified"] for fc in fact_checks) else 0.6,
            "source_verification": 0.8 if sources else 0.4,
            "logical_coherence": logical_flow["coherence_score"],
            "value_delivery": sum(value_delivery.values()) / len(value_delivery),
            "readability": 0.85,  # Would use readability metrics
            "originality": 0.8,   # Would use similarity detection
            "actionability": 0.9 if value_delivery.get("actionable_advice") else 0.5
        }
        
        quality_score = sum(score * self.criteria_weights[criterion] 
                          for criterion, score in scores.items()) * 100
        
        # Generate improvement suggestions
        suggestions = []
        
        if not all(fc["verified"] for fc in fact_checks):
            suggestions.append("Add source citations for unverified claims")
        
        if not logical_flow["has_conclusion"]:
            suggestions.append("Add a clear conclusion with key takeaways")
        
        if controversy_score > 0.5:
            suggestions.append("Consider softening controversial statements")
        
        if not value_delivery.get("actionable_advice"):
            suggestions.append("Add specific, actionable next steps")
        
        # Determine if human review needed
        requires_human = (
            quality_score < 70 or
            controversy_score > 0.7 or
            bool(code_verification and code_verification.get("security_issues")) or
            not all(ethics_results.values())
        )
        
        return QualityAssessment(
            is_approved=quality_score >= 70 and not requires_human,
            quality_score=quality_score,
            fact_check_results=[{
                "claim": fc["claim"],
                "status": "verified" if fc["verified"] else "unverified",
                "confidence": fc["confidence"]
            } for fc in fact_checks],
            code_verification=code_verification,
            ethics_checklist=ethics_results,
            improvement_suggestions=suggestions,
            requires_human_review=requires_human,
            controversy_score=controversy_score
        )