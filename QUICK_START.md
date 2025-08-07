# Quick Start - AI Kolegium Redakcyjne

## 🎯 Cel: Od 0 do produktywnego developera w 30 minut

Ten przewodnik przeprowadzi Cię przez setup środowiska i uruchomienie pierwszego agenta AI w systemie redakcyjnym.

## 📋 Prerequisites

### Wymagane narzędzia:
- **Python 3.11+** - główny język projektu
- **Docker Desktop** - containerized environment
- **Git** - version control
- **VS Code** (opcjonalnie) - IDE z Python extensions

### Wymagane API keys:
```bash
# Będziesz potrzebować:
OPENAI_API_KEY=sk-...        # GPT-4 dla agentów
ANTHROPIC_API_KEY=claude-... # Claude jako fallback (opcjonalnie)
SERPER_API_KEY=...          # Google Search dla Content Scout
```

## ⚡ 30-Minute Setup

### Krok 1: Project Scaffolding (5 min)

```bash
# 1. Zainstaluj CrewAI CLI
pip install crewai[tools]

# 2. Stwórz projekt używając scaffolding
crewai create ai-kolegium-redakcyjne
cd ai-kolegium-redakcyjne

# 3. Podstawowa konfiguracja
cp .env.example .env
# Edytuj .env - dodaj swoje API keys
```

**Rezultat**: Masz gotową strukturę projektu CrewAI z example agents.

### Krok 2: Environment Setup (10 min)

```bash
# 1. Dodaj dependencies dla Vector Wave
echo "
# Vector Wave specific
fastapi==0.109.0
uvicorn[standard]==0.27.0
redis==5.0.1
asyncpg==0.29.0
sqlalchemy==2.0.25
websockets==12.0
pydantic==2.5.3
prometheus-client==0.19.0
" >> requirements.txt

# 2. Zainstaluj dependencies
pip install -r requirements.txt

# 3. Setup local development environment
cat > docker-compose.dev.yml << 'EOF'
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: kolegium_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev:/data

volumes:
  postgres_dev:
  redis_dev:
EOF

# 4. Start infrastructure
docker-compose -f docker-compose.dev.yml up -d
```

**Rezultat**: Masz działającą infrastrukturę (PostgreSQL + Redis).

### Krok 3: First Agent - Content Scout (10 min)

```bash
# 1. Modyfikuj existing agent dla Vector Wave use case
cat > src/ai_kolegium_redakcyjne/agents.py << 'EOF'
from crewai import Agent
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from langchain_openai import ChatOpenAI

def content_scout():
    """Content Scout - odkrywa trending topics"""
    return Agent(
        role='Content Scout',
        goal='Discover trending AI and tech topics with viral potential',
        backstory="""You are an expert content scout with deep knowledge of
        digital trends, social media patterns, and viral content mechanics.
        You excel at finding emerging topics before they go mainstream.""",
        verbose=True,
        allow_delegation=False,
        tools=[
            SerperDevTool(),  # Google Search
            ScrapeWebsiteTool()  # Web scraping
        ],
        llm=ChatOpenAI(model="gpt-4-turbo", temperature=0.1),
        max_iter=3,
        memory=True  # Enable memory for consistency
    )

def trend_analyst():
    """Trend Analyst - analizuje viral potential"""
    return Agent(
        role='Trend Analyst',
        goal='Analyze viral potential and engagement prediction for discovered topics',
        backstory="""You are a data-driven analyst specialized in viral content
        patterns, social media analytics, and engagement prediction. You excel
        at quantifying content potential.""",
        verbose=True,
        allow_delegation=False,
        tools=[SerperDevTool()],
        llm=ChatOpenAI(model="gpt-4", temperature=0.2),
        memory=True
    )
EOF

# 2. Modyfikuj tasks dla Vector Wave workflow
cat > src/ai_kolegium_redakcyjne/tasks.py << 'EOF'
from crewai import Task
from pydantic import BaseModel
from typing import List, Dict, Any

class TopicDiscovery(BaseModel):
    """Structured output for topic discovery"""
    topics: List[Dict[str, Any]]
    total_found: int
    categories: List[str]
    discovery_timestamp: str

class ViralAnalysis(BaseModel):
    """Structured output for viral analysis"""
    topic_id: str
    viral_score: float  # 0-1
    engagement_prediction: Dict[str, int]
    recommendation: str  # approve/reject/review
    reasoning: str

def topic_discovery_task(agent):
    """Task: Discover trending topics"""
    return Task(
        description="""Search for trending topics in AI, technology, and digital culture.
        Focus on topics that have potential for viral spread and high engagement.

        Look for:
        1. Emerging AI technologies and breakthroughs
        2. Tech industry news and developments
        3. Digital culture trends and memes
        4. Startup and business innovations
        5. Social media trending topics

        For each topic, extract:
        - Title and description
        - Source URL
        - Key keywords
        - Initial sentiment
        - Estimated reach/popularity
        """,
        expected_output="List of 5-10 trending topics with metadata",
        agent=agent,
        output_pydantic=TopicDiscovery
    )

def viral_analysis_task(agent):
    """Task: Analyze viral potential"""
    return Task(
        description="""Analyze the discovered topics for viral potential and engagement prediction.

        For each topic, evaluate:
        1. Viral coefficient (how likely to be shared)
        2. Engagement potential (comments, likes, shares)
        3. Controversy level (0-1, where 1 is highly controversial)
        4. Timing relevance (is it timely/relevant now?)
        5. Audience match (fits our target audience?)

        Provide recommendation: approve (high potential), reject (low potential),
        or review (needs human evaluation due to controversy/complexity).
        """,
        expected_output="Viral analysis with scores and recommendations",
        agent=agent,
        output_pydantic=ViralAnalysis,
        context=[topic_discovery_task]  # Depends on discovery results
    )
EOF

# 3. Modyfikuj main crew file
cat > src/ai_kolegium_redakcyjne/crew.py << 'EOF'
from crewai import Crew, Process
from crewai.project import CrewBase, agent, crew, task

from .agents import content_scout, trend_analyst
from .tasks import topic_discovery_task, viral_analysis_task

@CrewBase
class AiKolegiumRedakcyjneCrew():
    """AI Kolegium Redakcyjne crew"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def content_scout(self) -> Agent:
        return content_scout()

    @agent
    def trend_analyst(self) -> Agent:
        return trend_analyst()

    @task
    def topic_discovery_task(self) -> Task:
        return topic_discovery_task(self.content_scout())

    @task
    def viral_analysis_task(self) -> Task:
        return viral_analysis_task(self.trend_analyst())

    @crew
    def crew(self) -> Crew:
        """Creates the AI Kolegium Redakcyjne crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,  # Enable crew memory
            embedder={
                "provider": "openai",
                "config": {"model": "text-embedding-3-small"}
            }
        )
EOF
```

