# AI Kolegium Redakcyjne

## 🚨 **CRITICAL: Latest Working Version**
- **Commit**: `4b19b48` (2025-08-06)
- **Status**: ✅ Phase 5 AI Assistant COMPLETED | TRUE Agentic RAG Implementation WORKING
- **Current Phase**: Production Ready - All 12 steps of Phase 5 completed
- **Last Achievement**: Complete AI Assistant integration with conversation memory & comprehensive error handling
- **Key Features**: 
  - TRUE Agentic RAG (agent autonomously queries style guide)
  - AI Assistant for draft editing with natural language
  - Conversation memory (20 messages per session)
  - Streaming responses with SSE
  - Comprehensive error handling & health monitoring
- **Documentation**: See [FEATURE_CUSTOM_IDEAS_ANALYSIS.md](./docs/FEATURE_CUSTOM_IDEAS_ANALYSIS.md)

## 🚀 **Intelligent Editorial System with AI Agent Collaboration**

Zautomatyzowany system redakcyjny gdzie **5 wyspecjalizowanych agentów AI** współpracuje w czasie rzeczywistym przy odkrywaniu trendów, analizie viralowości i podejmowaniu decyzji redakcyjnych z możliwością ludzkiej interwencji.

**Tech Stack**: CrewAI 0.152.0 + Knowledge Base + Docker + PostgreSQL + Digital Ocean

## 🧭 **Start Tutaj**

### 👤 **Jestem nowy w projekcie**
→ **[QUICK_START.md](./QUICK_START.md)** - Od 0 do działającego systemu w 30 minut

### 🏗️ **Chcę zrozumieć architekturę**  
→ **[PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)** - Aktualny stan, tech decisions, metryki

### ⚡ **Chcę implementować features**
→ **[ROADMAP.md](./ROADMAP.md)** - 5 faz implementacji z atomic tasks

### 🔧 **Chcę zgłębić CrewAI**
→ **[docs/CREWAI_COMPLETE_ANALYSIS.md](./docs/CREWAI_COMPLETE_ANALYSIS.md)** - Kompletna analiza framework

## 🎯 **Czym jest AI Kolegium Redakcyjne?**

Inteligentny system który **automatyzuje proces redakcyjny** od odkrycia trendu do decyzji o publikacji.

### 🤖 **10+ Współpracujących Agentów AI**

### Kolegium Redakcyjne (5 agentów)
| Agent | Rola | Główne zadanie |
|-------|------|----------------|
| **Content Scout** | 🔍 Odkrywca | Skanuje internet w poszukiwaniu trending topics |
| **Trend Analyst** | 📊 Analityk | Ocenia viral potential i engagement prediction |
| **Editorial Strategist** | 📝 Strateg | Podejmuje decyzje redakcyjne (z human-in-the-loop) |
| **Quality Assessor** | ✅ Kontroler | Fact-checking, source verification, quality control |
| **Decision Coordinator** | 🎯 Koordynator | Orkiestruje całą współpracę i generuje raporty |

### AI Writing Flow (5 agentów) + Knowledge Base
| Agent | Rola | Główne zadanie | KB Integration |
|-------|------|----------------|----------------|
| **Research Agent** | 🔬 Badacz | Deep research, źródła, fact-finding | ✅ Full KB access |
| **Audience Mapper** | 👥 Strateg | Dopasowanie do grup docelowych | ✅ KB patterns |
| **Content Writer** | ✍️ Pisarz | Generowanie contentu zgodnego ze styleguide | ✅ Style guides |
| **Style Validator** | 📏 Strażnik | Walidacja stylu Vector Wave | ✅ Validation rules |
| **Quality Controller** | 🎯 Kontroler | Finalna ocena jakości i etyki | ✅ Quality metrics |

### ⚡ **Kluczowe Zalety**

- **10x szybsze decyzje redakcyjne** - od discovery do publication w <5 minut
- **Human-in-the-loop** - AI radzi, człowiek decyduje przy kontrowersyjnych tematach  
- **Full audit trail** - każda decyzja AI jest zapisana i wyjaśniona
- **Real-time collaboration** - redaktorzy widzą co myślą agenty w czasie rzeczywistym
- **Scalable** - można dodawać nowych agentów przez natural language

### 🆕 **Najnowsze Features (2025-08-06)**

