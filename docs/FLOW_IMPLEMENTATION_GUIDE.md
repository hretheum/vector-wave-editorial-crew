# CrewAI Flow Implementation Guide

## 🚀 Overview

Zaimplementowaliśmy CrewAI Flow w AI Kolegium Redakcyjne, które obsługuje logikę warunkową dla różnych typów contentu.

## 🔄 Jak to działa

### 1. Detekcja typu contentu

System automatycznie wykrywa:
- **Typ contentu**: SERIES (>5 plików z numeracją) vs STANDALONE
- **Własność contentu**: ORIGINAL (bez źródeł) vs EXTERNAL (ze źródłami)

### 2. Routing warunkowy

```python
@router(analyze_content_ownership)
def route_by_content_ownership(self):
    if self.state.content_ownership == "ORIGINAL":
        return "validate_original_content"
    else:
        return "validate_external_content"
```

### 3. Różne ścieżki walidacji

#### Content ORIGINAL
- **Pomija**: Content Scout, weryfikację źródeł
- **Skupia się na**: Spójności głosu, kreatywności, potencjale wiralowym

#### Content EXTERNAL  
- **Pełna walidacja**: Content Scout, weryfikacja źródeł (min. 3)
- **Dodatkowe**: Fact-checking, analiza wiarygodności

## 📁 Struktura plików

```
ai_kolegium_redakcyjne/
├── src/ai_kolegium_redakcyjne/
│   ├── kolegium_flow.py      # Nowa implementacja Flow
│   ├── crew.py               # Oryginalna implementacja Crew
│   ├── config.py             # Konfiguracja i ładowanie style guides
│   └── main.py               # Wspiera obie implementacje
```

## 🔧 Użycie

### Domyślnie używa Flow:
```bash
python src/ai_kolegium_redakcyjne/main.py
```

### Przełączenie na oryginalną implementację:
```bash
USE_CREWAI_FLOW=false python src/ai_kolegium_redakcyjne/main.py
```

### Integracja z UI

Frontend automatycznie korzysta z Flow gdy analizuje foldery:
```typescript
const response = await fetch('http://localhost:8001/api/analyze-content', {
  method: 'POST',
  body: JSON.stringify({ folder: folderName })
});
```

## 📊 Wyniki analizy

Analiza zwraca:
```json
{
  "content_ownership": "ORIGINAL",
  "content_type": "SERIES",
  "flow_results": {
    "approved": 5,
    "rejected": 1,
    "human_review": 2
  },
  "recommendations": [
    "Content ownership: ORIGINAL",
    "Validation path: No source requirements",
    "Review editorial decisions in report"
  ]
}
```

## 🎯 Korzyści

1. **Efektywność** - nie uruchamiamy niepotrzebnych agentów
2. **Dokładność** - różne kryteria dla różnych typów contentu
3. **Skalowalność** - łatwo dodać nowe typy contentu
4. **Przejrzystość** - jasne ścieżki decyzyjne

## 🔮 Następne kroki

1. **Human-in-the-Loop** - dodanie możliwości interwencji człowieka
2. **Batch Processing** - przetwarzanie wielu folderów jednocześnie
3. **Real-time Events** - streaming wydarzeń do UI
4. **Persystencja stanu** - zapisywanie stanu flow dla późniejszego wznowienia