**Rezultat**: Masz działającego Content Scout + Trend Analyst agents.

### Krok 4: Test Run (5 min)

```bash
# 1. Test basic crew functionality
crewai run

# 2. Jeśli wszystko działa, zobaczysz output podobny do:
# [Content Scout] Starting topic discovery...
# [Content Scout] Found 7 trending topics...
# [Trend Analyst] Analyzing viral potential...
# [Trend Analyst] Topic X has viral score 0.8...

# 3. Sprawdź wyniki w terminalu i/lub plikach output
```

**Rezultat**: Pierwszy uruchomienie AI agents system - Content Scout odkrywa topics, Trend Analyst je analizuje.

## 🎉 Success! Co masz teraz:

✅ **Working CrewAI setup** z scaffolding
✅ **2 działających agentów** (Content Scout + Trend Analyst)
✅ **Infrastructure ready** (PostgreSQL + Redis)
✅ **Memory enabled** dla consistency
✅ **Structured outputs** z Pydantic models

## 🚀 Next Steps

Teraz możesz przejść do bardziej zaawansowanych features:

### Immediate (next 30 min):
1. **[AG-UI Integration](./docs/CREWAI_COMPLETE_ANALYSIS.md#ag-ui-event-integration)** - dodaj real-time events
2. **[Web Interface](./docs/implementation-plan.md#frontend-setup)** - React dashboard
3. **[More Agents](./tasks/phase-2-core-agents.md)** - Editorial Strategist + Quality Assessor

### Advanced (next few hours):
1. **[CrewAI Flows](./docs/CREWAI_FLOWS_DECISION_SYSTEM.md)** - decision-making system
2. **[Human-in-the-Loop](./tasks/phase-3-human-in-the-loop.md)** - human collaboration
3. **[Production Deployment](./DEPLOYMENT.md)** - deploy to Digital Ocean

### Expert (next few days):
1. **[Dynamic Agents](./tasks/phase-5-dynamic-agents.md)** - runtime agent creation
2. **[Knowledge Sources](./docs/CREWAI_COMPLETE_ANALYSIS.md#knowledge-sources)** - editorial guidelines
3. **[Multi-LLM Setup](./docs/CREWAI_COMPLETE_ANALYSIS.md#llm-configuration)** - fallback chains

## 🛠️ Troubleshooting

### Common Issues:

**"crewai command not found"**
```bash
pip install --upgrade crewai[tools]
# Make sure you're in correct Python environment
```

**"Database connection failed"**
```bash
# Check if containers are running
docker-compose -f docker-compose.dev.yml ps

# Restart if needed
docker-compose -f docker-compose.dev.yml restart postgres
```

**"OpenAI API errors"**
```bash
# Check your .env file
cat .env | grep OPENAI

# Verify API key is valid
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

**"Import errors"**
```bash
# Make sure you're in project directory
cd ai-kolegium-redakcyjne

# Verify Python path
export PYTHONPATH=$PWD/src:$PYTHONPATH
crewai run
```

## 📚 Further Reading

- **[PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)** - Deep dive into architecture
- **[CREWAI_COMPLETE_ANALYSIS.md](./docs/CREWAI_COMPLETE_ANALYSIS.md)** - All CrewAI features explained
- **[ROADMAP.md](./ROADMAP.md)** - Full implementation plan
- **[CrewAI Documentation](https://docs.crewai.com)** - Official framework docs

---

**Gratulacje!** 🎉 Masz działający AI editorial system. Czas na eksperymentowanie i rozbudowę!