1. **TRUE Agentic RAG System**
   - **Autonomous Agent**: Agent sam decyduje co i jak szukać w style guide
   - **OpenAI Function Calling**: Natywna integracja z function calling (nie hacki z regex!)
   - **Iterative Search**: 3-5 autonomicznych wyszukiwań per generacja
   - **Zero Hardcoded Rules**: Brak predetermined queries czy fallback rules
   - **Unique Results**: Ten sam input → różne queries → różny content

2. **Complete Style Guide Integration**
   - **180 reguł** ładowanych automatycznie z plików styleguides
   - **ChromaDB Vector Search**: Semantyczne wyszukiwanie reguł
   - **Real Query Logs**: Każde wyszukiwanie agenta widoczne w logach
   - **Dynamic Discovery**: Agent odkrywa różne reguły dla różnych tematów

3. **SSE Streaming dla Batch Analysis**
   - **Real-time progress**: Widać postęp analizy każdego pomysłu
   - **Progress bar ready**: Procenty 0-100% dla UI
   - **Event types**: start, progress, result, error, complete
   - **Cache support**: Wyniki całego batcha są cachowane

4. **AI-Powered Dashboard z Preload**
   - **Instant response**: Preload przy starcie kontenera
   - **Auto-refresh**: Co 20 minut odświeża preloaded data
   - **Smart fallback**: Preload → cache → generate

## 🤖 CrewAI - Serce Systemu

### Dlaczego CrewAI?
- **Role-Based Agents**: Każdy agent ma jasno zdefiniowaną rolę i cel
- **Tool Integration**: Agenci używają własnych narzędzi (RSS, APIs, ML models)
- **Task Chaining**: Zadania mogą zależeć od wyników innych zadań
- **Human Input**: Natywne wsparcie dla ludzkiej interwencji
- **Delegation**: Agenci mogą delegować zadania do innych agentów
- **Knowledge Base**: Zintegrowana baza wiedzy CrewAI z vector search

### Przykład CrewAI Agent
```python
from crewai import Agent, Task, Crew

content_scout = Agent(
    role="Content Scout",
    goal="Discover trending topics with viral potential",
    backstory="Expert at finding emerging trends across multiple sources",
    tools=[rss_checker, social_monitor, keyword_extractor],
    allow_delegation=False
)

# Task with AG-UI event emission
discovery_task = Task(
    description="Find 10 trending AI topics",
    agent=content_scout,
    expected_output="List of topics with metadata",
    callback=lambda result: emit_agui_event("TOPIC_DISCOVERED", result)
)
```

### Multi-Agent Orchestration
```python
editorial_crew = Crew(
    agents=[content_scout, trend_analyst, editorial_strategist, 
            quality_assessor, decision_coordinator],
    tasks=[discover, analyze, review, assess, coordinate],
    process="hierarchical",  # Decision Coordinator manages others
    verbose=True
)

# Execute full editorial pipeline
result = editorial_crew.kickoff()
```
## 🏗️ Nowa Architektura z AG-UI

### Korzyści z AG-UI Integration
- **Real-time streaming** od agentów CrewAI do frontend
- **Bi-directional state sync** - redaktorzy mogą ingerować w proces
- **Generative UI** dla dynamicznych raportów i wizualizacji
- **Human-in-the-loop** collaboration dla decyzji redakcyjnych
- **Frontend tool use** - agenci mogą wywoływać narzędzia frontendowe
- **16 standardowych typów eventów** dla spójnej komunikacji

### Zaktualizowana Architektura
```
┌─────────────────────────────────────────────────────────┐
│                Digital Ocean Droplet                    │
│  ┌─────────────────────────────────────────────────────┐│
│  │              AG-UI Backend Layer                    ││
│  │  ┌─────────────────────────────────────────────────┐││
│  │  │         CrewAI Agents System                   │││
│  │  │  ┌─────────┬─────────┬─────────┬─────────────┐  │││
│  │  │  │ Scout   │ Analyst │Strategist│Quality+Coord│  │││
│  │  │  └─────────┴─────────┴─────────┴─────────────┘  │││
│  │  └─────────────────────────────────────────────────┘││
│  │  ┌─────────────────────────────────────────────────┐││
│  │  │         AG-UI Event Middleware                  │││
│  │  │  • 16 Standard Event Types                     │││
│  │  │  • SSE/WebSocket Transport                     │││
│  │  │  • State Synchronization                       │││
│  │  └─────────────────────────────────────────────────┘││
│  │  ┌─────────────────────────────────────────────────┐││
│  │  │      FastAPI + AG-UI HTTP Implementation       │││
│  │  └─────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │              React Frontend                         ││
│  │  ┌─────────────────────────────────────────────────┐││
│  │  │          CopilotKit Integration                 │││
│  │  │  • Real-time Agent Communication               │││
│  │  │  • Interactive Editorial Dashboard             │││
│  │  │  • Human-in-the-loop Controls                  │││
│  │  └─────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```
## 📡 AG-UI Event Types dla Kolegium Redakcyjnego

