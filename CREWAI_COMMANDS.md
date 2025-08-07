# CrewAI Commands Guide

## 🚀 Szybkie użycie

### Opcja 1: Używaj wrapper script (najłatwiejsze)
```bash
./crewai.sh --help
./crewai.sh flow plot
./crewai.sh flow run
```

### Opcja 2: Aktywuj venv ręcznie
```bash
source ai_kolegium_redakcyjne/.venv/bin/activate
crewai --help
```

## 📋 Przydatne komendy CrewAI

### Flow Commands
```bash
# Pokaż diagram flow
crewai flow plot

# Uruchom flow
crewai flow run

# Testuj flow
crewai flow test
```

### Crew Commands
```bash
# Uruchom crew
crewai run

# Trenuj crew
crewai train

# Powtórz wykonanie
crewai replay <task_id>

# Testuj crew
crewai test
```

### Narzędzia diagnostyczne
```bash
# Sprawdź wersję
crewai --version

# Pomoc
crewai --help

# Pomoc dla konkretnej komendy
crewai flow --help
```

## 🔧 Lokalizacje CrewAI

CrewAI jest zainstalowane w następujących venv:
- `ai_kolegium_redakcyjne/.venv` (główne)
- `ai_publishing_cycle/.venv`
- `.venv` (jeśli istnieje)

## 📊 Generowanie diagramów Flow

Aby wygenerować diagram flow:
```bash
cd ai_kolegium_redakcyjne
source .venv/bin/activate
crewai flow plot
```

To stworzy plik `crewai_flow.html` z interaktywnym diagramem.

## 🐛 Troubleshooting

### "command not found: crewai"
Musisz aktywować virtual environment:
```bash
source ai_kolegium_redakcyjne/.venv/bin/activate
```

### "No flow found"
Upewnij się że jesteś w folderze z kodem flow:
```bash
cd ai_kolegium_redakcyjne/src/ai_kolegium_redakcyjne
```

### Instalacja CrewAI
Jeśli nie masz CrewAI:
```bash
pip install crewai crewai-tools
```