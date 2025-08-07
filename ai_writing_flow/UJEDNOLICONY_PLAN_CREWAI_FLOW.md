# 🎯 UJEDNOLICONY PLAN IMPLEMENTACJI CREWAI FLOW

**Status**: MASTER PLAN - Single Source of Truth  
**Version**: 1.0  
**Created**: 2025-08-04  
**Last Updated**: 2025-08-04  

## 📊 EXECUTIVE SUMMARY

### Cel Projektu
Implementacja pełnowymiarowego **CrewAI Flow** zgodnego z AI_WRITING_FLOW_DIAGRAM.md, wykorzystującego stabilną infrastrukturę z Phase 1-4 i Knowledge Base integration.

### Current State vs Target State
- **CURRENT**: Linear Flow z doskonałą infrastrukturą (monitoring, alerting, circuit breakers) ale bez CrewAI Flow business logic
- **TARGET**: Full CrewAI Flow z @router/@listen decorators, conditional branching, Knowledge Base decision support

### Success Metrics
- ✅ CrewAI Flow completion rate >95%
- ✅ Knowledge Base integration w 80%+ routing decisions  
- ✅ Backward compatibility z existing Kolegium integration
- ✅ Performance <10% overhead vs Linear Flow

---

## 🏗️ ARCHITECTURE OVERVIEW

### Hybrid Architecture Strategy
**ZACHOWAĆ** całą proven infrastructure (Phase 1-4) + **DODAĆ** CrewAI Flow layer:

```python
class AIWritingCrewFlow(Flow):
    """Production CrewAI Flow z full monitoring"""
    
    def __init__(self):
        # Inherit proven infrastructure
        self.metrics = FlowMetrics()           # ✅ Keep
        self.circuit_breaker = CircuitBreaker() # ✅ Keep  
        self.knowledge_adapter = get_adapter()  # ✅ Keep
        self.quality_gates = QualityGate()     # ✅ Keep
        
        # Add CrewAI Flow components
        self.setup_flow_routes()               # 🆕 Add
        self.setup_agents()                    # 🆕 Add
    
    @start
    def content_analysis_start(self):
        return Task(
            description="Analyze content and determine flow path",
            agent=self.analysis_agent,
            expected_output="Content analysis with routing decision"
        )
    
    @router(content_analysis_start)
    def route_by_content_type(self, context):
        if context.output.get('content_type') == "TECHNICAL_TUTORIAL":
            return self.technical_flow
        elif context.output.get('viral_score', 0) > 0.8:
            return self.viral_content_flow
        return self.standard_flow
    
    @listen(content_analysis_start)
    def technical_flow(self, context):
        return [
            self.deep_research_task,
            self.code_validation_task, 
            self.technical_writing_task
        ]
```

### Key Components

#### 1. **Flow Control Layer** 🆕
- `@start/@router/@listen` decorators
- Conditional branching logic
- Flow state management
- Context passing between stages

#### 2. **Enhanced Knowledge Integration** 🔄
```python
@tool("flow_routing_advisor")
def flow_routing_advisor(content_analysis: str) -> str:
    """KB-powered routing decisions"""
    routing_query = f"CrewAI flow routing patterns {content_analysis}"
    kb_advice = await get_adapter().search(routing_query, limit=3)
    return determine_optimal_path(kb_advice)
```

#### 3. **Proven Infrastructure** ✅ KEEP ALL
- FlowMetrics & AlertManager (monitoring)
- Circuit Breakers & RetryManager (reliability)
- QualityGate & ValidationRules (quality)
- Enhanced Knowledge Tools (KB integration)
- UIBridge & API endpoints (Kolegium integration)

---

## 📋 4-WEEK IMPLEMENTATION PLAN

### Week 1: Foundation Migration 🏗️
**Goal**: Basic CrewAI Flow structure with proven infrastructure

**Day 1-2: Project Setup**
- Install CrewAI dependencies in existing environment
- Create CrewAI Flow project structure
- Setup basic Flow class inheriting from proven components

**Day 3-4: Basic Flow Implementation**
```python
# First working Flow
class BasicAIWritingFlow(Flow):
    @start
    def analyze_content(self):
        return Task(
            description="Basic content analysis",
            agent=self.analyzer_agent
        )
    
    @listen(analyze_content)
    def write_content(self, context):
        return Task(
            description="Generate content based on analysis",
            agent=self.writer_agent
        )
```

