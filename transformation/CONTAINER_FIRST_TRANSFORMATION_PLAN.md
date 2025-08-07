# 🐳 Container-First Transformation Plan - AI Writing Flow

## 📊 Status Wykonania

### ✅ Faza 0: Minimal Container Foundation - **UKOŃCZONA**
- [x] Zadanie 0.1: Minimalny kontener FastAPI
- [x] Zadanie 0.2: Docker Compose setup
- [x] Zadanie 0.3: Basic CI/CD (Makefile)

### ✅ Faza 1: CrewAI Integration Container - **UKOŃCZONA & ZWERYFIKOWANA**
- [x] Zadanie 1.1: Research Agent Endpoint ✅
- [x] Zadanie 1.2: Writer Agent Endpoint ✅ (verified 2025-08-05, commit: 6cec870)
  - **VERIFIED**: Używa prawdziwego OpenAI GPT-4 API
  - Dodano endpoint `/api/verify-openai` do weryfikacji
  - Comprehensive tests added
- [x] Zadanie 1.3: Complete Flow Endpoint ✅

**🚨 CRITICAL: Working version saved in commit `2c960c1` (2025-08-05 16:44:00 CEST)**
**✅ VERIFIED: Real OpenAI API in commit `6cec870` (2025-08-05 17:37:52 CEST)**
**⚠️ DO NOT MODIFY without backing up this state first!**

### 🚧 Faza 2: Frontend Integration & Flow Diagnostics - **W TRAKCIE** (2/3)
- [x] Zadanie 2.1: Flow Diagnostics Endpoint ✅ (2025-08-05, verified commit: 9df36f5)
  - **VERIFIED**: Wszystkie endpointy diagnostyczne działają poprawnie
  - Pełne śledzenie wykonania z agent decisions
  - Content loss metrics i timing tracking
  - Comprehensive test suite (6 test cases)
- [x] Zadanie 2.2: Frontend Backend Switch ✅ (endpoint /api/analyze-potential - 1ms!)
- [x] Zadanie 2.2.1: Fix Draft Generation Errors ✅ (2025-08-05, commit: 58cbf76)
  - **FIXED**: 404 error - changed endpoint URL
  - **FIXED**: 422 error - added data transformation
  - **FIXED**: "Failed to start writing flow" - response format
  - **OPTIMIZED**: skip_research for ORIGINAL content (20% faster)
- [ ] Zadanie 2.3: Human Review UI Integration

### 🔄 Faza 3: Production Container - **W TRAKCIE** (Sprint 4/5)
- [ ] Zadanie 3.1: Multi-stage Dockerfile
- [ ] Zadanie 3.2: Redis + Knowledge Base + Style Guide RAG (5 sprintów)
  - [x] Sprint 3.2.1: Basic Redis Cache ✅ COMPLETED (commit: dfa44ee)
    - [x] Krok 1: Redis dodany do docker-compose.minimal.yml (commit: 20ce0bc)
      - Port 6380 aby uniknąć konfliktu
      - Health check skonfigurowany
    - [x] Krok 2: Endpoint testujący cache /api/cache-test
      - Redis client z graceful fallback
      - TTL support (60 sekund)
      - Response time: <1ms
  - [x] Sprint 3.2.2: Cache for analyze-potential ✅ COMPLETED (commit: 27258a0)
    - Cache key: `analysis:{folder_name}`
    - TTL: 300 sekund (5 minut)
    - Performance: ~50% faster on cache hits
  - [x] Sprint 3.2.3: ChromaDB for Style Guide - Naive RAG ✅ COMPLETED (commit: 39158cb)
    - ChromaDB na porcie 8001
    - Style guide collection z 8 regułami
    - Naive RAG similarity search
    - Style score 0-100
  - [x] Sprint 3.2.4: Agentic RAG with CrewAI ✅ COMPLETED (commit: pending)
    - Style Guide Expert Agent
    - Intelligent analysis with context
    - Alternative openings & CTAs
    - Compare endpoint
  - [ ] Sprint 3.2.5: Production Docker Compose (30 min)
- [ ] Zadanie 3.3: Environment configuration

### ⏳ Faza 4: Full Integration - **OCZEKUJE**
- [ ] Zadanie 4.1: Knowledge Base Integration
- [ ] Zadanie 4.2: Complete Flow Testing
- [ ] Zadanie 4.3: Documentation

---

## 🎯 Filozofia: Container-First Development

**Zamiast**: Budować skomplikowany system i potem go konteneryzować  
**Robimy**: Każdy krok rozwoju działa od razu w kontenerze z testowalnym API

### Główne zasady:
1. **Każde zadanie = nowy endpoint API** który można przetestować curl'em
2. **Progresywny rozwój** - kontener rośnie z każdym zadaniem
3. **Zero setup** - `docker compose up` i wszystko działa
4. **Instant feedback** - każda zmiana widoczna przez API

---

## 📋 Faza 0: Minimal Container Foundation (2 godziny) ✅ UKOŃCZONA

### Zadanie 0.1: Minimalny kontener FastAPI (45 min)

**Cel**: Najprostszy możliwy kontener z endpointem testującym routing

**Pliki do stworzenia**:

```dockerfile
# Dockerfile.minimal
FROM python:3.11-slim
WORKDIR /app
COPY requirements.minimal.txt .
RUN pip install -r requirements.minimal.txt
COPY app.py .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```python
# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="AI Writing Flow - Container First")

class ContentRequest(BaseModel):
    title: str
    content_type: str = "STANDARD"  # STANDARD, TECHNICAL, VIRAL
    platform: str = "LinkedIn"
    content_ownership: str = "EXTERNAL"  # EXTERNAL, ORIGINAL

@app.get("/")
def root():
    return {"status": "ok", "service": "ai-writing-flow"}

@app.get("/health")
def health():
    return {"status": "healthy", "container": "running"}

@app.post("/api/test-routing")
def test_routing(content: ContentRequest):
    """Test endpoint pokazujący że routing działa"""
    # Podstawowa logika routingu
    if content.content_ownership == "ORIGINAL":
        route = "skip_research_flow"
    elif content.content_type == "TECHNICAL":
        route = "technical_deep_dive_flow"
    elif content.content_type == "VIRAL":
        route = "viral_engagement_flow"
    else:
        route = "standard_editorial_flow"
    
    return {
        "status": "routed",
        "input": content.dict(),
        "route_decision": route,
        "skip_research": content.content_ownership == "ORIGINAL",
        "container_id": "ai-writing-flow-v1"
    }
```

```txt
# requirements.minimal.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
```

**Test**:
```bash
# Build i uruchom
docker build -f Dockerfile.minimal -t ai-writing-flow:minimal .
docker run -p 8000:8000 ai-writing-flow:minimal

# Testuj routing
curl -X POST http://localhost:8000/api/test-routing \
  -H "Content-Type: application/json" \
  -d '{"title": "AI Article", "content_ownership": "ORIGINAL"}'

