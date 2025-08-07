# ROADMAP - AI Kolegium Redakcyjne

## 📊 Project Overview
- **Objective**: Implementacja inteligentnego systemu redakcyjnego z AG-UI Protocol
- **Success Criteria**: Działający system human-in-the-loop z 5 agentami AI
- **Timeline**: 7 tygodni (42 dni robocze)
- **Risk Level**: Medium - nowa technologia AG-UI, kompleksna architektura

## 🏗️ Architecture Overview
Event-driven microservices z Clean Architecture, gdzie każdy domain service jest niezależnym kontenerem komunikującym się przez AG-UI events. Event sourcing zapewnia pełną audytowalność decyzji redakcyjnych.

## 📈 Implementation Phases

**Total Timeline**: 8 tygodni (5 phases)
**Total Atomic Tasks**: 24 (Tasks 1.0 - 5.5)

### Phase 1: Foundation & Infrastructure (2 tygodnie)
**Objective**: Stworzenie solid infrastructure z AG-UI, CI/CD i monitoringiem
**Success Criteria**: Deploy pipeline działa, pierwszy agent emituje eventy

#### Atomic Tasks:

- [x] **Task 1.0**: Setup Digital Ocean droplet infrastructure ✅ [COMPLETED 2025-01-17]
  - **Agent**: deployment-specialist
  - **Time**: 2h
  - **Dependencies**: none
  - **Success**: 
    - Droplet (46.101.156.14) dostępny przez SSH ✅
    - Docker + Docker Compose zainstalowane ✅
    - Basic firewall rules (22, 80, 443, 8000-8010) ✅
    - Non-root user 'editorial-ai' created ✅
    - Python venv with crewai, fastapi, redis ✅
  - **Files**: `/docs/digital-ocean-setup.md` (existing)

- [x] **Task 1.1**: Knowledge Base integration ✅ [COMPLETED 2025-08-03]
  - **Agent**: deployment-specialist + project-coder
  - **Time**: 6h
  - **Dependencies**: Task 1.0
  - **Success**:
    - Standalone KB service w kontenerach (port 8082) ✅
    - PostgreSQL + Redis + ChromaDB integration ✅
    - Enhanced Knowledge Tools z adapter pattern ✅
    - Circuit breaker i hybrid search strategies ✅
    - Testy integracyjne przechodzą z CrewAI agents ✅
  - **Files**: `knowledge_adapter.py`, `enhanced_knowledge_tools.py`, docker-compose.yml

- [ ] **Task 1.2**: AG-UI integration z CrewAI agents
  - **Agent**: project-coder  
  - **Time**: 3h
  - **Dependencies**: Task 1.1
  - **Success**:
    - Custom tools emitują AG-UI events
    - Event emitter integration w agent callbacks
    - WebSocket endpoint dla real-time communication
    - TOPIC_DISCOVERED + CONTENT_ANALYSIS events working
  - **Files**: `src/tools/agui_tools.py`, FastAPI websocket endpoints

- [x] **Task 1.3**: Docker containers setup ✅ [COMPLETED 2025-08-03]
  - **Agent**: deployment-specialist
  - **Time**: 3h
  - **Dependencies**: Task 1.2
  - **Success**:
    - docker-compose.yml dla development ✅
    - docker-compose.prod.yml dla production z ghcr.io ✅
    - Dockerfile dla głównego API ✅
    - Health checks dla wszystkich containers ✅
    - Monitoring stack (Prometheus + Grafana) ✅
  - **Files**: `docker-compose.yml`, `docker-compose.prod.yml`, `Dockerfile`

- [x] **Task 1.4**: GitHub Actions CI/CD pipeline ✅ [COMPLETED 2025-08-03]
  - **Agent**: deployment-specialist
  - **Time**: 4h
  - **Dependencies**: Task 1.3
  - **Success**:
    - Build & test na każdym PR ✅
    - Push images do ghcr.io ✅
    - Auto-deploy przez Watchtower ✅
    - Security scanning (Trivy) ✅
    - Multi-service build matrix ✅
  - **Files**: `.github/workflows/ci-cd.yml`, `DEPLOYMENT_GUIDE.md`

- [ ] **Task 1.5**: PostgreSQL Event Store implementation
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 1.2
  - **Success**:
    - Event store tables (events, snapshots)
    - Event repository implementation
    - Migration system setup
    - Basic event replay capability
  - **Files**: `src/shared/infrastructure/database/`, `migrations/`