### 16 Standardowych Event Types
```python
from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict, Optional

class AGUIEventType(Enum):
    # Core messaging events
    MESSAGE = "message"
    MESSAGE_DELTA = "message_delta"
    
    # State management
    STATE_SYNC = "state_sync"
    STATE_UPDATE = "state_update"
    
    # Tool interaction
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    
    # UI generation
    UI_COMPONENT = "ui_component"
    UI_UPDATE = "ui_update"
    
    # Human interaction
    HUMAN_INPUT_REQUEST = "human_input_request"
    HUMAN_FEEDBACK = "human_feedback"
    
    # Progress tracking
    PROGRESS_UPDATE = "progress_update"
    TASK_COMPLETE = "task_complete"
    
    # Editorial specific
    TOPIC_DISCOVERED = "topic_discovered"
    EDITORIAL_DECISION = "editorial_decision"
    CONTENT_ANALYSIS = "content_analysis"
    QUALITY_ASSESSMENT = "quality_assessment"
```
## 🤖 CrewAI Agents z AG-UI Integration

### Agent 1: Content Scout (Skaut Treści)
```python
content_scout = Agent(
    role='Content Scout z Real-time Updates',
    goal='Zbieranie tematów z live updates dla redaktorów',
    backstory='Doświadczony dziennikarz śledczy z real-time awareness...',
    tools=[WebScrapingTool(), RSSFeedTool(), SocialMediaTool()],
    verbose=True
)
```

**Funkcjonalności:**
- Real-time skanowanie źródeł RSS, social media, portali
- Emisja `TOPIC_DISCOVERED` events dla każdego nowego tematu
- Progress tracking z `PROGRESS_UPDATE` events
- Automatyczna kategoryzacja i wstępna ocena

### Agent 2: Trend Analyst (Analityk Trendów)
```python
trend_analyst = Agent(
    role='Trend Analyst z Analytics',
    goal='Analiza popularności i potencjału viralowego z real-time metrics',
    backstory='Ekspert od trendów cyfrowych z AI-powered insights...',
    tools=[GoogleTrendsTool(), SocialAnalyticsTool(), KeywordTool()],
    verbose=True
)
```

**Funkcjonalności:**
- Google Trends analysis w czasie rzeczywistym
- Social media sentiment monitoring
- Viral potential scoring
- Competitive keyword analysis
### Agent 3: Editorial Strategist (Strateg Redakcyjny) - Human-in-the-Loop
```python
editorial_strategist = Agent(
    role='Editorial Strategist z Human Collaboration',
    goal='Strategiczna ocena tematów z możliwością konsultacji z redaktorami',
    backstory='Doświadczony strateg redakcyjny z intuicją collaborative AI...',
    tools=[EditorialGuidelinesTool(), AudienceAnalysisTool()],
    verbose=True
)
```

**Kluczowe funkcje:**
- Automatyczna ocena zgodności z linią redakcyjną
- `HUMAN_INPUT_REQUEST` dla kontrowersyjnych tematów (controversy_level > 7)
- Real-time collaboration z redaktorami
- Emisja `EDITORIAL_DECISION` events z uzasadnieniem

### Agent 4: Quality Assessor (Oceniacz Jakości)
```python
quality_assessor = Agent(
    role='Quality Assessor z Fact-checking',
    goal='Weryfikacja jakości, wiarygodności i fact-checking',
    backstory='Pedantyczny fact-checker z AI-enhanced verification...',
    tools=[FactCheckingTool(), SourceVerificationTool(), PlagiarismTool()],
    verbose=True
)
```

### Agent 5: Decision Coordinator (Koordynator Decyzji)
```python
decision_coordinator = Agent(
    role='Decision Coordinator z Generative UI',
    goal='Koordynacja decyzji i generowanie dynamicznych raportów',
    backstory='Doświadczony moderator z AI-powered synthesis...',
    tools=[VotingSystemTool(), ConsensusBuilderTool(), ReportGeneratorTool()],
    verbose=True
)
```
## 🖥️ **Demo - Jak to działa?**