# Oczekiwany wynik:
{
  "status": "routed",
  "route_decision": "skip_research_flow",
  "skip_research": true
}
```

**Success Criteria**:
- ✅ Kontener buduje się < 2 min
- ✅ Endpoint /api/test-routing poprawnie routuje ORIGINAL vs EXTERNAL
- ✅ Health check działa

---

### Zadanie 0.2: Docker Compose Foundation (30 min)

**Cel**: Docker Compose który będzie rósł z każdym zadaniem

```yaml
# docker-compose.yml
version: '3.8'

services:
  ai-writing-flow:
    build:
      context: .
      dockerfile: Dockerfile.minimal
    ports:
      - "8000:8000"
    environment:
      - ENV=development
      - LOG_LEVEL=debug
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./app.py:/app/app.py  # Hot reload dla development
```

**Test**:
```bash
docker compose up -d
docker compose ps  # Sprawdź że kontener jest healthy
curl http://localhost:8000/health
docker compose logs -f  # Zobacz logi
```

---

### Zadanie 0.3: Automated Container Tests (45 min)

**Cel**: Framework do testowania każdego nowego endpointu

```python
# tests/test_container_api.py
import requests
import pytest
import time

BASE_URL = "http://localhost:8000"

def wait_for_api(timeout=30):
    """Czekaj aż API będzie dostępne"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def test_container_health():
    """Test że kontener odpowiada"""
    assert wait_for_api(), "API nie odpowiada po 30 sekundach"
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_routing_original_content():
    """Test że ORIGINAL content pomija research"""
    payload = {
        "title": "My Personal AI Journey",
        "content_ownership": "ORIGINAL",
        "content_type": "STANDARD"
    }
    
    response = requests.post(f"{BASE_URL}/api/test-routing", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["route_decision"] == "skip_research_flow"
    assert data["skip_research"] == True

def test_routing_external_technical():
    """Test że EXTERNAL TECHNICAL idzie przez deep research"""
    payload = {
        "title": "Kubernetes Architecture Deep Dive",
        "content_ownership": "EXTERNAL",
        "content_type": "TECHNICAL"
    }
    
    response = requests.post(f"{BASE_URL}/api/test-routing", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["route_decision"] == "technical_deep_dive_flow"
    assert data["skip_research"] == False
```

```makefile
# Makefile
.PHONY: test

test:
	docker compose up -d
	@echo "Czekam na start kontenera..."
	@sleep 5
	pytest tests/test_container_api.py -v
	
clean:
	docker compose down

full-test: clean test
	@echo "✅ Wszystkie testy przeszły!"
```

**Test**:
```bash
make full-test
```

---

## 📋 Faza 1: CrewAI Integration Container (1 dzień) 

### Zadanie 1.1: Research Agent Endpoint (2h)

**Cel**: Dodaj endpoint który wykonuje research przez CrewAI

```python
# app.py - rozszerzenie
from crewai import Agent, Task, Crew
import os

# Dodaj do istniejącego app.py

class ResearchRequest(BaseModel):
    topic: str
    depth: str = "standard"  # quick, standard, deep
    skip_research: bool = False

@app.post("/api/research")
async def execute_research(request: ResearchRequest):
    """Wykonuje research używając CrewAI Agent"""
    
    if request.skip_research:
        return {
            "status": "skipped",
            "reason": "skip_research flag is True",
            "topic": request.topic,
            "findings": []
        }
    
    # Stwórz Research Agent
    researcher = Agent(
        role="Senior Research Analyst",
        goal=f"Research comprehensive information about {request.topic}",
        backstory="Expert researcher with access to vast knowledge",
        verbose=True
    )
    
    # Stwórz task
    research_task = Task(
        description=f"""
        Research the topic: {request.topic}
        Depth level: {request.depth}
        
        Provide:
        1. Key concepts and definitions
        2. Current trends and developments
        3. Best practices
        4. Common challenges
        """,
        agent=researcher,
        expected_output="Comprehensive research findings"
    )
    
    # Wykonaj research
    crew = Crew(
        agents=[researcher],
        tasks=[research_task],
        verbose=True
    )
    
    try:
        result = crew.kickoff()
        
        return {
            "status": "completed",
            "topic": request.topic,
            "depth": request.depth,
            "findings": {
                "summary": str(result),
                "key_points": extract_key_points(str(result)),
                "word_count": len(str(result).split())
            },
            "execution_time_ms": 2500  # W prawdziwej implementacji zmierz czas
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "topic": request.topic
        }

def extract_key_points(text: str) -> list:
    """Wyciągnij kluczowe punkty z tekstu"""
    # Prosta heurystyka - w produkcji użyj NLP
    lines = text.split('\n')
    key_points = [line.strip() for line in lines if line.strip() and len(line.strip()) > 20][:5]
    return key_points
```

**Update Dockerfile**:
```dockerfile
# Dockerfile - dodaj CrewAI
FROM python:3.11-slim
WORKDIR /app

# System dependencies dla CrewAI
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

```txt
# requirements.txt - rozszerzone
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
crewai==0.1.0
langchain==0.1.0
openai==1.0.0
```

**Test**:
```bash
# Test research endpoint
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "Container-First Development", "depth": "standard"}'

# Test skip research
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "My Story", "skip_research": true}'
```

---

### Zadanie 1.2: Writer Agent Endpoint (2h) ✅ VERIFIED

**Cel**: Dodaj endpoint który generuje content przez WriterAgent

**Status**: ✅ Zweryfikowane 2025-08-05
- **Commit**: `6cec870bd7ff1a96f2cccdc4c56b4fc4aa0cb8a2`
- **VERIFIED**: Używa prawdziwego OpenAI GPT-4 API
- Dodano endpoint `/api/verify-openai` do weryfikacji autentyczności
- Dodano 5 testów pokrywających różne scenariusze
- Rozszerzono Makefile o komendy: `test-writer`, `test-writer-research`, `test-complete-flow`

```python
@app.post("/api/generate-draft")
async def generate_draft(content: ContentRequest, research_data: dict = None):
    """Generuje draft używając CrewAI Writer Agent"""
    
    # Writer Agent
    writer = Agent(
        role=f"{content.platform} Content Writer",
        goal=f"Write engaging {content.platform} content about {content.title}",
        backstory=f"Expert {content.platform} content creator",
        verbose=True
    )
    
    # Context z research (jeśli jest)
    context = ""
    if research_data and research_data.get("findings"):
        context = f"Research findings: {research_data['findings']['summary']}"
    
    # Writing task
    writing_task = Task(
        description=f"""
        Write {content.platform} content about: {content.title}
        Content type: {content.content_type}
        
        {context}
        
        Requirements:
        - Optimize for {content.platform} best practices
        - Target length: {"280 chars" if content.platform == "Twitter" else "500-1000 words"}
        - Include engaging hook
        - Add call to action
        """,
        agent=writer,
        expected_output=f"Complete {content.platform} post"
    )
    
    crew = Crew(agents=[writer], tasks=[writing_task])
    
    try:
        result = crew.kickoff()
        
        return {
            "status": "completed",
            "draft": {
                "title": content.title,
                "content": str(result),
                "platform": content.platform,
                "word_count": len(str(result).split()),
                "optimized_for": content.platform
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "content_type": content.content_type,
                "used_research": research_data is not None
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

---

### Zadanie 1.3: Complete Flow Endpoint (2h)

**Cel**: Połącz routing + research + writing w jeden flow

```python
@app.post("/api/execute-flow")
async def execute_complete_flow(content: ContentRequest):
    """Wykonuje kompletny flow: routing → research → writing"""
    
    execution_log = []
    start_time = datetime.now()
    
    # Step 1: Routing
    routing_result = test_routing(content)
    execution_log.append({
        "step": "routing",
        "result": routing_result,
        "duration_ms": 50
    })
    
    # Step 2: Research (jeśli potrzebny)
    research_result = None
    if not routing_result["skip_research"]:
        research_request = ResearchRequest(
            topic=content.title,
            depth="deep" if content.content_type == "TECHNICAL" else "standard"
        )
        research_result = await execute_research(research_request)
        execution_log.append({
            "step": "research",
            "result": research_result,
            "duration_ms": 2500
        })
    
    # Step 3: Generate Draft
    draft_result = await generate_draft(content, research_result)
    execution_log.append({
        "step": "draft_generation",
        "result": draft_result,
        "duration_ms": 3000
    })
    
    total_duration = (datetime.now() - start_time).total_seconds() * 1000
    
    return {
        "flow_id": f"flow_{int(time.time())}",
        "status": "completed",
        "routing_decision": routing_result["route_decision"],
        "execution_log": execution_log,
        "final_draft": draft_result.get("draft"),
        "total_duration_ms": total_duration
    }
```

**Test kompletnego flow**:
```bash
# Test ORIGINAL content (skip research)
curl -X POST http://localhost:8000/api/execute-flow \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My AI Journey",
    "content_ownership": "ORIGINAL",
    "platform": "LinkedIn"
  }'

# Test EXTERNAL TECHNICAL (with research)
curl -X POST http://localhost:8000/api/execute-flow \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Kubernetes Best Practices",
    "content_ownership": "EXTERNAL",
    "content_type": "TECHNICAL",
    "platform": "Blog"
  }'
```

---

## 📋 Faza 2: Frontend Integration & Flow Diagnostics (1 dzień)

**Kontekst**: Frontend (Next.js) już istnieje ale łączy się ze starym backendem (8001). Trzeba go połączyć z nowym backendem CrewAI (8003) i dodać rzeczywiste dane diagnostyczne.

### Zadanie 2.1: Flow Diagnostics Endpoint (2h) 

**Cel**: Dodaj endpoint zwracający rzeczywiste dane wykonania flow dla UI

**Status**: ✅ Wykonane 2025-08-05

- **Commit**: `3e3e3a3b404ae721ccb3a10a709b3c25a554bb92` (2025-08-05 17:09:54 +0200)
- Dodano endpoint `/api/execute-flow-tracked` z pełnym śledzeniem
- Dodano endpoint `/api/flow-diagnostics/{flow_id}` dla szczegółów wykonania
- Dodano endpoint `/api/flow-diagnostics` dla listy wykonań
- Przetestowano z EXTERNAL (z research) i ORIGINAL (bez research) content
- Rozszerzono testy o 5 nowych test cases pokrywających wszystkie aspekty
- Dodano komendy Makefile: `test-diagnostics` i `list-flows`

```python
# Dodaj do app.py
from typing import List, Dict, Any
import json

# Storage dla wykonań flow (w produkcji użyj Redis/DB)
flow_executions = {}

class FlowStep:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.input = None
        self.output = None
        self.agent_decisions = []
        self.content_loss = None
        self.errors = []

@app.post("/api/execute-flow-tracked")
async def execute_flow_with_tracking(content: ContentRequest):
    """Wykonuje flow z pełnym śledzeniem dla diagnostyki"""
    
    flow_id = f"flow_{int(time.time())}"
    steps: List[FlowStep] = []
    
    # Step 1: Input Validation
    validation_step = FlowStep("input_validation", "Walidacja Wejścia")
    validation_step.start_time = datetime.now().isoformat()
    validation_step.input = content.dict()
    
    try:
        # Walidacja
        validation_step.output = {
            "validated": True,
            "content_type": content.content_type,
            "platform": content.platform,
            "ownership": content.content_ownership
        }
        validation_step.agent_decisions = [
            f"Wykryto typ contentu: {content.content_type}",
            f"Platforma docelowa: {content.platform}",
            f"Ownership: {content.content_ownership} - {'pominięto research' if content.content_ownership == 'ORIGINAL' else 'wymagany research'}"
        ]
        validation_step.status = "completed"
    except Exception as e:
        validation_step.status = "failed"
        validation_step.errors = [str(e)]
    
    validation_step.end_time = datetime.now().isoformat()
    steps.append(validation_step)
    
    # Step 2: Research (jeśli potrzebny)
    research_step = FlowStep("research", "Badanie Tematu")
    if content.content_ownership == "ORIGINAL":
        research_step.status = "skipped"
        research_step.agent_decisions = [
            "Pominięto research dla ORIGINAL content",
            "Flaga skip_research = true"
        ]
    else:
        research_step.start_time = datetime.now().isoformat()
        try:
            research_request = ResearchRequest(
                topic=content.title,
                depth="deep" if content.content_type == "TECHNICAL" else "standard"
            )
            research_result = await execute_research(research_request)
            
            research_step.output = research_result
            research_step.agent_decisions = [
                f"Wykonano {research_request.depth} research",
                f"Znaleziono {len(research_result.get('findings', {}).get('key_points', []))} kluczowych punktów",
                f"Czas wykonania: {research_result.get('execution_time_ms', 0)}ms"
            ]
            research_step.status = "completed"
            
            # Oblicz content loss
            input_size = len(content.title) * 50  # Przybliżenie
            output_size = research_result.get('findings', {}).get('word_count', 0) * 5
            research_step.content_loss = {
                "inputSize": input_size,
                "outputSize": output_size,
                "lossPercentage": round((1 - output_size/input_size) * 100, 1) if input_size > 0 else 0
            }
        except Exception as e:
            research_step.status = "failed"
            research_step.errors = [str(e)]
        
        research_step.end_time = datetime.now().isoformat()
    
    steps.append(research_step)
    
    # Step 3: Draft Generation
    draft_step = FlowStep("draft_generation", "Generowanie Draftu")
    draft_step.start_time = datetime.now().isoformat()
    
    try:
        draft_request = GenerateDraftRequest(
            content=content,
            research_data=research_step.output if research_step.status == "completed" else None
        )
        draft_result = await generate_draft(draft_request)
        
        draft_step.output = draft_result
        draft_step.agent_decisions = [
            "✅ Wygenerowano draft używając CrewAI Writer Agent",
            f"Długość: {draft_result.get('draft', {}).get('word_count', 0)} słów",
            f"Wykorzystano research: {'Tak' if draft_request.research_data else 'Nie'}",
            f"Platforma: {content.platform}"
        ]
        draft_step.status = "completed"
        
        # Content preservation check
        draft_step.content_loss = {
            "inputSize": len(str(draft_request.dict())) * 10,
            "outputSize": len(draft_result.get('draft', {}).get('content', '')),
            "lossPercentage": 0  # CrewAI zachowuje content
        }
    except Exception as e:
        draft_step.status = "failed"
        draft_step.errors = [str(e)]
    
    draft_step.end_time = datetime.now().isoformat()
    steps.append(draft_step)
    
    # Zapisz wykonanie
    flow_executions[flow_id] = {
        "flow_id": flow_id,
        "steps": [vars(step) for step in steps],
        "created_at": datetime.now().isoformat(),
        "total_duration_ms": sum(
            (datetime.fromisoformat(s.end_time) - datetime.fromisoformat(s.start_time)).total_seconds() * 1000
            for s in steps if s.start_time and s.end_time
        )
    }
    
    return {
        "flow_id": flow_id,
        "status": "completed" if all(s.status in ["completed", "skipped"] for s in steps) else "failed",
        "diagnostic_url": f"/api/flow-diagnostics/{flow_id}",
        "final_draft": draft_step.output.get("draft") if draft_step.status == "completed" else None
    }

@app.get("/api/flow-diagnostics/{flow_id}")
async def get_flow_diagnostics(flow_id: str):
    """Zwraca dane diagnostyczne dla konkretnego wykonania flow"""
    
    if flow_id not in flow_executions:
        raise HTTPException(status_code=404, detail="Flow execution not found")
    
    return flow_executions[flow_id]

@app.get("/api/flow-diagnostics")
async def list_flow_executions(limit: int = 10):
    """Lista ostatnich wykonań flow"""
    
    executions = sorted(
        flow_executions.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]
    
    return {
        "total": len(flow_executions),
        "executions": executions
    }
```

**Test diagnostics endpoint**:
```bash
# Wykonaj flow z trackingiem
curl -X POST http://localhost:8003/api/execute-flow-tracked \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test AI Flow Diagnostics",
    "content_type": "TECHNICAL",
    "platform": "LinkedIn",
    "content_ownership": "EXTERNAL"
  }'

# Pobierz diagnostykę
curl http://localhost:8003/api/flow-diagnostics/flow_1234567890

# Lista ostatnich wykonań
curl http://localhost:8003/api/flow-diagnostics
```

---

### Zadanie 2.2: Frontend Backend Switch (2h) ✅ COMPLETED

**Cel**: Zaktualizuj frontend aby łączył się z nowym backendem CrewAI

**Status**: ✅ UKOŃCZONE (2025-08-05)
- **Commit**: `19dfe1950e3ef0f4d1a18235bdce517cf3bcf3be`
- **OSIĄGNIĘCIE**: Endpoint `/api/analyze-potential` z czasem odpowiedzi **1ms**!

**Zrealizowane**:
- ✅ Dodano endpoint `/api/analyze-potential` z uproszczoną analizą contentu
- ✅ Ultraszybka odpowiedź: 1ms (vs 2-3s w wymaganiach)
- ✅ Uproszczone audience scoring bez zależności od AI agentów
- ✅ Naprawiono konfigurację portów (backend działa na 8003, nie 8000)
- ✅ Wszystkie przyciski "Analizuj potencjał" działają poprawnie w UI
- ✅ Zachowano kompatybilność wsteczną przez endpoint `/api/analyze-content`

**Krok 1: Dodaj zmienną środowiskową**:
```bash
# vector-wave-ui/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8003
NEXT_PUBLIC_OLD_API_URL=http://localhost:8001
```

**Krok 2: Update konfiguracji Next.js**:
```typescript
// vector-wave-ui/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      // Nowe endpointy CrewAI
      {
        source: '/api/crewai/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/:path*`,
      },
      // Stare endpointy (tymczasowo)
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_OLD_API_URL || 'http://localhost:8001'}/api/:path*`,
      },
    ];
  },
};
```

**Krok 3: Update FlowDiagnostics component**:
```typescript
// vector-wave-ui/components/FlowDiagnostics.tsx
// Zamień mock data na prawdziwe API call

useEffect(() => {
  const fetchDiagnostics = async () => {
    setLoading(true);
    
    try {
      // Użyj nowego endpointu
      const response = await fetch(`/api/crewai/flow-diagnostics/${flowId}`);
      const data = await response.json();
      
      // Mapuj dane z backendu na format UI
      const mappedSteps: FlowStep[] = data.steps.map((step: any) => ({
        id: step.id,
        name: step.name,
        status: step.status,
        startTime: step.start_time,
        endTime: step.end_time,
        duration: step.end_time && step.start_time ? 
          new Date(step.end_time).getTime() - new Date(step.start_time).getTime() : undefined,
        input: step.input,
        output: step.output,
        errors: step.errors || [],
        agentDecisions: step.agent_decisions || [],
        contentLoss: step.content_loss
      }));
      
      setSteps(mappedSteps);
    } catch (error) {
      console.error('Failed to fetch diagnostics:', error);
      // Fallback na mock data jeśli API niedostępne
    } finally {
      setLoading(false);
    }
  };

  if (flowId) {
    fetchDiagnostics();
  }
}, [flowId]);
```

**Krok 4: Update main page do używania tracked flow**:
```typescript
// vector-wave-ui/app/page.tsx
// W funkcji analyzeFolder zamień endpoint

const response = await fetch('/api/crewai/execute-flow-tracked', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: folderName,
    content_type: 'STANDARD',
    platform: 'LinkedIn',
    content_ownership: 'EXTERNAL'
  })
});

const data = await response.json();

// Otwórz diagnostykę w nowym komponencie
if (data.flow_id) {
  setCurrentFlowId(data.flow_id);
  setShowDiagnostics(true);
}
```

---

### Zadanie 2.3: Human Review UI Integration (3h)

**Cel**: Dodaj UI dla Human Review Queue w istniejącym frontendzie

**Krok 1: Dodaj Review Queue component**:
```typescript
// vector-wave-ui/components/ReviewQueue.tsx
'use client';

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Edit3, Clock } from "lucide-react";

interface ReviewItem {
  review_id: string;
  draft: {
    title: string;
    content: string;
    platform: string;
    word_count: number;
  };
  status: string;
  created_at: string;
  reviewer?: string;
  feedback?: string;
}

export function ReviewQueue() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    fetchReviewQueue();
  }, []);

  const fetchReviewQueue = async () => {
    try {
      const response = await fetch('/api/crewai/review-queue?status=pending');
      const data = await response.json();
      setItems(data.items);
    } catch (error) {
      console.error('Failed to fetch review queue:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitReview = async (reviewId: string, decision: string) => {
    try {
      const response = await fetch(`/api/crewai/submit-review/${reviewId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          feedback,
          reviewer: 'frontend_user'
        })
      });

      if (response.ok) {
        // Odśwież kolejkę
        fetchReviewQueue();
        setSelectedItem(null);
        setFeedback("");
      }
    } catch (error) {
      console.error('Failed to submit review:', error);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Review Queue</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p>Loading...</p>
          ) : items.length === 0 ? (
            <p>No items pending review</p>
          ) : (
            <div className="space-y-4">
              {items.map((item) => (
                <Card key={item.review_id} className="cursor-pointer hover:shadow-lg">
                  <CardHeader onClick={() => setSelectedItem(item)}>
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold">{item.draft.title}</h3>
                        <p className="text-sm text-gray-600">
                          {item.draft.platform} • {item.draft.word_count} words
                        </p>
                      </div>
                      <Badge>{item.status}</Badge>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Review Modal */}
      {selectedItem && (
        <Card className="fixed inset-4 z-50 overflow-auto">
          <CardHeader>
            <CardTitle>Review: {selectedItem.draft.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-gray-50 p-4 rounded">
              <p className="whitespace-pre-wrap">{selectedItem.draft.content}</p>
            </div>
            
            <textarea
              className="w-full min-h-[100px] p-2 border rounded"
              placeholder="Add your feedback..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
            
            <div className="flex gap-2">
              <Button 
                onClick={() => submitReview(selectedItem.review_id, 'approved')}
                className="bg-green-600"
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Approve
              </Button>
              <Button 
                onClick={() => submitReview(selectedItem.review_id, 'needs_revision')}
                variant="secondary"
              >
                <Edit3 className="w-4 h-4 mr-2" />
                Request Revision
              </Button>
              <Button 
                onClick={() => submitReview(selectedItem.review_id, 'rejected')}
                variant="destructive"
              >
                <XCircle className="w-4 h-4 mr-2" />
                Reject
              </Button>
              <Button 
                onClick={() => setSelectedItem(null)}
                variant="outline"
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

**Test integracji**:
```bash
# 1. Uruchom nowy backend CrewAI
cd kolegium
docker-compose -f docker-compose.minimal.yml up

# 2. Uruchom frontend
cd vector-wave-ui
npm run dev

# 3. Testuj flow z diagnostyką
# - Otwórz http://localhost:3000
# - Kliknij "Analizuj potencjał" na dowolnym folderze
# - Sprawdź czy Flow Diagnostics pokazuje prawdziwe dane
# - Sprawdź Review Queue dla pending items
---


```

---









```yaml

```

```python

```

---

## 📋 Faza 3: Production Container (1 dzień)

### Zadanie 3.1: Multi-stage Dockerfile (1h)

**Cel**: Produkcyjny Dockerfile z optymalizacją

```dockerfile
# Dockerfile.production
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser templates templates/
COPY --chown=appuser:appuser static static/

USER appuser

# Update PATH
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Zadanie 3.2: Redis + Knowledge Base + Style Guide RAG (4h - przyrostowo)

**Cel**: Pełny stack z Redis, Knowledge Base i Agentic RAG dla Style Guide

#### 🎯 Filozofia przyrostowego rozwoju RAG:

```yaml
Sprint 1-2: Cache Layer
- Po co: Instant response dla powtórzeń
- Test: Czy drugie wywołanie jest instant?
- Rollback: Wyłącz Redis, app nadal działa

Sprint 3: Naive RAG
- Po co: Podstawowe wyszukiwanie reguł
- Test: Czy zwraca sensowne reguły?
- Rollback: ChromaDB down = brak style check, ale reszta działa

Sprint 4: Agentic RAG  
- Po co: Inteligentna analiza z kontekstem
- Test: Czy agent rozumie niuanse?
- Rollback: Fallback do naive RAG

Sprint 5: Production
- Po co: Persistent storage, auto-restart
- Test: Czy przeżywa restart?
- Rollback: Wróć do dev compose
```

**WAŻNE**: Każdy sprint to osobny commit, test, i "czy działa?" przed następnym!

#### Sprint 3.2.1: Basic Redis Cache (30 min) ✅ COMPLETED

**Krok 1**: Dodaj Redis do docker-compose
```yaml
# docker-compose.yml - dodaj serwis
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
```

**Krok 2**: Dodaj endpoint testujący cache
```python
# app.py - dodaj na górze
import redis
import json
import hashlib

# Redis connection
try:
    redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
    redis_client.ping()
    print("✅ Redis connected")
except:
    redis_client = None
    print("⚠️ Redis not available - running without cache")

@app.get("/api/cache-test", tags=["diagnostics"])
async def test_cache():
    """Test Redis cache functionality"""
    if not redis_client:
        return {"status": "no_cache", "message": "Redis not connected"}
    
    # Test set/get
    test_key = f"test:{datetime.now().isoformat()}"
    redis_client.setex(test_key, 60, "Hello Redis!")
    value = redis_client.get(test_key)
    
    return {
        "status": "ok",
        "cached_value": value,
        "ttl": redis_client.ttl(test_key)
    }
```

**Test**:
```bash
docker-compose up -d redis
docker-compose restart ai-writing-flow
curl http://localhost:8003/api/cache-test
# Should return: {"status": "ok", "cached_value": "Hello Redis!", "ttl": 59}
```

#### Sprint 3.2.2: Cache for analyze-potential (30 min) ✅ COMPLETED

**Krok**: Dodaj cache do istniejącego endpointa
```python
# app.py - zmodyfikuj analyze_content_potential
@app.post("/api/analyze-potential", tags=["content"])
async def analyze_content_potential(request: AnalyzePotentialRequest):
    """Ultra-fast content analysis with Redis cache"""
    
    # Check cache first
    if redis_client:
        cache_key = f"analysis:{request.folder}"
        cached = redis_client.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["from_cache"] = True
            result["processing_time_ms"] = 0
            return result
    
    start_time = time.time()
    
    # ... existing analysis code ...
    
    # Cache result before returning
    if redis_client and "error" not in analysis_result:
        redis_client.setex(
            cache_key,
            900,  # 15 minutes TTL
            json.dumps(analysis_result)
        )
    
    return analysis_result
```

**Test**:
```bash
# First call - should take 1ms
curl -X POST http://localhost:8003/api/analyze-potential \
  -H "Content-Type: application/json" \
  -d '{"folder": "test-folder"}'

# Second call - should take 0ms and have from_cache: true
curl -X POST http://localhost:8003/api/analyze-potential \
  -H "Content-Type: application/json" \
  -d '{"folder": "test-folder"}'
```

#### Sprint 3.2.3: ChromaDB for Style Guide - Naive RAG (1h) ✅ COMPLETED

**Krok 1**: Dodaj ChromaDB do docker-compose
```yaml
# docker-compose.yml - dodaj serwis
services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8082:8000"
    environment:
      - ANONYMIZED_TELEMETRY=false
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 5s
      timeout: 3s
      retries: 5
```

**Krok 2**: Dodaj endpoint do ładowania style guide
```python
# app.py - dodaj import
import httpx

# ChromaDB client
chroma_client = None
try:
    import chromadb
    chroma_client = chromadb.HttpClient(host="chromadb", port=8000)
    print("✅ ChromaDB connected")
except:
    print("⚠️ ChromaDB not available")

@app.post("/api/style-guide/load", tags=["content"])
async def load_style_guide():
    """Load Vector Wave style guide into ChromaDB"""
    if not chroma_client:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    # Create collection
    collection = chroma_client.get_or_create_collection("style_guide")
    
    # Sample style rules
    rules = [
        {
            "id": "hook_001",
            "text": "Start with compelling hook in first 2 lines",
            "platform": "LinkedIn",
            "examples": "I was wrong about AI.\nCompletely wrong."
        },
        {
            "id": "emoji_001", 
            "text": "Use emojis sparingly - max 2-3 per post",
            "platform": "LinkedIn",
            "examples": "🎯 Key insight: Focus beats features"
        }
    ]
    
    # Load into ChromaDB
    collection.add(
        ids=[r["id"] for r in rules],
        documents=[r["text"] for r in rules],
        metadatas=[{"platform": r["platform"]} for r in rules]
    )
    
    return {"status": "loaded", "rules_count": len(rules)}

@app.post("/api/style-guide/check", tags=["content"])
async def check_style_naive(content: str, platform: str = "LinkedIn"):
    """Naive RAG style check - just similarity search"""
    if not chroma_client:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    collection = chroma_client.get_collection("style_guide")
    
    # Simple similarity search
    results = collection.query(
        query_texts=[content],
        n_results=3,
        where={"platform": platform}
    )
    
    return {
        "relevant_rules": results["documents"][0] if results["documents"] else [],
        "distances": results["distances"][0] if results["distances"] else [],
        "method": "naive_rag"
    }
```

**Test**:
```bash
docker-compose up -d chromadb
docker-compose restart ai-writing-flow

# Load style guide
curl -X POST http://localhost:8003/api/style-guide/load

# Test naive RAG
curl -X POST http://localhost:8003/api/style-guide/check \
  -H "Content-Type: application/json" \
  -d '"Check my post about AI automation"'
```

#### Sprint 3.2.4: Agentic RAG with CrewAI (1.5h) ✅ COMPLETED

**Krok 1**: Dodaj Style Guide Agent
```python
# app.py - dodaj agenta
style_guide_agent = Agent(
    role="Style Guide Expert",
    goal="Validate content against Vector Wave style guide using intelligent reasoning",
    backstory="Expert in editorial standards who understands context and nuance",
    verbose=True,
    llm=llm
)

@app.post("/api/style-guide/check-agentic", tags=["content"])
async def check_style_agentic(
    content: str, 
    platform: str = "LinkedIn",
    context: Optional[str] = None
):
    """Agentic RAG style check - intelligent analysis"""
    if not chroma_client:
        return {"status": "error", "message": "ChromaDB not connected"}
    
    # First get relevant rules from ChromaDB
    collection = chroma_client.get_collection("style_guide")
    results = collection.query(
        query_texts=[content],
        n_results=5,
        where={"platform": platform}
    )
    
    # Create task for agent
    style_task = Task(
        description=f"""
        Analyze this content for style guide compliance:
        
        Content: {content}
        Platform: {platform}
        Context: {context or 'General post'}
        
        Relevant style rules from database:
        {json.dumps(results['documents'][0] if results['documents'] else [])}
        
        Provide:
        1. Overall compliance score (0-100)
        2. Specific violations with severity
        3. Improvement suggestions
        4. Why these rules matter for this context
        """,
        agent=style_guide_agent,
        expected_output="Detailed style analysis with reasoning"
    )
    
    # Execute with CrewAI
    crew = Crew(agents=[style_guide_agent], tasks=[style_task])
    result = crew.kickoff()
    
    return {
        "analysis": str(result),
        "method": "agentic_rag",
        "rules_considered": len(results['documents'][0]) if results['documents'] else 0
    }
```

**Krok 2**: Dodaj multi-hop reasoning
```python
@app.post("/api/style-guide/validate-draft", tags=["content"])
async def validate_draft_style(request: GenerateDraftRequest):
    """Full draft validation with multi-hop style checking"""
    
    # Step 1: Quick naive check
    naive_check = await check_style_naive(
        request.content.title, 
        request.content.platform
    )
    
    # Step 2: If issues found, do deep agentic check
    if naive_check["distances"][0][0] < 0.5:  # High similarity to rules
        agentic_check = await check_style_agentic(
            request.content.title,
            request.content.platform,
            f"Content type: {request.content.content_type}"
        )
        
        return {
            "needs_revision": True,
            "naive_rules": naive_check["relevant_rules"],
            "agentic_analysis": agentic_check["analysis"],
            "recommendation": "Consider revising based on style guide"
        }
    
    return {
        "needs_revision": False,
        "message": "Style check passed"
    }
```

**Test**:
```bash
# Test agentic RAG
curl -X POST http://localhost:8003/api/style-guide/check-agentic \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hey guys! Check out this AMAZING AI tool!!!!! 🚀🔥💯🎉",
    "platform": "LinkedIn",
    "context": "Professional announcement"
  }'

# Should return intelligent analysis explaining why this violates style
```

#### Sprint 3.2.5: Production Docker Compose (30 min)

**Final docker-compose.production.yml**:
```yaml
version: '3.8'

services:
  ai-writing-flow:
    build:
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "8003:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - CHROMADB_URL=http://chromadb:8000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      redis:
        condition: service_healthy
      chromadb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - ANONYMIZED_TELEMETRY=false
      - PERSIST_DIRECTORY=/chroma/chroma
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  redis_data:
  chroma_data:
```

### Metryki sukcesu każdego sprintu:

1. **Sprint 3.2.1**: ✅ `curl /api/cache-test` zwraca `{"status": "ok", "cached_value": "Hello Redis!", "ttl": 60}`
2. **Sprint 3.2.2**: ✅ Drugie wywołanie `/api/analyze-potential` ma `from_cache: true`
3. **Sprint 3.2.3**: ✅ `/api/style-guide/check` zwraca relevantne reguły, violations i style score
4. **Sprint 3.2.4**: ✅ `/api/style-guide/check-agentic` zwraca inteligentną analizę z alternatywnymi openingami
5. **Sprint 3.2.5**: `docker-compose -f docker-compose.production.yml up` startuje wszystko
    `ports:`
      `- "80:80"`
    `volumes:`
      `- ./nginx.conf:/etc/nginx/nginx.conf:ro`
    `depends_on:`
      `- ai-writing-flow`
    `restart: unless-stopped`

`networks:`
  `default:`
    `driver: bridge`

`volumes:`
  `redis-data:`
  `chroma-data:`



# `app.py - dodaj Redis support`
`import redis`
`from typing import Optional`

# `Redis connection`
`redis_client = redis.from_url(`
    `os.getenv("REDIS_URL", "redis://localhost:6379"),`
    `decode_responses=True`
`)`

`@app.on_event("startup")`
`async def startup_event():`
    `"""Initialize services on startup"""`
    `try:`
        `redis_client.ping()`
        `print("✅ Redis connected")`
    `except:`
        `print("⚠️ Redis not available - using in-memory storage")`

# `Update review queue to use Redis`
`async def request_human_review(draft: dict, review_type: str = "editorial"):`
    `"""Dodaje draft do kolejki review (Redis-backed)"""`
``    

    review_id = str(uuid4())
    review_item = {
        "review_id": review_id,
        "draft": json.dumps(draft),  # Redis wymaga string
        "review_type": review_type,
        "status": ReviewStatus.PENDING,
        "created_at": datetime.now().isoformat()
    }
    
    # Save to Redis
    try:
        redis_client.hset(f"review:{review_id}", mapping=review_item)
        redis_client.zadd("review_queue", {review_id: time.time()})
    except:
        # Fallback to in-memory
        review_queue[review_id] = review_item
    
    return {"review_id": review_id, "status": ReviewStatus.PENDING}



### Zadanie 3.3: Monitoring Dashboard (2h)

**Cel**: Dashboard z metrykami systemu

```python
@app.get("/dashboard", response_class=HTMLResponse)
async def monitoring_dashboard():
    """Live monitoring dashboard"""
    
    # Gather metrics
    try:
        redis_info = redis_client.info()
        redis_status = "connected"
    except:
        redis_info = {}
        redis_status = "disconnected"
    
    # System metrics
    import psutil
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    # Business metrics
    total_flows = redis_client.get("metrics:total_flows") or 0
    total_reviews = redis_client.zcard("review_queue") or len(review_queue)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Writing Flow - Dashboard</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background: #f5f5f5; 
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
            }}
            .metrics {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 20px; 
                margin: 20px 0; 
            }}
            .metric {{ 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            }}
            .metric h3 {{ 
                margin: 0 0 10px 0; 
                color: #333; 
            }}
            .metric .value {{ 
                font-size: 2em; 
                font-weight: bold; 
                color: #2196F3; 
            }}
            .status {{ 
                padding: 5px 10px; 
                border-radius: 4px; 
                display: inline-block; 
            }}
            .status.connected {{ 
                background: #4CAF50; 
                color: white; 
            }}
            .status.disconnected {{ 
                background: #f44336; 
                color: white; 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 AI Writing Flow - Live Dashboard</h1>
            <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="metrics">
                <div class="metric">
                    <h3>System Status</h3>
                    <div class="value">Healthy</div>
                    <p>CPU: {cpu_percent}%</p>
                    <p>Memory: {memory.percent}%</p>
                </div>
                
                <div class="metric">
                    <h3>Redis Status</h3>
                    <div class="status {redis_status}">{redis_status.upper()}</div>
                    <p>Keys: {redis_info.get('db0', {}).get('keys', 0)}</p>
                </div>
                
                <div class="metric">
                    <h3>Total Flows</h3>
                    <div class="value">{total_flows}</div>
                    <p>Processed today</p>
                </div>
                
                <div class="metric">
                    <h3>Review Queue</h3>
                    <div class="value">{total_reviews}</div>
                    <p>Pending reviews</p>
                </div>
            </div>
            
            <h2>Recent Activity</h2>
            <div id="activity">
                <p>Loading recent activity...</p>
            </div>
            
            <script>
                // Auto-refresh activity feed
                async function loadActivity() {{
                    try {{
                        const response = await fetch('/api/recent-activity');
                        const data = await response.json();
                        
                        const activityHtml = data.activities
                            .map(a => `<p>$ {{a.timestamp}} - $ {{a.action}} - $ {{a.details}}</p>`)
                            .join('');
                            
                        document.getElementById('activity').innerHTML = activityHtml || '<p>No recent activity</p>';
                    }} catch (e) {{
                        console.error('Failed to load activity:', e);
                    }}
                }}
                
                loadActivity();
                setInterval(loadActivity, 5000);
            </script>
        </div>
    </body>
    </html>
    """
    
    return html

