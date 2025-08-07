# AI Kolegium Redakcyjne - CrewAI Flow Implementation

## 🚀 Szybki start

### Opcja 1: Skrypt startowy (rekomendowane)
```bash
./start-flow.sh
```

### Opcja 2: Ręczne uruchomienie
```bash
# W jednym terminalu - backend z Flow
cd ai_publishing_cycle && USE_CREWAI_FLOW=true python src/ai_publishing_cycle/copilot_backend.py

# W drugim terminalu - frontend
cd vector-wave-ui && npm run dev
```

### Otwórz w przeglądarce
http://localhost:3000

## 🔄 Jak działa Flow

### Automatyczna detekcja contentu
System automatycznie wykrywa:
- **ORIGINAL**: Content bez źródeł → uproszczona walidacja
- **EXTERNAL**: Content ze źródłami → pełna weryfikacja

### Różne ścieżki walidacji

#### Content ORIGINAL (własny)
```
Start → Detekcja → Router → Walidacja ORIGINAL → Raport
                                    ↓
                          • Bez Content Scout
                          • Bez weryfikacji źródeł  
                          • Focus na kreatywności
```

#### Content EXTERNAL (ze źródłami)
```
Start → Detekcja → Router → Walidacja EXTERNAL → Raport
                                    ↓
                          • Content Scout aktywny
                          • Min. 3 źródła wymagane
                          • Fact-checking
```

## 📊 Wyniki w UI

UI automatycznie pokazuje:
- Typ contentu (SERIES/STANDALONE)
- Własność contentu (ORIGINAL/EXTERNAL)
- Wyniki Flow (approved/rejected/human review)
- Ścieżkę walidacji

## 🛠️ Konfiguracja

### Przełączanie między Flow a Crew
```bash
# Użyj Flow (domyślnie)
USE_CREWAI_FLOW=true python main.py

# Użyj oryginalnego Crew
USE_CREWAI_FLOW=false python main.py
```

### Mock mode (bez CrewAI)
Jeśli CrewAI nie jest zainstalowane, backend automatycznie przełączy się na mock analysis.

## 📁 Struktura

```
kolegium/
├── ai_kolegium_redakcyjne/
│   ├── kolegium_flow.py        # Implementacja Flow
│   ├── crew.py                 # Oryginalna implementacja
│   └── main.py                 # Wspiera obie wersje
├── ai_publishing_cycle/
│   └── copilot_backend.py      # API endpoint z Flow support
└── vector-wave-ui/
    └── app/page.tsx            # UI z Flow results display
```

## 🧪 Testowanie

### Test content ORIGINAL
Utwórz plik bez źródeł:
```markdown
# Mój własny pomysł

To jest moja oryginalna koncepcja...
```

### Test content EXTERNAL
Utwórz plik ze źródłami:
```markdown
# Analiza rynku AI

Według raportu Gartner [1], rynek AI rośnie...

Źródła:
[1] https://gartner.com/ai-report-2025
```

## 🐛 Troubleshooting

### "CrewAI Flow not available"
```bash
pip install crewai crewai-tools
```

### Backend nie odpowiada
Sprawdź czy działa na porcie 8001:
```bash
curl http://localhost:8001/health
```

### Flow się nie uruchamia
Sprawdź logi - Flow loguje każdy krok:
- 🔍 Analyzing content ownership
- ➡️ Routing to validation path
- 🎨 Validating ORIGINAL content
- 📚 Validating EXTERNAL content