### Real-time Editorial Dashboard
```
┌─────────────────────────────────────────────────────────┐
│  🤖 AI Kolegium Redakcyjne - Live Dashboard            │
├─────────────────────┬───────────────────────────────────┤
│ 📈 Trending Topics  │ 🧠 Agent Activity                 │
│                     │                                   │
│ 🔥 "GPT-5 leaked"   │ Content Scout: Found 12 topics   │
│    Viral: 94%       │ Trend Analyst: Analyzing...       │
│    ⚠️ Controversy   │ Editorial: HUMAN INPUT NEEDED    │
│                     │                                   │
│ 🚀 "Apple VR Pro"   │ 💬 Human Decision Required:       │
│    Viral: 87%       │ Topic "GPT-5 leaked" needs review │
│    ✅ Auto-approved  │ Controversy level: 8.2/10        │
├─────────────────────┼───────────────────────────────────┤
│ 📊 Today's Stats    │ 🎯 Decisions Made                │
│ Topics found: 47    │ Auto-approved: 12                │
│ Analyzed: 31        │ Human-reviewed: 3                │
│ Published: 15       │ Rejected: 8                      │
└─────────────────────┴───────────────────────────────────┘
```

## 💻 **Frontend Tech Stack**

### Enhanced React Dashboard
```javascript
import { CopilotKit, CopilotProvider } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { useAGUIConnection } from "./hooks/useAGUIConnection";

const EditorialDashboard = () => {
  const {
    topics,
    agentStatus,
    pendingDecisions,
    emit,
    isConnected
  } = useAGUIConnection();

  return (
    <CopilotProvider runtimeUrl="/api/agui/runtime">
      <div className="editorial-dashboard">
        <div className="main-content">
          <header className="dashboard-header">
            <h1>🤖 AI Kolegium Redakcyjne</h1>
            <StatusIndicator connected={isConnected} />
            <AgentStatusPanel agents={agentStatus} />
          </header>

          <div className="dashboard-grid">
            <TopicStream topics={topics} />
            <PendingDecisions decisions={pendingDecisions} />
            <AgentActivityFeed activities={agentActivities} />
            <GenerativeReports />
          </div>
        </div>
        
        <CopilotSidebar 
          instructions="Asystent redakcyjny AI..." 
          defaultOpen={false} 
        />
      </div>
    </CopilotProvider>
  );
};
```
## ✍️ **AI Writing Flow - Generowanie Contentu**

### Architektura Flow
```
Topic Selection → Research* → Audience Mapping → Draft Generation 
                     ↓                                    ↓
              (*skip for ORIGINAL)              Human Review Loop
                                                         ↓
                                              Style Validation → Quality Check → Publication
```

### Human-in-the-Loop Decision Points
- **Minor edits** → Style validation → Quality check
- **Major changes** → Audience re-alignment → New draft
- **Direction pivot** → New research (or audience for ORIGINAL)

### Integracja z UI
- Przycisk "Wygeneruj draft" w ChatPanel
- Real-time polling statusu generowania
- Interfejs feedbacku z 4 opcjami decyzji
- Metryki jakości (Quality Score, Style Score)

## 🗺️ **Implementation Status**

### ✅ **Phase 1: Foundation** (COMPLETED)
- Digital Ocean infrastructure setup (Droplet: 46.101.156.14)
- Docker + CI/CD pipeline working
- Basic CrewAI agents functional

### ✅ **Phase 2: Core Agents** (COMPLETED)  
- Content Scout + Trend Analyst implemented
- AG-UI event system partially integrated
- PostgreSQL + Redis infrastructure ready
- **AI Writing Flow fully implemented** (5 agents)
- **UI integration with generate-draft endpoints**
- **Human feedback loop operational**

### 🔄 **Phase 3: Integration** (IN PROGRESS)
- Connecting Kolegium Flow with Writing Flow
- WebSocket/SSE for real-time updates
- End-to-end testing

### 📋 **Phase 4-5: Advanced Features** (PLANNED)
- Dynamic agent creation
- Production hardening
- Performance optimization

**Current Status**: System ma pełne Kolegium Redakcyjne (5 agentów) oraz AI Writing Flow (5 agentów). UI jest zintegrowane z endpointami do generowania draftów. Human-in-the-loop feedback działa.

## 💰 **Resource Requirements**

### Infrastructure Costs (Monthly)
- **Digital Ocean**: $48 (4vCPU, 8GB RAM droplet)
- **OpenAI API**: $100-300 (depends on usage)
- **External APIs**: $50 (Google Trends, news sources)
- **Total**: ~$200-400/month for production system