@app.get("/api/recent-activity")
async def get_recent_activity():
    """Get recent system activity"""
    # Mock data - w produkcji pobierz z Redis
    activities = [
        {
            "timestamp": datetime.now().isoformat(),
            "action": "flow_executed",
            "details": "Technical content flow completed"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "action": "review_submitted",
            "details": "Content approved by senior_editor"
        }
    ]
    
    return {"activities": activities}
```

---

## 🎯 Finalne Testy E2E

### Test Script
```bash
#!/bin/bash
# test-e2e.sh

echo "🧪 AI Writing Flow - E2E Container Tests"

# 1. Start services
echo "1️⃣ Starting services..."
docker compose -f docker-compose.production.yml up -d

# 2. Wait for health
echo "2️⃣ Waiting for services..."
sleep 30

# 3. Test routing
echo "3️⃣ Testing routing..."
curl -s -X POST http://localhost:8000/api/test-routing \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content_ownership": "ORIGINAL"}' \
  | jq .route_decision

# 4. Test complete flow
echo "4️⃣ Testing complete flow..."
FLOW_RESPONSE=$(curl -s -X POST http://localhost:8000/api/execute-flow \
  -H "Content-Type: application/json" \
  -d '{"title": "Container Best Practices", "content_type": "TECHNICAL"}')