- [ ] **Task 1.6**: Redis integration dla caching i streams
  - **Agent**: project-coder
  - **Time**: 2h
  - **Dependencies**: Task 1.5
  - **Success**:
    - Redis streams dla event processing
    - Caching layer dla read models
    - Connection pooling configuration
    - Health checks
  - **Files**: `src/shared/infrastructure/cache/`

- [ ] **Task 1.7**: Basic monitoring setup (Prometheus + Grafana)
  - **Agent**: deployment-specialist
  - **Time**: 3h
  - **Dependencies**: Task 1.4
  - **Success**:
    - Prometheus metrics collection
    - Grafana dashboards dla system health
    - Basic alerting rules
    - OpenTelemetry tracing setup
  - **Files**: `monitoring/prometheus.yml`, `monitoring/grafana/dashboards/`

- [ ] **Task 1.8**: Security podstawy (JWT, rate limiting)
  - **Agent**: deployment-specialist
  - **Time**: 2h
  - **Dependencies**: Task 1.7
  - **Success**:
    - JWT authentication middleware
    - Rate limiting per endpoint
    - CORS configuration
    - Basic input validation
  - **Files**: `src/shared/infrastructure/security/`

#### Phase 1 Validation:
- [ ] **Quality Gate**: All tests passing (>80% coverage)
- [ ] **Performance Check**: <200ms API response time
- [ ] **Security Check**: Security scan passed
- [ ] **Documentation Update**: Architecture diagrams current

---

### Phase 2: Core Agent Implementation (2 tygodnie)
**Objective**: Enhanced Content Scout + Trend Analyst z pełną AG-UI integracją
**Success Criteria**: 2 agenty działają end-to-end z real-time events

#### Atomic Tasks:

- [ ] **Task 2.0**: Enhanced Content Scout z built-in tools  
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Phase 1 complete
  - **Success**:
    - SerperDevTool dla Google Search integrated
    - ScrapeWebsiteTool dla content extraction
    - Custom RSS monitoring tool
    - Social media monitoring tools
    - Pydantic output models (TopicDiscovery)
  - **Files**: Enhanced `agents.py`, `tasks.py`, custom tools

- [ ] **Task 2.1**: Memory system setup dla agent consistency
  - **Agent**: project-coder
  - **Time**: 2h
  - **Dependencies**: Task 2.0
  - **Success**:
    - PostgreSQL memory storage configured
    - 4 memory types enabled (short-term, long-term, entity, contextual)
    - Memory persistence across agent sessions
    - Embedding model setup dla similarity search
  - **Files**: Database config, memory configuration w Crew setup

- [ ] **Task 2.2**: Multi-LLM setup z fallback chains
  - **Agent**: project-coder
  - **Time**: 2h
  - **Dependencies**: Task 2.1
  - **Success**:
    - OpenAI GPT-4 jako primary LLM
    - Claude jako fallback LLM
    - Per-agent LLM customization
    - Automatic fallback on API errors
    - Cost optimization per use case
  - **Files**: LLM provider configuration, agent LLM assignments

- [ ] **Task 2.3**: Social media monitoring integration
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 2.2
  - **Success**:
    - Twitter/X API integration
    - Reddit API integration
    - Sentiment analysis básico
    - Rate limiting compliance
  - **Files**: `src/domains/content/infrastructure/services/social_service.py`

- [ ] **Task 2.4**: Knowledge Sources dla editorial guidelines
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 2.2
  - **Success**:
    - Editorial guidelines jako TextFileKnowledgeSource
    - Content strategies knowledge base
    - Controversial topics detection database
    - Vector embeddings dla knowledge retrieval
    - Knowledge integration w agent decisions
  - **Files**: `knowledge/` folder, knowledge source configurations

- [ ] **Task 2.5**: Google Trends API integration
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 2.4
  - **Success**:
    - Google Trends scraping
    - Trend strength calculation
    - Historical data comparison
    - API rate limiting
  - **Files**: `src/domains/analytics/infrastructure/apis/google_trends.py`

- [ ] **Task 2.6**: Trend Analyst agent implementation
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 2.5
  - **Success**:
    - CrewAI agent z analytics tools
    - CONTENT_ANALYSIS events emission
    - Viral potential scoring
    - Performance optimization
  - **Files**: `src/domains/analytics/infrastructure/agents/trend_analyst.py`

- [ ] **Task 2.7**: Read models dla topics i analytics
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 2.6
  - **Success**:
    - CQRS read models
    - Event projections
    - Query optimization
    - Cache invalidation strategy
  - **Files**: `src/shared/infrastructure/database/read_models/`

