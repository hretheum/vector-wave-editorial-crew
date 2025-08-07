import requests
import pytest
import time

BASE_URL = "http://localhost:8003"

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

def test_routing_viral_content():
    """Test że VIRAL content dostaje specjalne traktowanie"""
    payload = {
        "title": "10 AI Secrets That Will Shock You",
        "content_ownership": "EXTERNAL", 
        "content_type": "VIRAL",
        "platform": "Twitter"
    }
    
    response = requests.post(f"{BASE_URL}/api/test-routing", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["route_decision"] == "viral_engagement_flow"
    assert data["skip_research"] == False
    assert data["input"]["platform"] == "Twitter"

def test_flow_diagnostics_tracked_execution():
    """Test wykonania flow z pełnym śledzeniem"""
    payload = {
        "title": "Test AI Flow Diagnostics",
        "content_ownership": "ORIGINAL",
        "content_type": "STANDARD",
        "platform": "LinkedIn"
    }
    
    # Wykonaj flow z tracking
    response = requests.post(f"{BASE_URL}/api/execute-flow-tracked", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "flow_id" in data
    assert data["status"] == "completed"
    assert "diagnostic_url" in data
    assert data["diagnostic_url"] == f"/api/flow-diagnostics/{data['flow_id']}"
    
    # Sprawdź czy draft został wygenerowany
    assert "final_draft" in data
    assert data["final_draft"] is not None
    
    return data["flow_id"]

def test_get_flow_diagnostics_details():
    """Test pobierania szczegółów diagnostycznych flow"""
    # Najpierw wykonaj flow
    flow_id = test_flow_diagnostics_tracked_execution()
    
    # Pobierz diagnostykę
    response = requests.get(f"{BASE_URL}/api/flow-diagnostics/{flow_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["flow_id"] == flow_id
    assert "steps" in data
    assert len(data["steps"]) >= 2  # Minimum: validation + draft (research może być skipped)
    
    # Sprawdź strukturę kroków
    for step in data["steps"]:
        assert "id" in step
        assert "name" in step
        assert "status" in step
        assert step["status"] in ["completed", "failed", "skipped"]
        
        if step["status"] == "completed":
            assert "agent_decisions" in step
            assert len(step["agent_decisions"]) > 0
    
    # Sprawdź pierwszy krok (validation)
    validation_step = data["steps"][0]
    assert validation_step["id"] == "input_validation"
    assert validation_step["status"] == "completed"
    
def test_flow_diagnostics_with_research():
    """Test flow z research (EXTERNAL content)"""
    payload = {
        "title": "Advanced Kubernetes Patterns",
        "content_ownership": "EXTERNAL",
        "content_type": "TECHNICAL",
        "platform": "Blog"
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-flow-tracked", json=payload)
    assert response.status_code == 200
    
    flow_id = response.json()["flow_id"]
    
    # Pobierz diagnostykę
    diag_response = requests.get(f"{BASE_URL}/api/flow-diagnostics/{flow_id}")
    data = diag_response.json()
    
    # Znajdź research step
    research_step = next((s for s in data["steps"] if s["id"] == "research"), None)
    assert research_step is not None
    assert research_step["status"] == "completed"
    assert "content_loss" in research_step
    
def test_list_flow_executions():
    """Test listowania wykonań flow"""
    # Wykonaj kilka flow
    for i in range(3):
        payload = {
            "title": f"Test Flow {i}",
            "content_ownership": "ORIGINAL" if i % 2 == 0 else "EXTERNAL",
            "content_type": "STANDARD"
        }
        requests.post(f"{BASE_URL}/api/execute-flow-tracked", json=payload)
    
    # Pobierz listę
    response = requests.get(f"{BASE_URL}/api/flow-diagnostics?limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert "total" in data
    assert data["total"] >= 3
    assert "executions" in data
    assert len(data["executions"]) >= 3
    
    # Sprawdź sortowanie (najnowsze pierwsze)
    timestamps = [ex["created_at"] for ex in data["executions"]]
    assert timestamps == sorted(timestamps, reverse=True)

def test_flow_diagnostics_not_found():
    """Test błędu 404 dla nieistniejącego flow"""
    response = requests.get(f"{BASE_URL}/api/flow-diagnostics/non_existent_flow_12345")
    assert response.status_code == 404
    assert response.json()["detail"] == "Flow execution not found"

def test_generate_draft_without_research():
    """Test generowania draftu bez research data"""
    payload = {
        "content": {
            "title": "5 AI Tools That Changed My Life",
            "content_type": "VIRAL",
            "platform": "LinkedIn",
            "content_ownership": "ORIGINAL"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/generate-draft", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    assert "draft" in data
    assert data["draft"]["title"] == "5 AI Tools That Changed My Life"
    assert data["draft"]["platform"] == "LinkedIn"
    assert data["draft"]["word_count"] > 100
    assert data["metadata"]["used_research"] == False

def test_generate_draft_with_research():
    """Test generowania draftu z research data"""
    research_data = {
        "findings": {
            "summary": "AI tools like ChatGPT, Midjourney, GitHub Copilot, Notion AI, and RunwayML are revolutionizing productivity and creativity.",
            "key_points": [
                "ChatGPT for content generation",
                "Midjourney for visual creation",
                "GitHub Copilot for coding",
                "Notion AI for organization",
                "RunwayML for video editing"
            ]
        }
    }
    
    payload = {
        "content": {
            "title": "5 AI Tools That Changed My Life",
            "content_type": "VIRAL",
            "platform": "LinkedIn"
        },
        "research_data": research_data
    }
    
    response = requests.post(f"{BASE_URL}/api/generate-draft", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    assert data["metadata"]["used_research"] == True

def test_generate_draft_twitter():
    """Test generowania krótkiego contentu dla Twitter"""
    payload = {
        "content": {
            "title": "AI is changing everything",
            "content_type": "VIRAL",
            "platform": "Twitter"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/generate-draft", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    assert data["draft"]["platform"] == "Twitter"
    # Twitter content should be concise
    assert len(data["draft"]["content"]) <= 1500  # reasonable for a tweet thread

def test_generate_draft_technical_blog():
    """Test generowania technicznego contentu dla bloga"""
    payload = {
        "content": {
            "title": "Understanding Kubernetes Operators",
            "content_type": "TECHNICAL",
            "platform": "Blog"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/generate-draft", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    assert data["draft"]["platform"] == "Blog"
    assert data["draft"]["word_count"] >= 300  # Technical content should be detailed

def test_execute_complete_flow():
    """Test kompletnego flow: routing → research → writing"""
    payload = {
        "title": "The Future of Remote Work",
        "content_type": "STANDARD",
        "platform": "LinkedIn",
        "content_ownership": "EXTERNAL"
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-flow", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "flow_id" in data
    assert data["status"] == "completed"
    assert "execution_log" in data
    assert len(data["execution_log"]) >= 3  # routing, research, draft
    
    # Sprawdź czy każdy krok ma wymagane pola
    for step in data["execution_log"]:
        assert "step" in step
        assert "result" in step
        assert "duration_ms" in step
    
    # Sprawdź finalny draft
    assert "final_draft" in data
    assert data["final_draft"]["title"] == payload["title"]

def test_execute_flow_skip_research():
    """Test flow pomijający research dla ORIGINAL content"""
    payload = {
        "title": "My Personal Experience with AI",
        "content_type": "STANDARD",
        "platform": "LinkedIn",
        "content_ownership": "ORIGINAL"
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-flow", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    assert data["routing_decision"] == "skip_research_flow"
    
    # Sprawdź że research został pominięty
    research_steps = [s for s in data["execution_log"] if s["step"] == "research"]
    assert len(research_steps) == 0
    
    # Powinny być tylko routing i draft
    assert len(data["execution_log"]) == 2

def test_execute_flow_technical_deep_dive():
    """Test flow z deep research dla TECHNICAL content"""
    payload = {
        "title": "Implementing Distributed Tracing in Microservices",
        "content_type": "TECHNICAL",
        "platform": "Blog",
        "content_ownership": "EXTERNAL"
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-flow", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    assert data["routing_decision"] == "technical_deep_dive_flow"
    
    # Znajdź research step
    research_step = next((s for s in data["execution_log"] if s["step"] == "research"), None)
    assert research_step is not None
    assert research_step["result"]["depth"] == "deep"
    
    # Technical content powinien być długi
    assert data["final_draft"]["word_count"] >= 400

def test_execute_flow_viral_twitter():
    """Test flow dla VIRAL content na Twitter"""
    payload = {
        "title": "Why AI Won't Replace Developers",
        "content_type": "VIRAL",
        "platform": "Twitter",
        "content_ownership": "EXTERNAL"
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-flow", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "completed"
    assert data["routing_decision"] == "viral_engagement_flow"
    assert data["final_draft"]["platform"] == "Twitter"

def test_execute_flow_timing():
    """Test że flow zwraca realistyczne czasy wykonania"""
    payload = {
        "title": "Test Timing Analysis",
        "content_type": "STANDARD",
        "platform": "LinkedIn",
        "content_ownership": "EXTERNAL"
    }
    
    response = requests.post(f"{BASE_URL}/api/execute-flow", json=payload)
    data = response.json()
    
    # Sprawdź całkowity czas
    assert "total_duration_ms" in data
    assert data["total_duration_ms"] > 1000  # Minimum 1 sekunda
    assert data["total_duration_ms"] < 120000  # Maximum 2 minuty
    
    # Sprawdź czasy poszczególnych kroków
    for step in data["execution_log"]:
        assert step["duration_ms"] > 0
        if step["step"] == "research":
            # Research powinien trwać co najmniej kilka sekund
            assert step["duration_ms"] > 5000
        elif step["step"] == "draft_generation":
            # Draft generation też powinien trwać trochę
            assert step["duration_ms"] > 1000