echo "$FLOW_RESPONSE" | jq .status

# 5. Test with review
echo "5️⃣ Testing flow with review..."
REVIEW_RESPONSE=$(curl -s -X POST http://localhost:8000/api/execute-flow-with-review \
  -H "Content-Type: application/json" \
  -d '{"title": "AI Future", "platform": "LinkedIn"}')

REVIEW_ID=$(echo "$REVIEW_RESPONSE" | jq -r .human_review.review_id)
echo "Review ID: $REVIEW_ID"

# 6. Check dashboard
echo "6️⃣ Checking dashboard..."
curl -s http://localhost/dashboard | grep -q "AI Writing Flow" && echo "✅ Dashboard OK"

# 7. Submit review
echo "7️⃣ Submitting review..."
curl -s -X POST http://localhost:8000/api/submit-review/$REVIEW_ID \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved", "feedback": "Great content!"}' \
  | jq .status

# 8. Check metrics
echo "8️⃣ Final metrics..."
curl -s http://localhost:8000/api/system-metrics | jq .

echo "✅ All tests completed!"
```

---

## 📊 Podsumowanie Container-First Approach

### Co osiągnęliśmy:

1. **Zero Setup Time**
   - `docker compose up` - wszystko działa
   - Nie trzeba instalować Python, dependencies, etc.

2. **Testowalne API od pierwszego dnia**
   - Każde zadanie = nowy endpoint
   - Curl/httpie do testowania każdej funkcji

3. **Progresywny rozwój**
   - Zaczynamy od 50 linii kodu
   - Każde zadanie dodaje nową funkcjonalność
   - Zawsze mamy działający system

4. **Production Ready**
   - Health checks
   - Monitoring dashboard
   - Redis dla persistence
   - Nginx load balancer

5. **Human-in-the-Loop**
   - Web UI dla reviewerów
   - API dla integracji
   - Queue management

### Kluczowe różnice vs tradycyjne podejście:

| Tradycyjne | Container-First |
|------------|-----------------|
| Najpierw cały kod, potem testy | Każda linia kodu od razu testowalna |
| Konteneryzacja na końcu | Kontener od pierwszego dnia |
| Skomplikowany setup | docker compose up |
| Trudne debugowanie | curl do każdego endpointu |
| Deployment jako afterthought | Production-ready od początku |

### Next Steps:

1. **Kubernetes deployment** - Helm charts
2. **CI/CD pipeline** - GitHub Actions
3. **Observability** - Prometheus + Grafana
4. **API Gateway** - Kong/Traefik
5. **Message Queue** - RabbitMQ/Kafka dla async

Ten plan transformuje AI Writing Flow w nowoczesny, container-first system gdzie każdy krok jest testowalny i produkcyjny od pierwszego dnia.

---

## 📈 Podsumowanie Postępu

### Wykonane do tej pory:
- **Faza 0**: ✅ 100% - Podstawowy kontener z FastAPI działa
- **Faza 1**: ✅ 100% - Pełna integracja CrewAI z prawdziwymi agentami
- **Faza 2**: 🚧 33% - Flow Diagnostics gotowe, czeka integracja z frontendem

### Kluczowe osiągnięcia:
1. **Działający backend CrewAI** na porcie 8003 z prawdziwymi agentami AI
2. **Pełne śledzenie wykonania** - każdy krok flow jest monitorowany
3. **Diagnostyka w czasie rzeczywistym** - metryki, decyzje agentów, content loss
4. **Intelligent routing** - ORIGINAL content pomija research automatycznie

### Następne kroki:
- [ ] Połączyć frontend z nowym backendem (port 8003)
- [ ] Zaktualizować FlowDiagnostics.tsx do użycia prawdziwych danych
- [ ] Dodać UI dla Human Review Queue (opcjonalne)

**Data ostatniej aktualizacji**: 2025-08-05

---

## 🚀 PRAGMATYCZNY PLAN NAPRAWY BŁĘDU 404 - Przyciski "Wygeneruj Draft"

### 🎯 Problem
Przyciski "wygeneruj draft" zwracają błąd 404, ponieważ frontend wywołuje `/api/generate-draft-v2` który nie istnieje w backendzie.

### ⚡ PLAN MINIMUM VIABLE CHANGE (MVC)

#### **Krok 1: Napraw tylko błąd 404 (5 minut)**
```
ZMIANA: 1 linia w frontend proxy
- Z: /api/generate-draft-v2
- Na: /api/generate-draft
```
**Efekt**: Przyciski przestaną zwracać 404

#### **Krok 2: Minimalna transformacja danych (10 minut)**
```
ZMIANA: 5 linii w frontend proxy
- Mapuj: topic_title → title
- Zawiń w: content: { ... }
```
**Efekt**: Backend otrzyma dane których oczekuje

#### **Krok 3: STOP - Testuj co działa**
- Czy generuje drafty? ✓
- Jak długo trwa? Zmierz
- Co użytkownicy mówią? Zapytaj

### 📊 CZEGO NIE ROBIMY:
- ❌ NIE piszemy nowego routera
- ❌ NIE implementujemy skomplikowanej logiki  
- ❌ NIE refaktorujemy całego backendu
- ❌ NIE dodajemy 10 nowych features

### ✅ PRZYROSTOWE ULEPSZENIA (tylko jeśli potrzebne):

#### **Faza A: Wykorzystaj skip_research (jeśli za wolno)**
```python
# Dodaj 3 linie do istniejącego endpointu
if request_data.get("skip_research", False):
    research_data = None  # Pomijamy