**Day 5: Knowledge Base Integration Test**
- Test KB access from Flow context
- Validate enhanced_knowledge_tools.py compatibility
- Performance benchmark vs Linear Flow

**Week 1 Success Criteria**:
- ✅ Basic Flow executes without errors
- ✅ Knowledge Base accessible from Flow
- ✅ Monitoring/alerting functional
- ✅ V1 API still working (backward compatibility)

### Week 2: Conditional Routing 🛤️
**Goal**: Implement @router logic with KB-powered decisions

**Day 1-2: Router Implementation**
```python
@router(content_analysis_start)
def route_by_content_analysis(self, context):
    content_type = context.output.get('content_type')
    viral_score = context.output.get('viral_score', 0)
    controversy = context.output.get('controversy_score', 0)
    
    # KB-powered routing decision
    routing_advice = self.knowledge_adapter.get_flow_examples(
        f"routing {content_type} viral:{viral_score}"
    )
    
    if content_type == "TECHNICAL":
        return self.technical_flow
    elif viral_score > 0.8:
        return self.viral_flow
    elif controversy > 0.7:
        return self.editorial_review_flow
    
    return self.standard_flow
```

**Day 3-4: Multiple Flow Paths**
- Technical Tutorial Flow (research → code validation → writing)
- Viral Content Flow (trend research → viral writing → engagement)
- Editorial Review Flow (controversy assessment → human review)
- Standard Flow (research → audience → writing → style → quality)

**Day 5: Flow Decision Validation**
- Test routing accuracy with sample content
- Validate Knowledge Base decision support
- Performance impact assessment

**Week 2 Success Criteria**:
- ✅ 4 distinct flow paths working
- ✅ KB-powered routing decisions
- ✅ Flow context preserved across stages
- ✅ Decision accuracy >90%

### Week 3: Human-in-Loop Integration 👤
**Goal**: AG-UI integration for human review points

**Day 1-2: Human Review Points**
```python
@listen("draft_completed")
def human_review_gate(self, context):
    # Present draft to human via AG-UI
    review_result = self.ui_bridge.request_human_review(
        draft=context.output.get('draft'),
        review_type="content_quality"
    )
    
    if review_result.decision == "approve":
        return self.style_validation
    elif review_result.decision == "minor_edits":
        return self.style_validation_with_notes
    elif review_result.decision == "major_revisions":
        return self.audience_realignment
    else:  # direction_change
        return self.research_enhancement
```

**Day 3-4: AG-UI Event Integration**
- Human feedback collection via ChatPanel
- Real-time flow status updates
- Human decision impact on flow routing

**Day 5: End-to-End Flow Testing**
- Complete flows with human intervention
- UI responsiveness validation
- Error handling in human review timeouts

**Week 3 Success Criteria**:
- ✅ Human review integrated at key decision points
- ✅ AG-UI real-time flow status
- ✅ Human decisions properly route flow
- ✅ Timeout/error handling robust

### Week 4: Production Optimization 🚀
**Goal**: Performance, monitoring, and production deployment

**Day 1-2: Performance Optimization**
- Flow execution profiling
- Knowledge Base query optimization
- Circuit breaker tuning for Flow patterns

**Day 3-4: Enhanced Monitoring**
```python
class FlowMetricsV2(FlowMetrics):
    """Enhanced metrics for CrewAI Flow"""
    
    def track_flow_decision(self, router_name: str, decision: str, context: dict):
        self.record_custom_metric("flow_decision", {
            "router": router_name,
            "decision": decision,
            "context_size": len(str(context)),
            "kb_usage": context.get("kb_queries", 0)
        })
    
    def track_human_interaction(self, interaction_type: str, duration: float):
        self.record_custom_metric("human_interaction", {
            "type": interaction_type,
            "duration_seconds": duration,
            "flow_stage": self.current_stage
        })
```

**Day 5: Production Deployment**
- Blue-green deployment with fallback to Linear Flow
- Production monitoring dashboard
- Performance validation in production environment

**Week 4 Success Criteria**:
- ✅ Flow performance <10% overhead vs Linear
- ✅ Production monitoring comprehensive
- ✅ Zero-downtime deployment successful
- ✅ Fallback mechanisms tested

---

## 🔧 TECHNICAL IMPLEMENTATION DETAILS