### Development Requirements
- Python 3.11+, Docker, basic React knowledge
- OpenAI API key (required), Claude API key (optional fallback)
- 2-4 weeks development time for full implementation
## 🚀 **Why This Matters?**

### Business Impact
- **10x faster editorial decisions** - traditional newsrooms take hours, AI takes minutes
- **24/7 trend monitoring** - never miss a viral opportunity while you sleep  
- **Consistent quality** - AI doesn't have bad days, bias, or fatigue
- **Scalable editorial team** - handle 100x more content with same human resources

### Technical Innovation
- **First implementation** of CrewAI Flows for editorial decisions
- **Event-driven architecture** with full audit trail
- **Human-AI collaboration** patterns for controversial content
- **Real-time generative UI** for dynamic editorial dashboards

## 🎯 **ROI Potential**

### Dla Redaktorów
- **Real-time visibility** w proces AI decision making
- **Interactive control** nad decyzjami agentów
- **Seamless collaboration** między AI a ludźmi
- **Dynamic reports** dostosowane do aktualnych potrzeb
- **Transparent process** z full audit trail

### Dla Deweloperów
- **Standardized protocol** zamiast custom API
- **Built-in scaling** i performance optimization
- **Easy integration** z popularnymi frameworkami
- **Future-proof** architecture
- **16 event types** pokrywających wszystkie use cases

### Dla Organizacji
- **Transparent AI processes** z full audit trail
- **Flexible workflows** dostosowane do potrzeb
- **Reduced development time** dzięki ready-to-use components
- **Vendor agnostic** solution
- **Cost-effective** scaling

## 🚀 **Get Started Now**

### For Developers:
1. **[Quick Start Guide](./QUICK_START.md)** - 30-minute setup  
2. **[Implementation Roadmap](./ROADMAP.md)** - full development plan
3. **[Technical Deep Dive](./docs/CREWAI_COMPLETE_ANALYSIS.md)** - all CrewAI features

### For Decision Makers:
1. **[Project Context](./PROJECT_CONTEXT.md)** - business case & metrics
2. **[Architecture Overview](./ARCHITECTURE_RECOMMENDATIONS.md)** - technical decisions
3. **[Deployment Guide](./DEPLOYMENT.md)** - production considerations

## 📚 **Complete Documentation**

### 🌟 **Essential Reading**
- **[QUICK_START.md](./QUICK_START.md)** - 30-minute onboarding for new developers
- **[PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)** - Current status, tech stack, metrics  
- **[ROADMAP.md](./ROADMAP.md)** - Implementation plan with atomic tasks

### 🔧 **Technical Deep Dives**  
- **[CREWAI_COMPLETE_ANALYSIS.md](./docs/CREWAI_COMPLETE_ANALYSIS.md)** - Complete CrewAI framework analysis
- **[CREWAI_FLOWS_DECISION_SYSTEM.md](./docs/CREWAI_FLOWS_DECISION_SYSTEM.md)** - Advanced decision-making with Flows
- **[ARCHITECTURE_RECOMMENDATIONS.md](./ARCHITECTURE_RECOMMENDATIONS.md)** - Technical decisions & ADRs
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production deployment guide

### 📋 **Implementation Phases**
- **[Phase 1: Foundation](./tasks/phase-1-foundation.md)** - Infrastructure setup (Blocks 0-4)
- **[Phase 2: Core Agents](./tasks/phase-2-core-agents.md)** - Content Scout + Trend Analyst (Blocks 5-8)  
- **[Phase 3: Human-in-the-Loop](./tasks/phase-3-human-in-the-loop.md)** - Editorial collaboration (Blocks 9-12)
- **[Phase 4: Production](./tasks/phase-4-production.md)** - Quality + Orchestration (Blocks 13-17)
- **[Phase 5: Dynamic Agents](./tasks/phase-5-dynamic-agents.md)** - Runtime agent creation (Blocks 18-21)

### 🌐 **External Resources**
- [CrewAI Documentation](https://docs.crewai.com) - Official framework docs
- [AG-UI Protocol](https://ag-ui.com) - Real-time AI communication standard
- [Vector Wave](https://github.com/vector-wave) - Parent project ecosystem

---

**Autor**: AI Kolegium Team  
**Data utworzenia**: 2025-01-31  
**Ostatnia aktualizacja**: 2025-01-31