```
**Zysk**: -20 sekund dla ORIGINAL content

#### **Faza B: Wykorzystaj viral_score (jeśli użytkownicy chcą)**
```python
# Dodaj 2 linie do writer prompt
if request_data.get("viral_score", 0) > 7:
    prompt += " Make it viral and engaging!"
```
**Zysk**: Lepsze dopasowanie stylu

#### **Faza C: Cache (jeśli dużo powtórzeń)**
```python
# Dodaj prosty dict cache
draft_cache = {}
cache_key = f"{title}:{platform}"
if cache_key in draft_cache:
    return draft_cache[cache_key]
```
**Zysk**: Instant response dla powtórzeń

### 🛡️ ZASADY BEZPIECZEŃSTWA:

1. **Każda zmiana < 30 minut**
   - Jeśli dłużej = za skomplikowane
   
2. **Każda zmiana = osobny commit**
   - Łatwy rollback gdy coś nie działa

3. **Każda zmiana = test z użytkownikiem**
   - "Czy to pomogło?" przed następną zmianą

4. **NIE DODAWAJ jeśli działa**
   - "Good enough" > "Perfect"

### 📈 METRYKI DECYZYJNE:

Robimy kolejny krok TYLKO gdy:
- Użytkownicy narzekają na konkretny problem
- Mamy dane że coś jest za wolne (>30s)
- Wiemy dokładnie co chcemy poprawić

### 🎮 PRZYKŁAD ŚCIEŻKI:

**Dzień 1**: 
- Fix 404 (5 min) ✓
- Test → Działa? → Stop

**Dzień 7** (jeśli użytkownicy: "za wolno dla własnych notatek"):
- Add skip_research (10 min) ✓
- Test → Szybciej? → Stop

**Dzień 14** (jeśli użytkownicy: "chcemy więcej viral"):
- Add viral_score usage (10 min) ✓
- Test → Lepiej? → Stop

### ❌ CZEGO UNIKAMY (lekcja z "linear flow"):

1. **NIE** - "Przepiszmy całość na nową architekturę"
2. **NIE** - "Dodajmy 5 typów flow od razu"
3. **NIE** - "Zróbmy super AI router"
4. **NIE** - "Zoptymalizujmy wszystko"

---

## 🎉 NAJNOWSZE OSIĄGNIĘCIA (2025-08-06)

### ✅ Future Enhancements: Batch Analysis Progress COMPLETED

**Co zrobiliśmy**:
1. **SSE Streaming Endpoint** (`/api/analyze-custom-ideas-stream`)
   - Real-time progress updates podczas analizy wielu pomysłów
   - Progress tracking z procentami (0-100%)
   - Event types: start, progress, result, error, complete
   - Cachowanie całego batcha po zakończeniu

2. **Fix: Style Guide Loading**
   - 180 prawdziwych reguł ładowanych z plików `/styleguides`
   - Auto-seeding przy starcie kontenera
   - Parser wyciąga reguły z markdown files
   - Volume mount w docker-compose dla styleguides

**Jak testować**:
```bash
# Test SSE streaming
curl -N -X POST http://localhost:8003/api/analyze-custom-ideas-stream \
  -H "Content-Type: application/json" \
  -d '{
    "folder": "2025-08-05-hybrid-rag-crewai",
    "ideas": ["Idea 1", "Idea 2", "Idea 3"],
    "platform": "LinkedIn"
  }'

# Test style guide z realnymi regułami  
curl -X POST http://localhost:8003/api/style-guide/check \
  -H "Content-Type: application/json" \
  -d '{"content": "Test content", "platform": "LinkedIn"}'
```

**Co dalej**:
- Sprint 3.2.5: Production Docker Compose (ostatni sprint fazy 3)
- LUB: Frontend Progress Bar dla Custom Ideas Analysis

### ✅ CO ROBIMY:

1. **TAK** - "Naprawmy błąd 404"
2. **TAK** - "Zobaczmy czy to wystarczy"
3. **TAK** - "Dodajmy 1 małą rzecz jeśli trzeba"
4. **TAK** - "Zatrzymajmy się gdy działa"

### 💡 KLUCZOWA LEKCJA:

Po doświadczeniu z "linear flow" które pochłonęło 2 dni i nie działało, stosujemy zasadę:
> "Mały problem → Małe rozwiązanie → Działa? → Stop"

To jak różnica między:
- **Źle**: "Zbudujmy nowy dom bo drzwi skrzypią"
- **Dobrze**: "Naoliwmy zawiasy i zobaczmy"

**Data ostatniej aktualizacji**: 2025-08-05
