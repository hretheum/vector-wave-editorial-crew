# CrewAI Conditional Flow - Propozycja Implementacji

## Problem
Różne typy contentu wymagają różnych kryteriów oceny:
- **Content własny** - nie wymaga weryfikacji źródeł
- **Content ze źródłami** - wymaga sprawdzenia min. 3 źródeł

## Rozwiązanie: Router-based Flow

### 1. State Management (SharedState)

```python
from crewai.flow.flow import Flow, start, router
from pydantic import BaseModel
from typing import List, Optional

class ContentAnalysisState(BaseModel):
    """Shared state for content analysis flow"""
    folder_path: str
    content_type: str  # SERIES or STANDALONE
    content_ownership: str  # ORIGINAL or EXTERNAL
    files: List[str]
    analysis_results: dict = {}
    quality_score: Optional[float] = None
    recommendations: List[str] = []
```

### 2. Flow z Routerem

```python
class ContentAnalysisFlow(Flow[ContentAnalysisState]):
    
    @start()
    def analyze_content_type(self):
        """Initial analysis to determine content type and ownership"""
        # Logika detekcji typu i autorstwa
        files = self._get_files(self.state.folder_path)
        
        # Sprawdź czy to seria
        is_series = len(files) > 5 and self._has_numbering(files)
        self.state.content_type = "SERIES" if is_series else "STANDALONE"
        
        # Sprawdź autorstwo
        has_sources = self._check_for_sources(files[0])
        self.state.content_ownership = "EXTERNAL" if has_sources else "ORIGINAL"
        
        return self.state
    
    @router()
    def route_by_ownership(self):
        """Router deciding which validation path to take"""
        if self.state.content_ownership == "ORIGINAL":
            return "validate_original_content"
        else:
            return "validate_sourced_content"
    
    @listen("validate_original_content")
    def validate_original_content(self):
        """Validation for original content (without source requirements)"""
        crew = Crew(
            agents=[
                # NIE UŻYWAMY content_scout_agent - nie ma sensu szukać źródeł dla własnego contentu
                style_guide_agent,
                voice_consistency_agent,
                engagement_agent,
                viral_analyzer_agent
            ],
            tasks=[
                Task(
                    description="Sprawdź zgodność ze style guide BEZ wymogu źródeł",
                    expected_output="Ocena zgodności ze stylem",
                    agent=style_guide_agent,
                    context={"skip_source_check": True}
                ),
                Task(
                    description="Oceń spójność głosu i tonu",
                    expected_output="Analiza spójności narracji",
                    agent=voice_consistency_agent
                ),
                Task(
                    description="Przeanalizuj potencjał zaangażowania",
                    expected_output="Ocena viralowości i engagement",
                    agent=engagement_agent
                ),
                # ... inne taski
            ]
        )
        
        result = crew.kickoff({
            "content": self.state.files,
            "style_guide": self._load_style_guide()
        })
        
        self.state.analysis_results["style_compliance"] = result
        return self.state
    
    @listen("validate_sourced_content")
    def validate_sourced_content(self):
        """Full validation including source verification"""
        crew = Crew(
            agents=[
                content_scout_agent,  # UŻYWAMY content scout dla contentu ze źródłami
                style_guide_agent,
                source_verification_agent,
                fact_checking_agent,
                voice_consistency_agent,
                engagement_agent
            ],
            tasks=[
                Task(
                    description="Znajdź dodatkowe źródła i kontekst",
                    expected_output="Lista dodatkowych źródeł i insights",
                    agent=content_scout_agent
                ),
                Task(
                    description="Sprawdź zgodność ze style guide WŁĄCZNIE z weryfikacją źródeł",
                    expected_output="Ocena zgodności ze stylem + weryfikacja min. 3 źródeł",
                    agent=style_guide_agent
                ),
                Task(
                    description="Zweryfikuj jakość i wiarygodność źródeł",
                    expected_output="Raport weryfikacji źródeł",
                    agent=source_verification_agent
                ),
                # ... inne taski
            ]
        )
        
        result = crew.kickoff({
            "content": self.state.files,
            "style_guide": self._load_style_guide()
        })
        
        self.state.analysis_results["style_compliance"] = result
        return self.state
    
    @listen(["validate_original_content", "validate_sourced_content"])
    def generate_final_report(self):
        """Common final step for both paths"""
        # Generowanie raportu końcowego
        self.state.quality_score = self._calculate_score()
        self.state.recommendations = self._generate_recommendations()
        
        return self.state
```