- [ ] **Task 2.8**: Basic React frontend setup
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 2.7
  - **Success**:
    - React 18 + TypeScript setup
    - AG-UI connection hook
    - Basic dashboard layout
    - Real-time topic stream component
  - **Files**: `frontend/src/`, `frontend/src/hooks/useAGUIConnection.ts`

#### Phase 2 Validation:
- [ ] **Quality Gate**: End-to-end topic discovery works
- [ ] **Performance Check**: <2s agent response time
- [ ] **Integration Test**: AG-UI events flow correctly
- [ ] **Documentation Update**: Agent specifications documented

---

### Phase 3: CrewAI Flows & Human-in-the-Loop (2 tygodnie)
**Objective**: EditorialDecisionFlow z human collaboration patterns
**Success Criteria**: Deterministic decision tree z human input support

#### Atomic Tasks:

- [ ] **Task 3.0**: EditorialDecisionFlow implementation
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Phase 2 complete
  - **Success**:
    - CrewAI Flow z @start, @listen, @router decorators
    - Conditional routing based on controversy/viral scores
    - State management z EditorialState Pydantic model
    - Flow execution paths: approve/reject/human_review
    - Integration z existing agents jako flow steps
  - **Files**: `flows/editorial_decision_flow.py`, state models

- [ ] **Task 3.1**: Controversy detection algorithm
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 3.0
  - **Success**:
    - ML model dla controversy scoring
    - Keyword-based detection
    - Sensitivity levels configuration
    - False positive minimization
  - **Files**: `src/domains/editorial/infrastructure/services/controversy_detector.py`

- [ ] **Task 3.2**: Human-in-the-Loop Flow implementation
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 3.1
  - **Success**:
    - HumanReviewFlow jako sub-flow
    - Native Flow support dla human input
    - Timeout handling (5 min default)
    - Escalation do senior editors
    - AG-UI events dla human interaction
  - **Files**: `flows/human_review_flow.py`, timeout/escalation logic

- [ ] **Task 3.3**: Human input UI components
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 3.2
  - **Success**:
    - Pending decisions panel
    - Decision form z context
    - Real-time notifications
    - Decision history view
  - **Files**: `frontend/src/components/editorial/`

- [ ] **Task 3.4**: Quality domain implementation
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 3.0
  - **Success**:
    - QualityAssessment, FactCheck entities
    - QualityScore value object
    - Source credibility scoring
    - Quality metrics aggregation
  - **Files**: `src/domains/quality/domain/`

- [ ] **Task 3.5**: Fact-checking API integration
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 3.4
  - **Success**:
    - Integration z fact-checking services
    - Source verification APIs
    - Plagiarism detection
    - Credibility scoring algorithm
  - **Files**: `src/domains/quality/infrastructure/apis/`

- [ ] **Task 3.6**: Quality Assessor agent
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 3.5
  - **Success**:
    - Automated quality checks
    - QUALITY_ASSESSMENT events
    - Source verification workflow
    - Quality score calculation
  - **Files**: `src/domains/quality/infrastructure/agents/quality_assessor.py`

- [ ] **Task 3.7**: CopilotKit integration
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 3.3
  - **Success**:
    - CopilotKit provider setup
    - AI assistant dla redaktorów
    - Interactive chat interface
    - Context-aware suggestions
  - **Files**: `frontend/src/providers/CopilotProvider.tsx`

- [ ] **Task 3.8**: Advanced dashboard components
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 3.7
  - **Success**:
    - Agent status monitoring
    - Decision queue management
    - Analytics visualizations
    - Activity feed real-time
  - **Files**: `frontend/src/components/dashboard/`

#### Phase 3 Validation:
- [ ] **Quality Gate**: Human decisions influence AI workflow
- [ ] **Performance Check**: <50ms WebSocket latency
- [ ] **UX Test**: Redaktorzy mogą skutecznie współpracować z AI
- [ ] **Documentation Update**: Human-in-the-loop workflow documented

---

### Phase 4: Orchestration & Production (1 tydzień)
**Objective**: Decision Coordinator + production hardening
**Success Criteria**: System production-ready z pełnym monitoringiem

#### Atomic Tasks:

- [ ] **Task 4.0**: Orchestration domain implementation
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Phase 3 complete
  - **Success**:
    - Workflow, TaskCoordination entities
    - Multi-agent coordination logic
    - Consensus building algorithms
    - Workflow state management
  - **Files**: `src/domains/orchestration/domain/`

- [ ] **Task 4.1**: Decision Coordinator agent
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 4.0
  - **Success**:
    - Multi-agent orchestration
    - UI_COMPONENT generation
    - Dynamic report creation
    - TASK_COMPLETE events
  - **Files**: `src/domains/orchestration/infrastructure/agents/decision_coordinator.py`

