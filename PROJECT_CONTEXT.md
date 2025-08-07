# PROJECT CONTEXT - AI Kolegium Redakcyjne

## 🎯 Misja Projektu
Stworzenie inteligentnego systemu wspomagającego decyzje redakcyjne poprzez orkiestrację agentów AI z zachowaniem pełnej transparentności i kontroli przez człowieka.

## 🏗️ Architektura Systemu

### Paradygmat: CrewAI Flows + Event-Driven Architecture
- **CrewAI Flows** - deterministyczne decision-making zamiast basic Crews  
- **Knowledge Sources** - editorial guidelines jako Vector Database
- **4 Memory Types** - short-term, long-term, entity, contextual
- **Multi-LLM Setup** - OpenAI primary, Claude fallback
- **AG-UI Protocol** - real-time communication z frontend
- **Event Sourcing** - full audit trail wszystkich AI decisions

### Stack Technologiczny (Zaktualizowany)
```yaml
AI Framework:
  - CrewAI 0.30.11+ z CLI scaffolding ✅
  - CrewAI Flows dla decision trees ✅ 
  - Built-in tools (SerperDev, ScrapeWebsite, etc.) ✅
  - Knowledge Sources dla editorial guidelines 🔄
  - Multi-LLM setup (OpenAI + Claude fallbacks) 🔄

Backend:
  - Python 3.11 + FastAPI ✅
  - PostgreSQL (event store + crew memory) ✅
  - Redis (cache + AG-UI streams) ✅
  - AG-UI Protocol implementation 🔄
  - OpenTelemetry tracing 📋

Frontend:
  - React 18 + TypeScript 📋
  - CopilotKit integration 📋  
  - AG-UI WebSocket/SSE client 🔄
  - Real-time dashboard components 📋

Infrastructure:
  - Digital Ocean Droplet (46.101.156.14) ✅ [ACTIVE]
  - Docker + GitHub Container Registry ✅
  - Watchtower auto-deployment 🔄
  - GitHub Actions CI/CD ✅
  - Prometheus + Grafana monitoring 📋

Legenda: ✅ Done | 🔄 In Progress | 📋 Planned
```

### 📊 Stan Implementacji (2025-01-31)

**Phase 1: Foundation & Infrastructure**
- [x] Task 1.0: Digital Ocean setup - COMPLETED 2025-01-17
  - Droplet ID: 511009535, IP: 46.101.156.14
  - User: editorial-ai (SSH alias: crew)
  - Python venv: /home/editorial-ai/venv
- [x] Discovery: CrewAI scaffolding approach (2025-01-31)
  - Use `crewai create` instead of custom Clean Architecture
  - Built-in tools replace custom implementations  
  - CrewAI Flows for decision-making replace basic Crews
  - Knowledge Sources for editorial guidelines
- [ ] Task 1.1: CrewAI project scaffolding (UPDATED)
- [ ] Task 1.2: AG-UI Event System integration
- [ ] Task 1.3: Docker containers setup
- [ ] Task 1.4: GitHub Actions CI/CD

## 🎭 Agenci i ich Implementacja (CrewAI)

### 1. Content Scout (IMPLEMENTED)
**CrewAI Agent Configuration**:
- **Role**: "Content Scout"
- **Goal**: "Discover trending AI and tech topics with viral potential"
- **Tools**: SerperDevTool(), ScrapeWebsiteTool()
- **LLM**: GPT-4-turbo (temperature=0.1)
- **Memory**: Enabled (consistency across sessions)
- **Output**: Pydantic model TopicDiscovery

### 2. Trend Analyst (IMPLEMENTED)  
**CrewAI Agent Configuration**:
- **Role**: "Trend Analyst"
- **Goal**: "Analyze viral potential and engagement prediction"
- **Tools**: SerperDevTool(), Google Trends integration
- **LLM**: GPT-4 (temperature=0.2)
- **Memory**: Enabled
- **Output**: Pydantic model ViralAnalysis

### 3. Editorial Strategist (PLANNED - CrewAI Flow)
**Implementation**: CrewAI Flow z conditional routing
- **Flow**: EditorialDecisionFlow
- **Routing**: @router based on controversy_level
- **Human-in-the-Loop**: Native Flow support
- **Decision Tree**: approve/reject/human_review paths

### 4. Quality Assessor (PLANNED)
**CrewAI Agent Configuration**:
- **Tools**: Fact-checking APIs, source verification
- **Knowledge Source**: Editorial guidelines vector DB
- **Integration**: AG-UI events dla quality scores

### 5. Decision Coordinator (PLANNED - Flow Orchestrator)
**Implementation**: Main orchestration Flow
- **Coordinates**: All other agents via Flow system
- **Generates**: Dynamic UI components
- **Outputs**: Final editorial decisions + reports

## 🔄 Event Flow Architecture

```mermaid
graph TD
    A[Content Scout] -->|TOPIC_DISCOVERED| B[Event Store]
    B --> C[Trend Analyst]
    C -->|CONTENT_ANALYSIS| B
    B --> D[Editorial Strategist]
    D -->|HUMAN_INPUT_REQUEST| E[Frontend]
    E -->|HUMAN_FEEDBACK| B
    D -->|EDITORIAL_DECISION| B
    B --> F[Quality Assessor]
    F -->|QUALITY_ASSESSMENT| B
    B --> G[Decision Coordinator]
    G -->|UI_COMPONENT| E
    G -->|TASK_COMPLETE| H[Publication Pipeline]
```

## 📊 Kluczowe Metryki

