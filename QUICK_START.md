# Quick Start Guide

## 🚀 Automatyczne uruchomienie (rekomendowane)

```bash
./start-flow.sh
```

## 🔧 Ręczne uruchomienie

### Terminal 1 - Backend
```bash
# Aktywuj venv (jeśli używasz)
source ai_publishing_cycle/.venv/bin/activate  # lub .venv/bin/activate

# Uruchom backend
cd ai_publishing_cycle && USE_CREWAI_FLOW=true python src/ai_publishing_cycle/copilot_backend.py
```

### Terminal 2 - Frontend
```bash
cd vector-wave-ui
npm install  # tylko za pierwszym razem
npm run dev
```

## 📍 Adresy

- Frontend: http://localhost:3000
- Backend: http://localhost:8001
- Health check: http://localhost:8001/health

## 🐛 Troubleshooting

### "No such file or directory: vector-wave-ui"
Upewnij się że jesteś w folderze `kolegium`:
```bash
pwd  # powinno pokazać: .../vector-wave/kolegium
```

### "source: command not found"
Używasz shell który nie wspiera `source`. Spróbuj:
```bash
. ai_publishing_cycle/.venv/bin/activate
```

### "ModuleNotFoundError"
Zainstaluj zależności:
```bash
cd ai_publishing_cycle
pip install -r requirements.txt
```

### Port już zajęty
Zatrzymaj poprzednie instancje:
```bash
lsof -ti:8001 | xargs kill  # Backend
lsof -ti:3000 | xargs kill  # Frontend
```