### Flow State Management
```python
class CrewAIFlowState(BaseModel):
    """Enhanced flow state for CrewAI patterns"""
    
    # Inherit from proven FlowControlState
    base_state: FlowControlState
    
    # CrewAI Flow specific
    current_flow_path: str
    router_decisions: List[Dict[str, Any]]
    human_interactions: List[Dict[str, Any]]
    kb_queries: List[Dict[str, Any]]
    context_data: Dict[str, Any]
    
    def add_router_decision(self, router: str, decision: str, reasoning: str):
        self.router_decisions.append({
            "timestamp": datetime.now(),
            "router": router,
            "decision": decision,
            "reasoning": reasoning,
            "kb_support": self.kb_queries[-1] if self.kb_queries else None
        })
```

### Knowledge Base Integration
```python
@tool("crewai_flow_advisor")
def crewai_flow_advisor(flow_context: str, decision_point: str) -> str:
    """Provide flow routing advice using KB knowledge"""
    
    query = f"CrewAI flow patterns {decision_point} {flow_context}"
    
    kb_response = get_adapter().search(
        query=query,
        strategy=SearchStrategy.HYBRID,
        limit=3,
        score_threshold=0.4
    )
    
    return f"""
    # Flow Decision Recommendation
    
    ## Context Analysis
    {flow_context}
    
    ## Knowledge Base Insights
    {kb_response.file_content}
    
    ## Recommended Action
    {analyze_kb_patterns_for_decision(kb_response, decision_point)}
    
    ## Confidence Score
    {kb_response.confidence_score}
    """
```

### Error Handling & Recovery
```python
class FlowCircuitBreaker(CircuitBreaker):
    """CrewAI Flow aware circuit breaker"""
    
    def __init__(self, flow_state: CrewAIFlowState):
        super().__init__("crewai_flow", flow_state.base_state)
        self.flow_state = flow_state
    
    def handle_flow_failure(self, stage: str, error: Exception):
        if isinstance(error, KnowledgeBaseError):
            # Fallback to Linear Flow without KB
            return self.fallback_to_linear_flow()
        elif isinstance(error, HumanReviewTimeout):
            # Auto-approve after timeout
            return self.auto_approve_with_logging()
        else:
            # Standard circuit breaker logic
            return super().handle_failure(stage, error)
```

---

## 🔗 INTEGRATION POINTS

### 1. Kolegium Redakcyjne Integration
**Input Interface**: Zachować existing API
```python
# Existing interface remains unchanged
writing_flow_input = {
    "topic_title": topic.title,
    "platform": topic.recommended_platform,
    "folder_path": analysis_result.folder,
    "content_type": analysis_result.contentType,
    "content_ownership": analysis_result.contentOwnership,
    "viral_score": topic.viralScore,
    "editorial_recommendations": analysis_result.recommendation
}

# Enhanced routing based on Kolegium analysis
@router(kolegium_input_analysis)
def route_by_kolegium_analysis(self, context):
    kolegium_data = context.inputs
    
    if kolegium_data.get('content_ownership') == 'ORIGINAL':
        return self.original_content_flow
    elif kolegium_data.get('viral_score', 0) > 0.8:
        return self.viral_optimization_flow
    
    return self.standard_editorial_flow
```

### 2. LinkedIn Module Integration
**Output Interface**: Enhanced publication packaging
```python
@listen("content_finalized")
def prepare_linkedin_publication(self, context):
    publication_package = {
        "content": context.output.get('final_draft'),
        "platform_variants": context.output.get('platform_variants', {}),
        "media_path": context.output.get('pdf_path'),
        "scheduling_recommendation": self.analyze_optimal_timing(context),
        "engagement_predictions": self.predict_performance(context)
    }
    
    # Direct integration with LinkedIn module
    linkedin_result = self.linkedin_publisher.schedule_post(
        content=publication_package['content'],
        media_path=publication_package['media_path'],
        schedule_time=publication_package['scheduling_recommendation']
    )
    
    return linkedin_result
```

### 3. Knowledge Base Deep Integration
**Enhanced Query Patterns**:
```python
class FlowKnowledgeQueries:
    """Specialized KB queries for flow decisions"""
    
    @staticmethod
    def get_routing_patterns(content_type: str, context: dict) -> str:
        return f"CrewAI flow routing {content_type} viral_score:{context.get('viral_score')} controversy:{context.get('controversy')}"
    
    @staticmethod
    def get_error_recovery_patterns(error_type: str, flow_stage: str) -> str:
        return f"CrewAI error handling {error_type} stage:{flow_stage} recovery patterns"
    
    @staticmethod
    def get_human_review_guidance(review_type: str, content_analysis: str) -> str:
        return f"CrewAI human review {review_type} {content_analysis} best practices"
```

