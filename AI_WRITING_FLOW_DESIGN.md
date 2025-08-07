# 🎯 Rekomendacja architektury `ai_writing_flow`

Na podstawie analizy styleguide Vector Waves i istniejącego flow kolegium, proponuję następującą architekturę dla `ai_writing_flow`:

## 1. **Struktura Flow - Wieloetapowy proces**

📊 **[Zobacz diagram przepływu →](./AI_WRITING_FLOW_DIAGRAM.md)**

### Podział odpowiedzialności:

**Kolegium Redakcyjne** (już zaimplementowane):
- Topic Discovery - odkrywanie trendów
- Viral Analysis - ocena potencjału (viral score)
- Content Type Detection - STANDALONE vs SERIES
- Ownership Analysis - ORIGINAL vs EXTERNAL
- Editorial Decision - wstępna decyzja
- Quality Assessment - ocena jakości

**AI Writing Flow** (do implementacji):
- Deep Content Research - głęboki research ze źródłami
- Audience Alignment - dostosowanie do person
- Draft Generation - tworzenie treści
- Style Guide Validation - walidacja stylu
- Platform Adaptation - wersje dla platform
- Final Polish - ostateczne szlify

**Przepływ danych z Kolegium do Writing Flow:**
- `topic_title` - wybrany temat
- `viral_score` - potencjał wiralny
- `content_type` - typ contentu
- `folder_path` - ścieżka do źródeł
- `content_ownership` - własność contentu
- `editorial_recommendations` - rekomendacje

## 2. **Agenty w ai_writing_flow**

### **2.1 Research Agent** [ENHANCED WITH KNOWLEDGE BASE]
```yaml
Rola: Deep Research Specialist
Zadania:
- Zbiera minimum 3 primary sources (styleguide requirement)
- Weryfikuje aktualność danych (<6 miesięcy)
- Tworzy evidence-based foundation
- Dokumentuje metodologię research
- Wykorzystuje Knowledge Base dla CrewAI patterns

Tools:
- search_crewai_knowledge() - dostęp do KB
- get_flow_examples() - przykłady patterns
- troubleshoot_crewai() - debugging help
- read_source_files() - lokalne źródła
- extract_sources() - ekstrakcja referencji

Reguły ze styleguide:
- "Test Everything" - każde twierdzenie musi być weryfikowalne
- "Show Our Work" - transparentne źródła
- NIE używa "revolutionary" bez dowodów
```

### **2.2 Audience Mapper**
```yaml
Rola: Target Audience Specialist
Zadania:
- Mapuje content do 4 person (z 02-audience.md):
  * Technical Founder (35%)
  * Senior Engineer (30%)
  * Decision Maker (25%)
  * Skeptical Learner (10%)
- Dostosowuje głębokość techniczną
- Kalibruje ton i formalizm

Reguły:
- Level 1-3 technical depth calibration
- Specific needs per persona
```

### **2.3 Content Writer**
```yaml
Rola: Master Content Creator
Zadania:
- Generuje draft według typu contentu:
  * Deep Analysis (3000+ words)
  * Quick Takes (500-800 words)
  * Technical Tutorials
  * Industry Critique
- Implementuje Voice & Tone guidelines
- Dodaje "non-obvious insights"

Reguły:
- Obsessively Specific
- Confidently Uncertain
- Professionally Irreverent
```

### **2.4 Style Validator**
```yaml
Rola: Brand Consistency Guardian
Zadania:
- Sprawdza forbidden phrases blacklist
- Weryfikuje technical accuracy
- Waliduje data presentation
- Kontroluje humor guidelines

Reguły:
- Zero "leverage", "seamless", "revolutionary"
- Kod musi działać w fresh environment
- Wersje i benchmarki wymagane
```

### **2.5 Platform Optimizer**
```yaml
Rola: Multi-Platform Specialist
Zadania:
- Adaptuje content do platform:
  * LinkedIn (professional, stats)
  * Twitter (krótko, emotki, hashtagi)
  * Beehiiv (rozbudowane, praktyczne)
  * Medium (narrative, code blocks)
- Optymalizuje format i długość
- Dodaje platform-specific elementy

Reguły:
- Zachowuje core message
- Dostosowuje ton do platformy
- Maksymalizuje engagement
```

### **2.6 Quality Controller**
```yaml
Rola: Final Gatekeeper
Zadania:
- Fact-checking wszystkich claims
- Weryfikacja kodu w sandbox
- Ethics checklist
- Performance predictions

Reguły:
- Instant rejection dla blacklisted phrases
- Human review dla controversy >0.7
- Corrections protocol ready
```

## 3. **Procesy redakcyjne w Flow**

### **3.1 Evidence Loop**
```python
# Każdy claim musi przejść przez:
1. Source identification
2. Verification
3. Documentation
4. Cross-reference check
```

### **3.2 Revision Cycles**
```python
# Maksymalnie 3 iteracje:
1. Content improvement
2. Style alignment
3. Platform optimization

# Po 3 iteracjach → human intervention
```

### **3.3 Conditional Paths**
```python
if content_type == "TECHNICAL_TUTORIAL":
    → Code Testing Pipeline
elif controversy_score > 0.7:
    → Editorial Review Board
elif viral_score > 0.8:
    → Fast Track Publication
```