- [ ] **Task 4.2**: Generative UI components
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 4.1
  - **Success**:
    - Dynamic chart generation
    - Context-sensitive reports
    - AI-generated summaries
    - Interactive decision trees
  - **Files**: `frontend/src/components/generative/`

- [ ] **Task 4.3**: Production security hardening
  - **Agent**: deployment-specialist
  - **Time**: 3h
  - **Dependencies**: Task 4.2
  - **Success**:
    - HTTPS z Let's Encrypt
    - Enhanced rate limiting
    - Input sanitization
    - Security headers
  - **Files**: `scripts/security-hardening.sh`, `nginx/nginx.conf`

- [ ] **Task 4.4**: Load testing i performance optimization
  - **Agent**: deployment-specialist
  - **Time**: 3h
  - **Dependencies**: Task 4.3
  - **Success**:
    - Load tests dla 100 concurrent users
    - Performance benchmarks
    - Database query optimization
    - Caching strategy refinement
  - **Files**: `tests/load/`, `docs/performance-benchmarks.md`

- [ ] **Task 4.5**: Advanced monitoring i alerting
  - **Agent**: deployment-specialist
  - **Time**: 3h
  - **Dependencies**: Task 4.4
  - **Success**:
    - Comprehensive Grafana dashboards
    - Alert rules dla critical metrics
    - Error tracking z Sentry
    - Business metrics monitoring
  - **Files**: `monitoring/grafana/dashboards/`, `monitoring/alerts/`

- [ ] **Task 4.6**: Backup i disaster recovery
  - **Agent**: deployment-specialist
  - **Time**: 2h
  - **Dependencies**: Task 4.5
  - **Success**:
    - Automated PostgreSQL backups
    - Event store backup strategy
    - Recovery procedures documented
    - Backup restoration testing
  - **Files**: `scripts/backup.sh`, `docs/disaster-recovery.md`

- [ ] **Task 4.7**: Final documentation i training materials
  - **Agent**: documentation-keeper
  - **Time**: 3h
  - **Dependencies**: Task 4.6
  - **Success**:
    - Complete API documentation
    - User guides dla redaktorów
    - Deployment runbooks
    - Troubleshooting guides
  - **Files**: `docs/api/`, `docs/user-guides/`, `docs/operations/`

#### Phase 4 Validation:
- [ ] **Quality Gate**: Load tests pass (100 concurrent users)
- [ ] **Security Check**: Penetration testing passed
- [ ] **Documentation Check**: All critical paths documented
- [ ] **Go-Live Check**: Production readiness checklist complete

---

### Phase 5: Dynamic Agent System (1 tydzień)
**Objective**: Runtime agent creation i management przez chat/API
**Success Criteria**: Użytkownicy mogą tworzyć custom agents przez natural language

#### Atomic Tasks:

- [ ] **Task 5.0**: Agent Factory & Registry implementation
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Phase 4 complete
  - **Success**:
    - DynamicAgentFactory class
    - Agent Registry z persistence
    - Agent Template system
    - Runtime tool resolution
  - **Files**: `src/shared/infrastructure/agents/agent_factory.py`

- [ ] **Task 5.1**: Natural Language Agent Parser
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 5.0
  - **Success**:
    - NL to agent config parser
    - Intent extraction z LLM
    - Capability validation
    - Security constraints checker
  - **Files**: `src/shared/infrastructure/agents/nl_parser.py`

- [ ] **Task 5.2**: Chat-based Agent Creation UI
  - **Agent**: project-coder
  - **Time**: 3h
  - **Dependencies**: Task 5.1
  - **Success**:
    - /spawn-agent command w UI
    - Agent creation wizard
    - Real-time preview
    - Capability selector
  - **Files**: `frontend/src/components/agents/AgentCreator.tsx`

- [ ] **Task 5.3**: Agent Lifecycle Management
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 5.2
  - **Success**:
    - Start/stop/pause agents
    - Resource monitoring
    - Performance tracking
    - Auto-scaling based on load
  - **Files**: `src/shared/infrastructure/agents/lifecycle_manager.py`

- [ ] **Task 5.4**: Dynamic Agent Security & Limits
  - **Agent**: deployment-specialist
  - **Time**: 3h
  - **Dependencies**: Task 5.3
  - **Success**:
    - Resource quotas (CPU/memory)
    - Tool access control
    - Rate limiting per agent
    - Sandboxing execution
  - **Files**: `src/shared/infrastructure/security/agent_sandbox.py`

