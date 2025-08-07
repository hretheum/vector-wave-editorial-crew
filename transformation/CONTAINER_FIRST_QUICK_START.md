# 🚀 Container-First Quick Start Guide

## 🎯 TL;DR - Start w 5 minut

```bash
# 1. Stwórz minimalny kontener
docker build -f Dockerfile.minimal -t ai-flow:v1 .

# 2. Uruchom
docker run -p 8000:8000 ai-flow:v1

# 3. Testuj routing (GŁÓWNY PROBLEM Z DIAGRAMU!)
curl -X POST http://localhost:8000/api/test-routing \
  -H "Content-Type: application/json" \
  -d '{"title": "My Story", "content_ownership": "ORIGINAL"}'

# Powinno zwrócić:
# "route_decision": "skip_research_flow"
# "skip_research": true
```

## 📁 Struktura Startowa (3 pliki)

### 1. `app.py` - Minimalny FastAPI z routingiem
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI Writing Flow - Container First")

class ContentRequest(BaseModel):
    title: str
    content_type: str = "STANDARD"  # STANDARD, TECHNICAL, VIRAL
    platform: str = "LinkedIn"
    content_ownership: str = "EXTERNAL"  # EXTERNAL, ORIGINAL

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/test-routing")
def test_routing(content: ContentRequest):
    """GŁÓWNY ENDPOINT - testuje routing ORIGINAL vs EXTERNAL"""
    
    # Kluczowa logika z diagramu!
    if content.content_ownership == "ORIGINAL":
        route = "skip_research_flow"  # Pomijamy research!
    elif content.content_type == "TECHNICAL":
        route = "technical_deep_dive_flow"
    elif content.content_type == "VIRAL":
        route = "viral_engagement_flow"
    else:
        route = "standard_editorial_flow"
    
    return {
        "route_decision": route,
        "skip_research": content.content_ownership == "ORIGINAL",
        "reason": f"Content ownership is {content.content_ownership}"
    }
```

### 2. `Dockerfile.minimal`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. `docker-compose.yml`
```yaml
version: '3.8'
services:
  ai-flow:
    build:
      context: .
      dockerfile: Dockerfile.minimal
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
```

## 🧪 Testy Kluczowego Routingu

### Test 1: ORIGINAL content (powinien pominąć research)
```bash
curl -X POST http://localhost:8000/api/test-routing \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Moja historia z ADHD",
    "content_ownership": "ORIGINAL",
    "platform": "Twitter"
  }'

# Oczekiwany wynik:
{
  "route_decision": "skip_research_flow",
  "skip_research": true,
  "reason": "Content ownership is ORIGINAL"
}
```

### Test 2: EXTERNAL content (powinien robić research)
```bash
curl -X POST http://localhost:8000/api/test-routing \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Kubernetes Best Practices",
    "content_ownership": "EXTERNAL",
    "content_type": "TECHNICAL"
  }'

# Oczekiwany wynik:
{
  "route_decision": "technical_deep_dive_flow",
  "skip_research": false,
  "reason": "Content ownership is EXTERNAL"
}
```

## 📈 Progresja - Co Dalej?

### Krok 2: Dodaj Research Agent (Zadanie 1.1)
```python
# Dodaj do app.py
@app.post("/api/research")
async def execute_research(topic: str, skip: bool = False):
    if skip:
        return {"status": "skipped", "reason": "ORIGINAL content"}
    
    # Tu będzie CrewAI ResearchAgent
    return {
        "status": "completed",
        "findings": f"Research about {topic}",
        "duration_ms": 1500
    }
```

### Krok 3: Dodaj Writer Agent (Zadanie 1.2)
```python
@app.post("/api/generate-draft")
async def generate_draft(request: ContentRequest, research: dict = None):
    context = research["findings"] if research else "No research (ORIGINAL)"
    
    return {
        "draft": f"Article about {request.title}. Context: {context}",
        "platform_optimized": request.platform
    }
```

### Krok 4: Complete Flow (Zadanie 1.3)
```python
@app.post("/api/execute-flow")
async def complete_flow(request: ContentRequest):
    # 1. Routing
    routing = test_routing(request)
    
    # 2. Research (jeśli potrzebny)
    research = None
    if not routing["skip_research"]:
        research = await execute_research(request.title)
    
    # 3. Generate
    draft = await generate_draft(request, research)
    
    return {
        "routing": routing,
        "research_executed": not routing["skip_research"],
        "draft": draft
    }
```

## 🏃 Makefile dla Wygody

```makefile
# Makefile
.PHONY: build run test clean

build:
	docker build -f Dockerfile.minimal -t ai-flow:latest .

run: build
	docker compose up -d
	@echo "Waiting for container..."
	@sleep 3
	@curl -s http://localhost:8000/health | jq .

test-routing:
	@echo "Testing ORIGINAL (should skip research):"
	@curl -s -X POST http://localhost:8000/api/test-routing \
		-H "Content-Type: application/json" \
		-d '{"title": "Test", "content_ownership": "ORIGINAL"}' | jq .
	
	@echo "\nTesting EXTERNAL (should do research):"
	@curl -s -X POST http://localhost:8000/api/test-routing \
		-H "Content-Type: application/json" \
		-d '{"title": "Test", "content_ownership": "EXTERNAL"}' | jq .

logs:
	docker compose logs -f

clean:
	docker compose down
	docker rmi ai-flow:latest

all: clean build run test-routing
```

## ⚡ One-Liner Start

```bash
# Stwórz 3 pliki i uruchom:
make all

# Lub ręcznie:
docker compose up -d && sleep 3 && \
curl -X POST http://localhost:8000/api/test-routing \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content_ownership": "ORIGINAL"}' | jq .
```

## 🎯 Dlaczego Container-First?

1. **Natychmiastowy feedback** - każda zmiana = curl test
2. **Zero setup** - nie musisz instalować Python, CrewAI, etc.
3. **Izolacja** - nie zepsujesz lokalnego środowiska
4. **Produkcyjność** - od początku myślisz o deployment
5. **Testowalność** - API endpoint dla każdej funkcji

## 🚨 Częste Błędy

### "Port already in use"
```bash
# Znajdź i zabij proces
lsof -i :8000
kill -9 <PID>

# Lub zmień port w docker-compose.yml
ports:
  - "8001:8000"
```

### "Module not found"
```bash
# Zawsze rebuilduj po zmianach w requirements
docker compose build --no-cache
```

### "Container exits immediately"
```bash
# Sprawdź logi
docker compose logs ai-flow

# Często to błąd składni w app.py
```

## 📊 Monitorowanie

```bash
# Live logs
docker compose logs -f

# Container stats
docker stats

# Health check
watch -n 1 'curl -s http://localhost:8000/health | jq .'
```

## 🎓 Next Steps

1. **Przeczytaj** `CONTAINER_FIRST_TRANSFORMATION_PLAN.md`
2. **Implementuj** Zadanie 0.1-0.3 (Minimal Container)
3. **Testuj** każdy endpoint curlem
4. **Commituj** po każdym działającym endpoincie
5. **Powtarzaj** dla kolejnych zadań

---

**Ready? Let's build!** 🚀

Pamiętaj: Każde zadanie = nowy endpoint = możliwość przetestowania = widoczny postęp!