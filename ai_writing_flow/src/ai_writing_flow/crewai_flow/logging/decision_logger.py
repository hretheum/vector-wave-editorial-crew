"""
Decision Logger for CrewAI Flow - Task 7.2

Comprehensive logging system for router decisions with:
- Structured decision logging
- Decision context capture
- Performance metrics tracking
- Decision audit trail
"""

import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog
from dataclasses import dataclass, asdict
from enum import Enum

# Configure structured logging
logger = structlog.get_logger(__name__)


class DecisionType(Enum):
    """Types of decisions that can be logged"""
    CONTENT_ANALYSIS = "content_analysis"
    ROUTING = "routing"
    KB_CONSULTATION = "kb_consultation"
    FLOW_TRANSITION = "flow_transition"
    ERROR_HANDLING = "error_handling"


@dataclass
class DecisionContext:
    """Context information for a decision"""
    flow_id: str
    timestamp: float
    topic_title: str
    platform: str
    key_themes: List[str]
    editorial_recommendations: str
    kb_available: bool
    performance_metrics: Dict[str, float]


@dataclass
class DecisionRecord:
    """Complete record of a routing decision"""
    decision_id: str
    decision_type: DecisionType
    context: DecisionContext
    inputs: Dict[str, Any]
    analysis_result: Dict[str, Any]
    routing_decision: str
    reasoning: str
    confidence: float
    kb_consulted: bool
    kb_guidance: Optional[Dict[str, Any]]
    execution_time_ms: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['decision_type'] = self.decision_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