---

## ⚠️ RISK MITIGATION

### 1. Infinite Loop Prevention
**Multi-Layer Protection**:
```python
class LoopPreventionV2(LoopPreventionSystem):
    """Enhanced loop prevention for CrewAI Flow"""
    
    def __init__(self):
        super().__init__()
        self.flow_path_history = []
        self.router_decision_count = {}
        self.max_same_router_decisions = 3
    
    def validate_flow_transition(self, from_stage: str, to_stage: str, router: str):
        # Prevent same router making too many decisions
        router_count = self.router_decision_count.get(router, 0)
        if router_count >= self.max_same_router_decisions:
            raise LoopDetectionError(f"Router {router} exceeded decision limit")
        
        # Prevent circular flow paths
        current_path = f"{from_stage}->{to_stage}"
        if self.flow_path_history.count(current_path) > 2:
            raise LoopDetectionError(f"Circular path detected: {current_path}")
```

### 2. Knowledge Base Dependency Management
**Fallback Strategy**:
```python
class KBFallbackStrategy:
    """Fallback when Knowledge Base unavailable"""
    
    def __init__(self, linear_flow: LinearAIWritingFlow):
        self.linear_fallback = linear_flow
        self.kb_health_check_interval = 30  # seconds
    
    def execute_with_fallback(self, flow_method, *args, **kwargs):
        try:
            if self.is_kb_healthy():
                return flow_method(*args, **kwargs)
            else:
                logger.warning("KB unhealthy, falling back to Linear Flow")
                return self.linear_fallback.execute(*args, **kwargs)
        except KnowledgeBaseError:
            logger.error("KB error, immediate fallback to Linear Flow")
            return self.linear_fallback.execute(*args, **kwargs)
```

### 3. Human Review Timeout Handling
```python
@listen("human_review_requested")
def handle_human_review_with_timeout(self, context):
    timeout_seconds = 300  # 5 minutes
    
    try:
        review_result = asyncio.wait_for(
            self.ui_bridge.request_human_review(context),
            timeout=timeout_seconds
        )
        return self.process_human_decision(review_result)
    
    except asyncio.TimeoutError:
        logger.warning("Human review timeout, auto-proceeding with quality gates")
        return self.auto_quality_assessment(context)
```

### 4. Backward Compatibility
**V1 API Preservation**:
```python
class BackwardCompatibilityLayer:
    """Maintain V1 API while adding V2 CrewAI Flow"""
    
    def __init__(self):
        self.v1_flow = LinearAIWritingFlow()  # Keep V1 working
        self.v2_flow = AIWritingCrewFlow()    # New CrewAI Flow
    
    def execute(self, inputs: dict, version: str = "v2"):
        if version == "v1" or not self.v2_flow.is_healthy():
            return self.v1_flow.execute(inputs)
        else:
            return self.v2_flow.kickoff(inputs)
```

---

## 📊 SUCCESS CRITERIA & VALIDATION

### Technical Metrics
```python
class CrewAIFlowKPIs:
    """Comprehensive success metrics"""
    
    # Flow Execution Metrics
    flow_completion_rate: float        # Target: >95%
    average_flow_duration: float       # Target: <300 seconds
    error_recovery_rate: float         # Target: >90%
    
    # Decision Quality Metrics  
    router_decision_accuracy: float    # Target: >90%
    kb_query_success_rate: float       # Target: >95%
    human_review_efficiency: float     # Target: <120 seconds avg
    
    # Integration Metrics
    kolegium_compatibility: float      # Target: 100%
    linkedin_publication_success: float # Target: >98%
    backward_compatibility: float      # Target: 100%
    
    # Performance Metrics
    flow_overhead_vs_linear: float     # Target: <10%
    kb_query_response_time: float      # Target: <200ms
    memory_usage_increase: float       # Target: <20%
```

### Business Metrics
- **Content Quality**: Improved routing leads to 15% better content quality scores
- **Efficiency**: 25% reduction in human review time through better initial routing
- **Scalability**: System handles 10x more concurrent flows than V1