### 3. Conditional Crew Configuration

```python
def create_dynamic_crew(content_ownership: str) -> Crew:
    """Factory for creating crew based on content type"""
    
    base_agents = [
        Agent(
            role="Style Guide Validator",
            goal="Sprawdź zgodność ze style guide",
            backstory="Ekspert od spójności treści"
        ),
        Agent(
            role="Engagement Analyzer",
            goal="Oceń potencjał zaangażowania",
            backstory="Specjalista od viralowości"
        )
    ]
    
    base_tasks = [
        Task(
            description="Analiza zgodności ze stylem",
            agent=base_agents[0]
        ),
        Task(
            description="Ocena potencjału wiralowego",
            agent=base_agents[1]
        )
    ]
    
    if content_ownership == "EXTERNAL":
        # Dodaj agentów do weryfikacji źródeł
        source_agent = Agent(
            role="Source Verifier",
            goal="Weryfikuj jakość i ilość źródeł",
            backstory="Fact-checker z doświadczeniem dziennikarskim"
        )
        
        base_agents.append(source_agent)
        base_tasks.insert(1, Task(
            description="Sprawdź czy content ma min. 3 wiarygodne źródła",
            agent=source_agent,
            expected_output="Lista źródeł z oceną wiarygodności"
        ))
    
    return Crew(
        agents=base_agents,
        tasks=base_tasks,
        process=Process.sequential
    )
```

### 4. Wykorzystanie w Pipeline

```python
# W głównym pipeline
flow = ContentAnalysisFlow()
result = await flow.kickoff({
    "folder_path": "content/raw/2025-07-31-brainstorm"
})

# State zawiera wszystkie wyniki
print(f"Typ contentu: {result.content_type}")
print(f"Autorstwo: {result.content_ownership}")
print(f"Wynik analizy: {result.quality_score}")
print(f"Rekomendacje: {result.recommendations}")
```

## Korzyści

1. **Elastyczność** - różne ścieżki dla różnych typów contentu
2. **Wydajność** - nie uruchamiamy niepotrzebnych agentów
3. **Klarowność** - jasno zdefiniowane flow dla każdego przypadku
4. **Skalowalność** - łatwo dodać nowe typy contentu lub kryteria

## Alternatywa: Conditional Tasks

```python
@task
def validate_style_guide(self):
    """Task with conditional logic inside"""
    if self.state.content_ownership == "ORIGINAL":
        # Uproszczona walidacja
        prompt = "Sprawdź zgodność ze style guide (pomiń wymagania dot. źródeł)"
    else:
        # Pełna walidacja
        prompt = "Sprawdź zgodność ze style guide włącznie z weryfikacją min. 3 źródeł"
    
    return self.agent.execute(prompt)
```

## Kluczowe różnice między ścieżkami

### Content Własny (ORIGINAL)
**Pomijamy:**
- ❌ Content Scout Agent - nie szukamy zewnętrznych źródeł
- ❌ Source Verification Agent - nie weryfikujemy źródeł
- ❌ Fact Checking Agent - nie sprawdzamy faktów ze źródłami
- ❌ Wymaganie min. 3 źródeł w style guide

**Skupiamy się na:**
- ✅ Spójności głosu i stylu
- ✅ Oryginalności i kreatywności
- ✅ Potencjale zaangażowania
- ✅ Zgodności z brand voice

### Content ze Źródłami (EXTERNAL)
**Używamy pełnego zestawu:**
- ✅ Content Scout - szuka dodatkowych źródeł
- ✅ Source Verification - weryfikuje wiarygodność
- ✅ Fact Checking - sprawdza fakty
- ✅ Pełna walidacja style guide (włącznie z min. 3 źródłami)

## Rekomendacja

Polecam użycie **Router-based Flow** dla czystości kodu i łatwości utrzymania. Pozwala to na:
- Wyraźne rozdzielenie logiki dla różnych typów contentu
- Łatwe dodawanie nowych typów w przyszłości
- Lepszą testowalność poszczególnych ścieżek
- Czytelniejsze logi i debugging
- Oszczędność zasobów - nie uruchamiamy niepotrzebnych agentów