### Business KPIs
- **Decision Accuracy**: >85% human approval rate
- **Time to Decision**: <5 minut od discovery do decision
- **Human Intervention Rate**: 15-25% (optimal dla controversial topics)
- **False Positive Rate**: <10% (topics rejected after analysis)

### Technical KPIs  
- **Event Processing Latency**: <100ms p95
- **WebSocket Connection Stability**: >99.5% uptime
- **Agent Response Time**: <2s dla standard queries
- **System Availability**: >99.9% excluding planned maintenance

### Quality KPIs
- **Code Coverage**: >80% dla core business logic
- **Deployment Frequency**: Multiple per day (small increments)
- **Mean Time to Recovery**: <15 minut
- **Change Failure Rate**: <5%

## 🚀 Deployment Strategy

### Container-First Approach
1. **Local Development**: Docker Compose z hot-reload
2. **CI Pipeline**: GitHub Actions → GitHub Container Registry
3. **Production**: Watchtower auto-deploy z ghcr.io
4. **Zero Manual Building**: Wszystko automatyczne

### Deployment Bloki
- **Blok 0-2**: Core infrastructure + basic AG-UI
- **Blok 3-5**: First agent (Content Scout) + tests
- **Blok 6-8**: Analytics agent + frontend integration  
- **Blok 9-11**: Human-in-the-loop workflow
- **Blok 12-14**: Quality assurance + orchestration
- **Blok 15-17**: Production hardening + monitoring

## 🔐 Security & Compliance

### Authentication & Authorization
- **JWT tokens** dla API access
- **Role-based access** (admin, editor, viewer)
- **Rate limiting** per user i per endpoint
- **CORS** properly configured

### Data Protection
- **Encryption at rest** dla sensitive data
- **TLS 1.3** dla all communications
- **PII anonymization** w event logs
- **GDPR compliance** dla EU users

## 🎯 Success Criteria

### Phase 1 (Foundation)
- [ ] AG-UI events flow end-to-end
- [ ] Basic Content Scout operational
- [ ] CI/CD pipeline delivers to production
- [ ] Monitoring dashboard shows key metrics

### Phase 2 (Multi-Agent)
- [ ] All 5 agents operational
- [ ] Human-in-the-loop workflow complete
- [ ] Event sourcing captures full audit trail
- [ ] Performance targets met

### Phase 3 (Production)
- [ ] Security hardening complete  
- [ ] Load testing passed (100 concurrent users)
- [ ] Documentation complete
- [ ] Training materials ready

## 🎨 Conventions

### Code Organization
```
src/
├── domains/           # Domain logic (DDD)
│   ├── content/
│   ├── analytics/
│   ├── editorial/
│   ├── quality/
│   └── orchestration/
├── infrastructure/    # External concerns
│   ├── agui/
│   ├── database/
│   ├── cache/
│   └── monitoring/
├── application/       # Use cases
└── interfaces/        # Controllers, DTOs
```

### Git Workflow
- **main** branch - production ready
- **develop** branch - integration
- **feature/** branches - atomic changes
- **hotfix/** branches - emergency fixes

### Commit Messages
```
feat(content): add RSS feed discovery
fix(agui): resolve WebSocket connection drops  
docs(readme): update deployment instructions
test(analytics): add viral potential scoring tests
```

## 🔧 Development Guidelines

### Agent Implementation Pattern
```python
class Agent(BaseAgent):
    async def execute(self, context: Context) -> AgentResult:
        # 1. Emit PROGRESS_UPDATE
        # 2. Perform core logic
        # 3. Emit domain-specific events
        # 4. Return structured result
```

### Event Handling Pattern
```python
@event_handler(AGUIEventType.TOPIC_DISCOVERED)
async def handle_topic_discovery(event: AGUIEvent):
    # 1. Validate event data
    # 2. Store in event store
    # 3. Trigger downstream processing
    # 4. Update read models
```

### Testing Strategy
- **Unit Tests**: Domain logic isolation
- **Integration Tests**: Agent communication
- **E2E Tests**: Full workflow scenarios
- **Performance Tests**: Load + stress testing

## 📈 Roadmap Overview (Zaktualizowany)

### Week 1-2: CrewAI Foundation
- ✅ CrewAI project scaffolding (`crewai create`)
- ✅ Content Scout + Trend Analyst agents
- 🔄 AG-UI event integration
- 📋 Docker containerization
- 📋 GitHub Actions CI/CD

### Week 3-4: Advanced Agents + Flows
- 📋 EditorialDecisionFlow implementation
- 📋 Human-in-the-loop workflows
- 📋 Knowledge Sources setup
- 📋 Quality Assessor agent
- 📋 React frontend dashboard

### Week 5-6: Production Features
- 📋 Decision Coordinator Flow
- 📋 Multi-LLM fallback setup
- 📋 4 memory types configuration
- 📋 Performance optimization
- 📋 Security hardening

### Week 7: Dynamic Agents
- 📋 Runtime agent creation
- 📋 Natural language agent parser
- 📋 Agent marketplace
- 📋 Full documentation
- 📋 Production deployment

---

**Kluczowe Principy (Zaktualizowane)**:
1. **CrewAI-First**: Scaffolding zamiast custom architecture
2. **Flows-First**: Deterministic decision trees zamiast autonomous agents
3. **Knowledge-First**: Vector DB z editorial guidelines
4. **Memory-First**: 4 typy pamięci dla consistency
5. **Human-First**: AI analizuje, człowiek decyduje przy kontrowersyjnych
6. **Event-First**: AG-UI Protocol dla real-time collaboration
7. **Container-First**: GitHub Container Registry + Watchtower auto-deploy