### Integration Success
- **Zero Downtime**: Deployment without service interruption
- **API Compatibility**: All existing Kolegium integrations work unchanged
- **LinkedIn Publishing**: Enhanced publication packaging with scheduling optimization

---

## 📁 DOCUMENTATION STRUCTURE (NEW)

### Consolidated Documentation
**REMOVE** (outdated/duplicate):
- CREWAI_FLOW_ATOMIC_TASKS.md ❌ (replaced by this plan)
- AI_WRITING_FLOW_TASKS.md ❌ (obsolete task list)
- CREWAI_FLOW_FIX_PLAN.md ❌ (superseded)
- NAPRAWA_FLOW.md ❌ (fix plan no longer relevant)
- FLOOD_FIX.md ❌ (specific issue fixed)

**KEEP** (current/valuable):
- AI_WRITING_FLOW_DIAGRAM.md ✅ (target vision)
- AI_WRITING_FLOW_DESIGN.md ✅ (detailed requirements)
- PROJECT_CONTEXT.md ✅ (project overview)
- DEPLOYMENT_STATUS.json ✅ (current status)

**CREATE** (new structure):
```
/docs/
├── UJEDNOLICONY_PLAN_CREWAI_FLOW.md    # This document - MASTER PLAN
├── implementation/
│   ├── week1-foundation.md
│   ├── week2-routing.md  
│   ├── week3-human-loop.md
│   └── week4-production.md
├── architecture/
│   ├── flow-patterns.md
│   ├── kb-integration.md
│   └── monitoring-v2.md
└── migration/
    ├── v1-to-v2-guide.md
    └── rollback-procedures.md
```

---

## 🚀 IMMEDIATE NEXT STEPS

### DAY 1 ACTIONS (Start Implementation):

1. **Environment Setup**:
```bash
cd /Users/hretheum/dev/bezrobocie/vector-wave/kolegium/ai_writing_flow
pip install crewai>=0.74.0
pip install crewai-tools
```

2. **Create Basic Flow Structure**:
```python
# src/ai_writing_flow/crewai_flow_v2.py
from crewai import Flow, Agent, Task
from .monitoring.flow_metrics import FlowMetrics

class AIWritingCrewFlow(Flow):
    def __init__(self):
        super().__init__()
        self.metrics = FlowMetrics()  # Keep proven monitoring
        
    @start
    def analyze_content(self):
        return Task(
            description="Analyze content requirements",
            agent=self.content_analyzer,
            expected_output="Content analysis with routing decision"
        )
```

3. **Test Knowledge Base Integration**:
```python
# Test KB access from Flow context
from knowledge_config import KnowledgeConfig
from src.ai_writing_flow.adapters.knowledge_adapter import get_adapter

adapter = get_adapter()
test_result = adapter.search("CrewAI flow patterns", limit=2)
print(f"KB Integration Test: {test_result.success}")
```

4. **Validate Existing Infrastructure**:
```bash
# Run existing monitoring/alerting tests
pytest tests/test_flow_metrics.py -v
pytest tests/test_circuit_breaker_complete.py -v
```

### SUCCESS VALIDATION (End of Day 1):
- ✅ CrewAI installed and basic Flow class created
- ✅ Knowledge Base accessible from Flow context  
- ✅ Existing monitoring/alerting still functional
- ✅ V1 Linear Flow still operational (backward compatibility)

---

## 🎯 FINAL RECOMMENDATION

**IMPLEMENTACJA READY**: Ten plan jest production-ready z:
- ✅ Proven infrastructure foundation (Phase 1-4 achievements)
- ✅ Clear 4-week implementation roadmap
- ✅ Comprehensive risk mitigation
- ✅ Backward compatibility strategy
- ✅ Integration points clearly defined

**START TODAY**: Wszystkie komponenty są gotowe do rozpoczęcia implementacji. Knowledge Base działa, infrastruktura jest stabilna, plan jest szczegółowy i wykonalny.

**EXPECTED OUTCOME**: Pełnowymiarowy CrewAI Flow zgodny z pierwotną wizją z AI_WRITING_FLOW_DIAGRAM.md, zachowujący całą proven infrastructure i dodający advanced flow control z Knowledge Base support.

---

*Ten dokument jest SINGLE SOURCE OF TRUTH dla implementacji CrewAI Flow. Wszystkie inne plany planistyczne są obsolete.*