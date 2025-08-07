# Environment Configuration

## 🔧 Konfiguracja zmiennych środowiskowych

### 1. Skopiuj przykładowy plik .env
```bash
cp .env.example .env
```

### 2. Edytuj .env według potrzeb
```bash
# Ścieżki do folderów
CONTENT_RAW_PATH=/Users/hretheum/dev/bezrobocie/vector-wave/content/raw
CONTENT_NORMALIZED_PATH=/Users/hretheum/dev/bezrobocie/vector-wave/content/normalized

# Feature flags
ARCHIVE_PROCESSED_CONTENT=false  # Ustaw na true aby archiwizować przetworzone treści
USE_CREWAI_FLOW=true            # Używaj Flow zamiast podstawowego Crew
```

## 📋 Dostępne zmienne

### Ścieżki
- `CONTENT_RAW_PATH` - Folder z surowymi treściami do przetworzenia
- `CONTENT_NORMALIZED_PATH` - Folder z znormalizowanymi treściami

### Feature Flags
- `ARCHIVE_PROCESSED_CONTENT` - Czy archiwizować/czyścić folder raw po przetworzeniu
  - `false` (domyślnie) - Nie czyści, zostawia pliki
  - `true` - Archiwizuje przetworzone pliki (TODO: implementacja)
  
- `USE_CREWAI_FLOW` - Wybór implementacji
  - `true` (domyślnie) - Używa CrewAI Flow z logiką warunkową
  - `false` - Używa oryginalnej implementacji Crew

### API Keys (opcjonalne)
- `OPENAI_API_KEY` - Klucz API OpenAI
- `ANTHROPIC_API_KEY` - Klucz API Anthropic

## 🚀 Użycie

### Ze skryptem startowym
Skrypt automatycznie załaduje .env:
```bash
./start-flow.sh
```

### Ręczne uruchomienie
```bash
# Załaduj zmienne środowiskowe
source .env

# Uruchom backend
cd ai_publishing_cycle && python src/ai_publishing_cycle/copilot_backend.py
```

## ⚠️ Ważne

1. **Nigdy nie commituj .env** - Plik jest w .gitignore
2. **Używaj ścieżek absolutnych** - Względne mogą nie działać poprawnie
3. **Sprawdź uprawnienia** - Backend musi mieć dostęp do folderów

## 🔍 Troubleshooting

### "No content in raw folder"
- Sprawdź czy `CONTENT_RAW_PATH` wskazuje na właściwy folder
- Upewnij się że folder zawiera podfoldery z plikami .md

### "Permission denied"
- Sprawdź uprawnienia do folderów
- Użyj `chmod -R 755 content/` jeśli potrzeba

### Zmienne się nie ładują
- Upewnij się że .env jest w głównym folderze kolegium
- Sprawdź czy nie ma błędów składni w .env