## 4. **Output: Publication Package**

```yaml
Finalne materiały:
1. Core Content:
   - Master draft (canonical version)
   - Platform variants (LinkedIn, Twitter, etc.)
   - Code repository (jeśli dotyczy)

2. Supporting Assets:
   - Data visualizations (accessible colors)
   - Source documentation
   - Performance benchmarks

3. Metadata:
   - Target audiences scores
   - Controversy assessment
   - Predicted metrics
   - Review schedule (3/6/12/24 months)

4. Action Items:
   - Suggested publication times
   - Cross-promotion strategy
   - Response templates
```

## 5. **Integration z UI - Przyciski kontekstowe**

Po zakończeniu flow, w ChatPanel pojawią się:
```typescript
contextActions: [
  {
    label: "📅 Zaplanuj publikację",
    action: () => openScheduler(package)
  },
  {
    label: "🔄 Wygeneruj warianty",
    action: () => generateMoreVariants(topic)
  },
  {
    label: "📊 Preview na platformach",
    action: () => showPlatformPreviews()
  },
  {
    label: "🚀 Publikuj teraz",
    action: () => publishWithConfirmation()
  }
]
```

## 6. **Konfiguracja CrewAI Flow**

```python
class WritingFlowState(BaseModel):
    # Input from Kolegium
    topic_title: str
    platform: str
    folder_path: str
    content_type: str  # STANDALONE/SERIES
    content_ownership: str  # ORIGINAL/EXTERNAL
    viral_score: float
    editorial_recommendations: str
    
    # Process tracking
    research_sources: List[Dict]
    audience_alignment: Dict[str, float]
    draft_versions: List[str]
    style_violations: List[str]
    
    # Output
    final_draft: str
    platform_variants: Dict[str, str]
    publication_metadata: Dict
    quality_score: float
```

### Integracja z Kolegium:
```python
# W UI po analizie kolegium:
if topic.viral_score > 0.7 and topic.approved:
    writing_flow_input = {
        "topic_title": topic.title,
        "platform": topic.recommended_platform,
        "folder_path": analysis_result.folder,
        "content_type": analysis_result.contentType,
        "content_ownership": analysis_result.contentOwnership,
        "viral_score": topic.viralScore,
        "editorial_recommendations": analysis_result.recommendation
    }
    
    # Uruchom AI Writing Flow
    await runWritingFlow(writing_flow_input)
```

## 7. **Kluczowe cechy implementacji**

1. **Styleguide-First Approach**
   - Każdy agent ma wbudowane reguły ze styleguide
   - Automatic rejection dla forbidden phrases
   - Enforced evidence requirements

2. **Multi-Stage Validation**
   - Research validation
   - Style compliance
   - Platform optimization
   - Final quality gate

3. **Human-in-the-Loop Triggers**
   - Controversy > 0.7
   - Failed ethics checklist
   - 3+ revision cycles
   - Sensitive topics

4. **Measurable Success**
   - 80%+ completion rate
   - <2% correction frequency

5. **Knowledge Base Integration** [NEW]
   - Full access to CrewAI documentation
   - Pattern examples for common tasks
   - Troubleshooting assistance
   - Hybrid search strategies
   - Circuit breaker for resilience
   - Platform-specific engagement metrics

## Podsumowanie

Zaprojektowałem kompleksowy `ai_writing_flow` który:

1. **Respektuje wszystkie reguły styleguide** - od forbidden phrases po evidence requirements
2. **Implementuje wieloetapową walidację** - research → writing → style → quality → platform
3. **Dostosowuje się do 4 person** zdefiniowanych w styleguide
4. **Generuje kompletny pakiet publikacyjny** z wariantami dla różnych platform
5. **Ma wbudowane mechanizmy bezpieczeństwa** - blacklisty, ethics checks, human triggers

Flow jest gotowy do implementacji i integracji z UI poprzez przyciski kontekstowe w ChatPanel.

## Implementation Status ✅ (2025-08-02)

### Completed

1. **All 5 agents implemented** in `ai_writing_flow/crews/`:
   - `research_crew.py` - Deep research and source extraction
   - `audience_crew.py` - Target audience mapping  
   - `writer_crew.py` - Content generation with style
   - `style_crew.py` - Vector Wave style validation
   - `quality_crew.py` - Final quality assessment

2. **Tools created**:
   - `styleguide_loader.py` - Loads Vector Wave style rules
   - `ui_bridge.py` - Human feedback interface

3. **UI Integration complete**:
   - API endpoints in `copilot_backend.py`
   - ChatPanel updated with draft generation buttons
   - Human feedback loop with 4 decision options
   - Real-time status polling

4. **Flow architecture**:
   - Conditional routing for ORIGINAL/EXTERNAL content
   - Human-in-the-loop at key decision points
   - Max 3 revisions before escalation
   - Full state management in WritingFlowState

### Next Steps

1. **Test flow** with real content examples
2. **Add WebSocket/SSE** for real-time progress updates
3. **Performance optimization** for faster generation
4. **Production deployment** with monitoring