class DecisionLogger:
    """
    Comprehensive decision logging system for CrewAI Flow routing.
    
    Features:
    - Structured logging of all routing decisions
    - Performance metrics tracking
    - Decision audit trail maintenance
    - Query interface for decision analysis
    - Export capabilities for reporting
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize Decision Logger
        
        Args:
            log_dir: Directory for decision logs (default: logs/decisions)
        """
        self.log_dir = Path(log_dir or "logs/decisions")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session file
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.log_dir / f"decisions_{session_id}.jsonl"
        
        # In-memory buffer for current session
        self.session_decisions: List[DecisionRecord] = []
        self.session_decisions_count = 0
        
        # Performance tracking
        self.metrics = {
            "total_decisions": 0,
            "routing_decisions": 0,
            "kb_consultations": 0,
            "avg_decision_time_ms": 0.0,
            "decision_type_counts": {}
        }
        
        logger.info(
            "DecisionLogger initialized",
            log_dir=str(self.log_dir),
            session_file=str(self.session_file)
        )
    
    def log_content_analysis(
        self,
        flow_id: str,
        inputs: Dict[str, Any],
        analysis_result: Dict[str, Any],
        execution_time_ms: float
    ) -> str:
        """
        Log content analysis decision
        
        Returns:
            Decision ID for reference
        """
        decision_id = f"analysis_{flow_id}_{int(time.time() * 1000)}"
        
        context = DecisionContext(
            flow_id=flow_id,
            timestamp=time.time(),
            topic_title=inputs.get('topic_title', ''),
            platform=inputs.get('platform', 'Unknown'),
            key_themes=inputs.get('key_themes', []),
            editorial_recommendations=inputs.get('editorial_recommendations', ''),
            kb_available=analysis_result.get('kb_available', False),
            performance_metrics={
                "analysis_time_ms": execution_time_ms
            }
        )
        
        record = DecisionRecord(
            decision_id=decision_id,
            decision_type=DecisionType.CONTENT_ANALYSIS,
            context=context,
            inputs=inputs,
            analysis_result=analysis_result,
            routing_decision="",  # Not yet determined
            reasoning=f"Content type: {analysis_result.get('content_type')}, Score: {analysis_result.get('viral_score')}",
            confidence=analysis_result.get('analysis_confidence', 0.0),
            kb_consulted=False,
            kb_guidance=None,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
        
        self._save_decision(record)
        
        logger.info(
            "Content analysis logged",
            decision_id=decision_id,
            content_type=analysis_result.get('content_type'),
            viral_score=analysis_result.get('viral_score')
        )
        
        return decision_id
    
    def log_routing_decision(
        self,
        flow_id: str,
        content_type: str,
        viability_score: float,
        routing_decision: str,
        reasoning: str,
        kb_consulted: bool = False,
        kb_guidance: Optional[Dict[str, Any]] = None,
        execution_time_ms: float = 0.0
    ) -> str:
        """
        Log routing decision
        
        Returns:
            Decision ID for reference
        """
        decision_id = f"routing_{flow_id}_{int(time.time() * 1000)}"
        
        # Get context from previous analysis if available
        analysis_record = self._find_latest_analysis(flow_id)
        
        if analysis_record:
            context = analysis_record.context
        else:
            # Create minimal context
            context = DecisionContext(
                flow_id=flow_id,
                timestamp=time.time(),
                topic_title="Unknown",
                platform="Unknown",
                key_themes=[],
                editorial_recommendations="",
                kb_available=kb_consulted,
                performance_metrics={}
            )
        
        record = DecisionRecord(
            decision_id=decision_id,
            decision_type=DecisionType.ROUTING,
            context=context,
            inputs={
                "content_type": content_type,
                "viability_score": viability_score
            },
            analysis_result={},
            routing_decision=routing_decision,
            reasoning=reasoning,
            confidence=0.9 if kb_consulted and kb_guidance else 0.8,
            kb_consulted=kb_consulted,
            kb_guidance=kb_guidance,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
        
        self._save_decision(record)
        
        logger.info(
            "Routing decision logged",
            decision_id=decision_id,
            routing=routing_decision,
            kb_enhanced=kb_consulted
        )
        
        return decision_id
    
    def log_kb_consultation(
        self,
        flow_id: str,
        query: str,
        results: List[Dict[str, Any]],
        guidance: Optional[Dict[str, Any]],
        execution_time_ms: float
    ) -> str:
        """
        Log Knowledge Base consultation
        
        Returns:
            Decision ID for reference
        """
        decision_id = f"kb_{flow_id}_{int(time.time() * 1000)}"
        
        context = DecisionContext(
            flow_id=flow_id,
            timestamp=time.time(),
            topic_title="",
            platform="",
            key_themes=[],
            editorial_recommendations="",
            kb_available=True,
            performance_metrics={
                "kb_query_time_ms": execution_time_ms,
                "results_count": len(results)
            }
        )
        
        record = DecisionRecord(
            decision_id=decision_id,
            decision_type=DecisionType.KB_CONSULTATION,
            context=context,
            inputs={"query": query},
            analysis_result={"results": results},
            routing_decision="",
            reasoning=f"KB consulted with {len(results)} results",
            confidence=guidance.get('confidence', 0.0) if guidance else 0.0,
            kb_consulted=True,
            kb_guidance=guidance,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
        
        self._save_decision(record)
        
        logger.info(
            "KB consultation logged",
            decision_id=decision_id,
            results_count=len(results),
            has_guidance=guidance is not None
        )
        
        return decision_id
    
    def _save_decision(self, record: DecisionRecord):
        """Save decision record to file and memory"""
        # Add to session buffer
        self.session_decisions.append(record)
        
        # Write to file
        with open(self.session_file, 'a') as f:
            f.write(json.dumps(record.to_dict()) + '\n')
        
        # Update metrics
        self._update_metrics(record)
    
    def _update_metrics(self, record: DecisionRecord):
        """Update performance metrics"""
        self.metrics["total_decisions"] += 1
        
        if record.decision_type == DecisionType.ROUTING:
            self.metrics["routing_decisions"] += 1
        
        if record.kb_consulted:
            self.metrics["kb_consultations"] += 1
        
        # Update type counts
        type_key = record.decision_type.value
        self.metrics["decision_type_counts"][type_key] = \
            self.metrics["decision_type_counts"].get(type_key, 0) + 1
        
        # Update average decision time
        if record.execution_time_ms > 0:
            current_avg = self.metrics["avg_decision_time_ms"]
            total_decisions = self.metrics["total_decisions"]
            self.metrics["avg_decision_time_ms"] = \
                (current_avg * (total_decisions - 1) + record.execution_time_ms) / total_decisions
    
    def _find_latest_analysis(self, flow_id: str) -> Optional[DecisionRecord]:
        """Find the latest analysis record for a flow"""
        for record in reversed(self.session_decisions):
            if (record.context.flow_id == flow_id and 
                record.decision_type == DecisionType.CONTENT_ANALYSIS):
                return record
        return None
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session decisions"""
        routing_accuracy = self._calculate_routing_accuracy()
        
        return {
            "session_file": str(self.session_file),
            "metrics": self.metrics,
            "routing_accuracy": routing_accuracy,
            "decision_timeline": self._get_decision_timeline(),
            "kb_usage_stats": self._get_kb_usage_stats()
        }
    
    def _calculate_routing_accuracy(self) -> Dict[str, float]:
        """Calculate routing accuracy metrics"""
        routing_decisions = [
            d for d in self.session_decisions 
            if d.decision_type == DecisionType.ROUTING
        ]
        
        if not routing_decisions:
            return {"accuracy": 0.0, "confidence": 0.0}
        
        total_confidence = sum(d.confidence for d in routing_decisions)
        avg_confidence = total_confidence / len(routing_decisions)
        
        return {
            "total_routing_decisions": len(routing_decisions),
            "avg_confidence": avg_confidence,
            "kb_enhanced_ratio": sum(1 for d in routing_decisions if d.kb_consulted) / len(routing_decisions)
        }
    
    def _get_decision_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline of decisions"""
        timeline = []
        for record in self.session_decisions:
            timeline.append({
                "timestamp": record.timestamp.isoformat(),
                "decision_type": record.decision_type.value,
                "flow_id": record.context.flow_id,
                "routing": record.routing_decision,
                "execution_time_ms": record.execution_time_ms
            })
        return timeline
    
    def _get_kb_usage_stats(self) -> Dict[str, Any]:
        """Get Knowledge Base usage statistics"""
        kb_decisions = [
            d for d in self.session_decisions 
            if d.kb_consulted
        ]
        
        if not kb_decisions:
            return {"kb_consultations": 0, "avg_response_time_ms": 0.0}
        
        avg_time = sum(d.execution_time_ms for d in kb_decisions) / len(kb_decisions)
        
        return {
            "kb_consultations": len(kb_decisions),
            "avg_response_time_ms": avg_time,
            "guidance_provided": sum(1 for d in kb_decisions if d.kb_guidance),
            "kb_impact_on_routing": sum(
                1 for d in kb_decisions 
                if d.decision_type == DecisionType.ROUTING and d.kb_guidance
            )
        }
    
    def log_feedback_processing(
        self,
        flow_id: str,
        stage: str,
        decision: str,
        action: str,
        has_feedback: bool = False
    ):
        """
        Log feedback processing decision
        
        Args:
            flow_id: Flow identifier
            stage: Current stage
            decision: Human decision
            action: Processing action taken
            has_feedback: Whether feedback text was provided
        """
        decision_data = {
            "decision_id": f"feedback_{flow_id}_{int(time.time() * 1000)}",
            "decision_type": "feedback_processing",
            "context": {
                "flow_id": flow_id,
                "timestamp": time.time(),
                "stage": stage,
                "has_feedback": has_feedback
            },
            "inputs": {"decision": decision, "stage": stage},
            "analysis_result": {"action": action},
            "routing_decision": action,
            "reasoning": f"Processing {decision} decision as {action}",
            "confidence": 1.0,
            "kb_consulted": False,
            "kb_guidance": None,
            "execution_time_ms": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log to session file
        with open(self.session_file, 'a') as f:
            f.write(json.dumps(decision_data) + '\n')
        
        logger.info(
            "Feedback processing logged",
            flow_id=flow_id,
            decision=decision,
            action=action
        )
    
    def log_human_review(
        self,
        flow_id: str,
        review_point: str,
        decision: str,
        feedback: Optional[str] = None,
        execution_time_ms: float = 0,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log human review decision
        
        Args:
            flow_id: Flow identifier
            review_point: Review stage identifier
            decision: Human decision (approve/edit/revise/redirect/skip)
            feedback: Optional human feedback text
            execution_time_ms: Time taken for review
            context: Additional context
        """
        # Create a human review decision entry similar to routing decision
        decision_data = {
            "decision_id": f"review_{flow_id}_{int(time.time() * 1000)}",
            "decision_type": "human_review",
            "context": {
                "flow_id": flow_id,
                "timestamp": time.time(),
                "topic_title": context.get("topic_title", "") if context else "",
                "platform": context.get("platform", "") if context else "",
                "key_themes": context.get("key_themes", []) if context else [],
                "editorial_recommendations": "",
                "kb_available": False,
                "performance_metrics": {
                    "review_time_ms": execution_time_ms
                }
            },
            "inputs": {"review_point": review_point},
            "analysis_result": {"human_decision": decision, "feedback": feedback},
            "routing_decision": decision,  # Human decision acts as routing
            "reasoning": f"Human review at {review_point}",
            "confidence": 1.0,  # Human decisions have full confidence
            "kb_consulted": False,
            "kb_guidance": None,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log to session file
        with open(self.session_file, 'a') as f:
            f.write(json.dumps(decision_data) + '\n')
        
        # Update session decisions count
        self.session_decisions_count += 1
        
        logger.info(
            "Human review logged",
            flow_id=flow_id,
            review_point=review_point,
            decision=decision,
            has_feedback=feedback is not None
        )
    
    def export_session_report(self, output_file: Optional[str] = None) -> str:
        """
        Export comprehensive session report
        
        Returns:
            Path to exported report
        """
        report_data = {
            "session_summary": self.get_session_summary(),
            "decisions": [d.to_dict() for d in self.session_decisions],
            "generated_at": datetime.now().isoformat()
        }
        
        if not output_file:
            output_file = self.log_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(
            "Session report exported",
            output_file=str(output_file),
            total_decisions=len(self.session_decisions)
        )
        
        return str(output_file)


# Global instance for easy access
_decision_logger: Optional[DecisionLogger] = None


def get_decision_logger() -> DecisionLogger:
    """Get or create global decision logger instance"""
    global _decision_logger
    if _decision_logger is None:
        _decision_logger = DecisionLogger()
    return _decision_logger