# 🧪 Test-Driven Container Tasks - AI Writing Flow

## 📋 Każde zadanie z gotowymi testami

### Filozofia: Red → Green → Refactor
1. **Red**: Napisz test który failuje
2. **Green**: Implementuj minimum żeby test przeszedł  
3. **Refactor**: Popraw kod zachowując zielone testy

---

## 🎯 Faza 0: Foundation (3h)

### Zadanie 0.1: Health Check Endpoint
**Test PIERWSZY**:
```python
# tests/test_health.py
def test_health_endpoint():
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

**Implementacja POTEM**:
```python
# app.py
@app.get("/health")
def health():
    return {"status": "healthy"}
```

**Uruchom test**:
```bash
docker compose up -d
pytest tests/test_health.py -v
```

---

### Zadanie 0.2: Routing Decision Test
**Test PIERWSZY**:
```python
# tests/test_routing.py
def test_original_content_skips_research():
    """ORIGINAL content should skip research phase"""
    payload = {
        "title": "My Personal Story",
        "content_ownership": "ORIGINAL"
    }
    
    response = requests.post(
        "http://localhost:8000/api/test-routing",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["skip_research"] == True
    assert "skip" in data["route_decision"].lower()

def test_external_content_needs_research():
    """EXTERNAL content should go through research"""
    payload = {
        "title": "Industry Analysis",
        "content_ownership": "EXTERNAL"
    }
    
    response = requests.post(
        "http://localhost:8000/api/test-routing",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["skip_research"] == False
    assert "research" in data["route_decision"].lower()
```

**Implementacja POTEM**:
```python
@app.post("/api/test-routing")
def test_routing(content: ContentRequest):
    if content.content_ownership == "ORIGINAL":
        return {
            "route_decision": "skip_research_flow",
            "skip_research": True
        }
    else:
        return {
            "route_decision": "standard_research_flow",
            "skip_research": False
        }
```

---

### Zadanie 0.3: Platform-Specific Routing
**Test PIERWSZY**:
```python
def test_technical_content_gets_deep_research():
    """TECHNICAL content should use deep research"""
    payload = {
        "title": "Microservices Architecture",
        "content_ownership": "EXTERNAL",
        "content_type": "TECHNICAL"
    }
    
    response = requests.post(
        "http://localhost:8000/api/test-routing",
        json=payload
    )
    
    data = response.json()
    assert "deep" in data["route_decision"] or "technical" in data["route_decision"]
    assert data.get("research_depth") == "deep"

def test_viral_content_gets_trend_analysis():
    """VIRAL content should include trend analysis"""
    payload = {
        "title": "10 Shocking AI Facts",
        "content_ownership": "EXTERNAL",
        "content_type": "VIRAL",
        "platform": "Twitter"
    }
    
    response = requests.post(
        "http://localhost:8000/api/test-routing",
        json=payload
    )
    
    data = response.json()
    assert "viral" in data["route_decision"] or "trend" in data["route_decision"]
    assert data.get("include_trend_analysis") == True
```

---

## 🎯 Faza 1: Agent Integration (4h)

### Zadanie 1.1: Research Agent Skip Test
**Test PIERWSZY**:
```python
# tests/test_research.py
def test_research_skipped_for_original():
    """Research should be skipped for ORIGINAL content"""
    payload = {
        "topic": "My ADHD Journey",
        "skip_research": True
    }
    
    response = requests.post(
        "http://localhost:8000/api/research",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert data["reason"] == "skip_research flag is True"
    assert data["findings"] == []

def test_research_executed_for_external():
    """Research should execute for EXTERNAL content"""
    payload = {
        "topic": "Kubernetes Best Practices",
        "skip_research": False
    }
    
    response = requests.post(
        "http://localhost:8000/api/research",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["findings"]) > 0
    assert data["execution_time_ms"] > 0
```

---

### Zadanie 1.2: Draft Generation Test
**Test PIERWSZY**:
```python
def test_draft_without_research():
    """Draft should be generated without research context"""
    payload = {
        "title": "My Story",
        "platform": "LinkedIn",
        "content_ownership": "ORIGINAL"
    }
    
    response = requests.post(
        "http://localhost:8000/api/generate-draft",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "research" not in data["draft"]["content"].lower()
    assert data["metadata"]["used_research"] == False

def test_draft_with_research_context():
    """Draft should incorporate research findings"""
    # First do research
    research_response = requests.post(
        "http://localhost:8000/api/research",
        json={"topic": "AI Trends", "skip_research": False}
    )
    research_data = research_response.json()
    
    # Then generate draft with research
    payload = {
        "title": "AI Trends Analysis",
        "platform": "Blog",
        "research_context": research_data["findings"]
    }
    
    response = requests.post(
        "http://localhost:8000/api/generate-draft",
        json=payload
    )
    
    data = response.json()
    assert data["metadata"]["used_research"] == True
    assert len(data["draft"]["content"]) > 100
```

---

### Zadanie 1.3: Complete Flow Test
**Test PIERWSZY**:
```python
def test_complete_flow_original_content():
    """Complete flow for ORIGINAL content should skip research"""
    payload = {
        "title": "My ADHD Experience",
        "content_ownership": "ORIGINAL",
        "platform": "Twitter"
    }
    
    response = requests.post(
        "http://localhost:8000/api/execute-flow",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify execution log
    steps = [step["step"] for step in data["execution_log"]]
    assert "routing" in steps
    assert "research" not in steps  # Should be skipped!
    assert "draft_generation" in steps
    
    # Verify skip_research worked
    routing_step = next(s for s in data["execution_log"] if s["step"] == "routing")
    assert routing_step["result"]["skip_research"] == True

def test_complete_flow_external_technical():
    """Complete flow for EXTERNAL TECHNICAL should do deep research"""
    payload = {
        "title": "Distributed Systems Architecture",
        "content_ownership": "EXTERNAL",
        "content_type": "TECHNICAL",
        "platform": "Blog"
    }
    
    response = requests.post(
        "http://localhost:8000/api/execute-flow",
        json=payload
    )
    
    data = response.json()
    
    # Verify all steps executed
    steps = [step["step"] for step in data["execution_log"]]
    assert "routing" in steps
    assert "research" in steps  # Should be included!
    assert "draft_generation" in steps
    
    # Verify research was deep
    research_step = next(s for s in data["execution_log"] if s["step"] == "research")
    assert research_step["result"]["depth"] == "deep"
```

---

## 🎯 Faza 2: Human Review (3h)

### Zadanie 2.1: Review Queue Test
**Test PIERWSZY**:
```python
def test_add_to_review_queue():
    """Content should be added to review queue"""
    draft = {
        "title": "AI Article",
        "content": "Draft content here...",
        "platform": "LinkedIn"
    }
    
    response = requests.post(
        "http://localhost:8000/api/request-review",
        json={"draft": draft, "review_type": "editorial"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "review_id" in data
    assert data["status"] == "pending"
    assert data["review_url"].startswith("/review/")
    
    # Verify it's in queue
    queue_response = requests.get("http://localhost:8000/api/review-queue")
    queue_data = queue_response.json()
    assert queue_data["stats"]["pending"] > 0

def test_submit_review_decision():
    """Review decision should update status"""
    # First add to queue
    review_response = requests.post(
        "http://localhost:8000/api/request-review",
        json={"draft": {"title": "Test"}, "review_type": "quality"}
    )
    review_id = review_response.json()["review_id"]
    
    # Submit decision
    decision_response = requests.post(
        f"http://localhost:8000/api/submit-review/{review_id}",
        json={
            "decision": "approved",
            "feedback": "Looks good!",
            "reviewer": "test_user"
        }
    )
    
    assert decision_response.status_code == 200
    
    # Check status updated
    status_response = requests.get(f"http://localhost:8000/api/review-status/{review_id}")
    assert status_response.json()["status"] == "approved"
```

---

### Zadanie 2.2: Review Timeout Test
**Test PIERWSZY**:
```python
def test_review_timeout():
    """Review should timeout and auto-approve"""
    import time
    
    # Request review with short timeout
    response = requests.post(
        "http://localhost:8000/api/request-review",
        json={
            "draft": {"title": "Timeout Test"},
            "review_type": "editorial",
            "timeout_minutes": 0.1  # 6 seconds
        }
    )
    review_id = response.json()["review_id"]
    
    # Wait for timeout
    time.sleep(7)
    
    # Check status
    status_response = requests.get(f"http://localhost:8000/api/review-status/{review_id}")
    data = status_response.json()
    
    assert data["status"] == "timeout"
    assert data["auto_decision"] == "approved"
```

---

## 🎯 Faza 3: Monitoring (2h)

### Zadanie 3.1: Metrics Collection Test
**Test PIERWSZY**:
```python
def test_metrics_increment():
    """Metrics should track flow executions"""
    # Get initial metrics
    initial = requests.get("http://localhost:8000/api/metrics").json()
    initial_flows = initial.get("flows_executed", 0)
    
    # Execute a flow
    requests.post(
        "http://localhost:8000/api/execute-flow",
        json={"title": "Test", "content_ownership": "ORIGINAL"}
    )
    
    # Check metrics incremented
    updated = requests.get("http://localhost:8000/api/metrics").json()
    assert updated["flows_executed"] == initial_flows + 1

def test_error_tracking():
    """Errors should be tracked in metrics"""
    # Trigger an error with invalid data
    response = requests.post(
        "http://localhost:8000/api/execute-flow",
        json={}  # Missing required fields
    )
    
    assert response.status_code == 422  # Validation error
    
    # Check error count increased
    metrics = requests.get("http://localhost:8000/api/metrics").json()
    assert metrics["error_count"] > 0
```

---

### Zadanie 3.2: Health Dashboard Test
**Test PIERWSZY**:
```python
def test_dashboard_loads():
    """Dashboard should return valid HTML"""
    response = requests.get("http://localhost:8000/dashboard")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AI Writing Flow" in response.text
    assert "System Status" in response.text

def test_dashboard_auto_refresh():
    """Dashboard should have auto-refresh meta tag"""
    response = requests.get("http://localhost:8000/dashboard")
    
    assert 'http-equiv="refresh"' in response.text
    assert 'content="5"' in response.text  # 5 second refresh
```

---

## 🏃 Continuous Test Runner

### `test_runner.py`
```python
#!/usr/bin/env python3
"""Continuous test runner dla container development"""
import time
import subprocess
import sys

def run_tests():
    """Run all tests and return status"""
    result = subprocess.run([
        "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        "-x"  # Stop on first failure
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result.returncode == 0

def main():
    """Watch for changes and run tests"""
    print("🧪 Starting continuous test runner...")
    print("Press Ctrl+C to stop\n")
    
    while True:
        print(f"\n{'='*60}")
        print(f"Running tests at {time.strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")
        
        success = run_tests()
        
        if success:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Tests failed!")
        
        print("\nWaiting 5 seconds before next run...")
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Test runner stopped")
```

### Użycie:
```bash
# Terminal 1: Run container
docker compose up

# Terminal 2: Run tests continuously
python test_runner.py

# Terminal 3: Make changes
# Testy automatycznie się uruchomią co 5 sekund
```

---

## 📊 Test Coverage Report

### `generate_coverage.sh`
```bash
#!/bin/bash
# Generate test coverage report

# Run tests with coverage
docker compose exec ai-flow pytest \
    --cov=/app \
    --cov-report=html \
    --cov-report=term \
    tests/

# Open coverage report
open htmlcov/index.html
```

---

## 🎯 Test-First Best Practices

1. **Zawsze test najpierw**
   - Napisz test
   - Zobacz że failuje
   - Dopiero wtedy pisz kod

2. **Jeden test = jedna funkcja**
   - Nie testuj wszystkiego naraz
   - Mały, focused test
   - Łatwy do debugowania

3. **Test nazwa mówi co testuje**
   - `test_original_content_skips_research`
   - NIE: `test_routing_1`

4. **Arrange-Act-Assert**
   ```python
   def test_example():
       # Arrange
       payload = {"data": "test"}
       
       # Act
       response = requests.post("/api/endpoint", json=payload)
       
       # Assert
       assert response.status_code == 200
   ```

5. **Fixtures dla powtarzalnych danych**
   ```python
   @pytest.fixture
   def original_content():
       return {
           "title": "Test",
           "content_ownership": "ORIGINAL"
       }
   ```

---

**Ready to Test-Drive Development?** 🚀

Pamiętaj: Red → Green → Refactor!