- [ ] **Task 5.5**: Agent Marketplace & Sharing
  - **Agent**: project-coder
  - **Time**: 4h
  - **Dependencies**: Task 5.4
  - **Success**:
    - Export/import agent templates
    - Community agent library
    - Version control for agents
    - Agent performance ratings
  - **Files**: `src/domains/agents/marketplace/`

#### Phase 5 Validation:
- [ ] **Quality Gate**: Dynamic agent creation < 5s
- [ ] **Security Check**: No privilege escalation possible
- [ ] **UX Test**: Non-technical users can create agents
- [ ] **Scale Test**: System handles 50+ dynamic agents

## 🔧 Tools & Resources
- **Required Tools**: Docker, GitHub Actions, PostgreSQL, Redis
- **External Dependencies**: OpenAI API, Google Trends API, Fact-checking APIs
- **Team Skills Needed**: Python/FastAPI, React/TypeScript, Docker, PostgreSQL

## 📊 Success Metrics

### Phase-by-phase KPIs
- **Phase 1**: Infrastructure automated, first deployment successful
- **Phase 2**: 2 agents operational, events flowing end-to-end
- **Phase 3**: Human decisions influence AI workflow
- **Phase 4**: Production-ready z <99.9% uptime
- **Phase 5**: Dynamic agents created via natural language

### Overall Project KPIs
- **Decision Accuracy**: >85% human approval rate
- **Time to Decision**: <5 minutes od discovery do decision
- **System Availability**: >99.9% excluding maintenance
- **Agent Response Time**: <2s dla standard queries

### Quality Indicators
- **Code Coverage**: >80% dla core business logic
- **Test Success Rate**: >95% dla CI/CD pipeline
- **Security Scan**: Zero critical vulnerabilities
- **Performance**: All targets met per phase

## ⚠️ Risk Management

### Identified Risks
1. **AG-UI Protocol Learning Curve** - Mitigation: Start z basic events, iterate
2. **Complex Multi-Agent Coordination** - Mitigation: Incremental agent addition
3. **Digital Ocean Network Issues** - Mitigation: Health checks, auto-recovery
4. **API Rate Limiting (External)** - Mitigation: Caching, backup data sources

### Rollback Plans
- **Phase 1**: Revert do previous infrastructure snapshot
- **Phase 2**: Disable problematic agents, fallback to manual
- **Phase 3**: Bypass human-in-the-loop, auto-approve low-risk
- **Phase 4**: Blue-green deployment z instant rollback
- **Phase 5**: Disable dynamic agent creation, use only predefined agents

### Escalation Paths
- **Technical Issues**: Lead Developer → Senior Architect
- **Infrastructure**: DevOps Lead → Cloud Provider Support
- **Business Logic**: Product Owner → Domain Expert
- **Security**: Security Officer → External Consultant

## 🚀 Quick Start

1. **Clone repository i setup environment**
   ```bash
   git clone <repo>
   cp .env.example .env
   # Configure API keys
   ```

2. **Run development environment**
   ```bash
   docker-compose up -d
   # Wait for services to be healthy
   ```

3. **Verify setup**
   ```bash
   curl http://localhost:8000/health
   # Should return 200 OK
   ```

## 📋 Agent Assignment Strategy

### Kiedy zatrudnić jakiego agenta:

**Phase 1 (Foundation)**:
- `deployment-specialist` dla Tasks 1.0, 1.3, 1.4, 1.7, 1.8
- `project-coder` dla Tasks 1.1, 1.2, 1.5, 1.6

**Phase 2 (Core Agents)**:
- `project-coder` dla wszystkich tasks 2.0-2.8
- Po każdym bloku: `code-reviewer` dla quality gate

**Phase 3 (Advanced)**:
- `project-coder` dla wszystkich tasks 3.0-3.8
- Po każdym bloku: `code-reviewer` + `/agent meta` dla validation

**Phase 4 (Production)**:
- `project-coder` dla Tasks 4.0-4.2
- `deployment-specialist` dla Tasks 4.3-4.6
- `documentation-keeper` dla Task 4.7

### Deployment Strategy:
- **Po każdych 2-3 taskach**: Deploy do droplet dla integration testing
- **Po każdej fazie**: Full regression testing
- **Emergency**: `emergency-system-controller` dostępny 24/7

---

**Kluczowe**: Ten roadmap jest zoptymalizowany dla agent chains. Każdy task ma wyraźnie zdefiniowanego agenta, dependencies i success criteria dla łatwej automatyzacji przez `/nakurwiaj`.