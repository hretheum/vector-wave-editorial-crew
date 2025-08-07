# Architektura Aplikacji: AI Writing Flow





## Cel



Niniejszy dokument przedstawia projekt architektury aplikacji skupiającej się wyłącznie na komponencie **AI Writing Flow**, zgodnie z wymaganiami dotyczącymi konteneryzacji Docker (ARM64 dla Mac, AMD64 dla Ubuntu) i rekomendacjami z poprzedniego planu. Centralnym elementem tej architektury będzie CrewAI `Flow`, który będzie orkiestrował cały proces pisania, zarządzając logiką warunkową i pętlami, podczas gdy wyspecjalizowane `Crews` (zespoły agentów) będą wykonywać konkretne, inteligentne zadania.



## 1. Wysokopoziomowy Przegląd Architektury



Aplikacja będzie składać się z kilku kluczowych, konteneryzowanych komponentów:

- **Core Application Service (CrewAI Orchestrator):** Główny silnik aplikacji, który hostuje i zarządza `AI Writing Flow` oraz wywołuje poszczególne `Crews` i agentów. Będzie również wystawiać API do interakcji zewnętrznych (np. inicjowanie przepływu, odbieranie danych z przeglądu ludzkiego).
- **Database Service:** Baza danych do przechowywania stanu `Flow`, postępów zadań, generowanych szkiców treści oraz wszelkich metadanych.
- **Vector Database Service (Opcjonalnie/Zintegrowane):** Jeśli przewodnik stylu będzie implementowany z wykorzystaniem Retrieval-Augmented Generation (RAG), może to być oddzielna usługa bazy wektorowej lub zintegrowana biblioteka w ramach Core Application Service.
- **File Storage:** Miejsce do przechowywania surowych materiałów wejściowych i finalnych szkiców.mermaid graph TD A -->|Trigger AI Writing Flow (API Call)| B(Core Application Service) B -->|Manages Flow State| C(Database Service) B -->|Queries Style Guide (RAG)| D(Vector Database Service) B -->|Reads/Writes Content| E(File Storage) B -->|Sends Draft for Human Review| F[Zewnętrzny Interfejs Użytkownika] F -->|Sends Feedback (API Call)| B B -->|Interacts with| G[LLM Provider]

```
## 2. Szczegółowy Projekt Komponentów

### 2.1. Core Application Service (CrewAI Orchestrator)

*   **Technologia:** Python, CrewAI, FastAPI (lub podobny framework webowy do API).
*   **Rola:**
    *   **Orkiestracja Flow:** Definiuje i uruchamia główny `AI Writing Flow`, który odwzorowuje diagram z Image 1 (AI Writing Flow). Ten `Flow` będzie zarządzał przejściami stanów, logiką warunkową (`Content Type?`, `Human Review`, `Quality Check`) i pętlami (`Revision Loop`). [1]
    *   **Zarządzanie Crews:** W ramach `Flow`, Core Application Service będzie dynamicznie inicjować i zarządzać wyspecjalizowanymi `Crews` dla zadań wymagających autonomii i współpracy agentów (np. `ResearchCrew`, `WritingCrew`). [1]
    *   **Agenci i Narzędzia:** Będzie zawierać definicje wszystkich agentów (np. `ResearchAgent`, `ContentWriterAgent`, `AudienceMapperAgent`, `StyleValidatorAgent`, `QualityControllerAgent`) oraz ich `Tools`.
    *   **API Endpoints:**
        *   `/start_writing_flow`: Endpoint do inicjowania procesu pisania, przyjmujący jako dane wejściowe surową treść i jej typ (np. "ORIGINAL", "EXTERNAL").
        *   `/human_review_feedback`: Endpoint do odbierania informacji zwrotnych od człowieka po etapie `Human Review`.
    *   **Integracja z LLM:** Będzie komunikować się z zewnętrznym dostawcą LLM (np. OpenAI, Google Gemini) w celu wykonywania zadań przez agentów.
    *   **Zarządzanie Stanem:** Będzie zapisywać i odczytywać stan `Flow` oraz generowane szkice z Database Service, aby zapewnić ciągłość procesu, zwłaszcza w przypadku długotrwałych operacji lub interwencji ludzkich.

### 2.2. Database Service

*   **Technologia:** PostgreSQL (zalecane dla produkcji), SQLite (dla lokalnego rozwoju).
*   **Rola:**
    *   **Stan Flow:** Przechowywanie bieżącego stanu `AI Writing Flow` (np. który krok jest aktywny, jakie były wyniki poprzednich decyzji).
    *   **Szkice Treści:** Zapisywanie generowanych szkiców treści na różnych etapach procesu, co umożliwia audyt i wznowienie pracy.
    *   **Metadane:** Przechowywanie metadanych związanych z każdym zadaniem pisania (np. typ treści, historia rewizji, informacje zwrotne od człowieka).

### 2.3. Vector Database Service (dla Przewodnika Stylu)

*   **Technologia:** ChromaDB, Weaviate, Pinecone (lub wbudowana biblioteka RAG, np. FAISS, w Core Application Service dla prostszych przypadków).
*   **Rola:**
    *   **Przewodnik Stylu jako Tool:** Przechowywanie wektorowych reprezentacji przewodnika stylu. Agenci (np. `StyleValidatorAgent`, `ContentWriterAgent`) będą używać `Tool`, które odpytuje tę bazę danych, aby dynamicznie pobierać odpowiednie zasady i przykłady stylistyczne. [1]
    *   **Dynamiczne Zapytania:** Umożliwia agentom zadawanie pytań dotyczących stylu i otrzymywanie kontekstowych odpowiedzi, zamiast polegania na statycznych instrukcjach.

### 2.4. File Storage

*   **Technologia:** Lokalny system plików (dla Docker Compose), S3-compatible storage (np. MinIO, AWS S3) dla produkcji.
*   **Rola:**
    *   **Materiały Wejściowe:** Przechowywanie surowych materiałów, które są początkowym wejściem do `AI Writing Flow`.
    *   **Szkice/Wyniki:** Opcjonalne przechowywanie finalnych szkiców lub pośrednich wyników w łatwo dostępnym formacie.

## 3. Implementacja Logiki Warunkowej i Pętli (w Core Application Service)

*   **"Content Type?" (Diament):** `Flow` będzie zawierał stan, który po otrzymaniu początkowych danych wejściowych (z `/start_writing_flow` API) oceni `content_type`. Na podstawie tej zmiennej, `Flow` przejdzie do stanu `DeepContentResearchState` (jeśli "EXTERNAL") lub `AudienceAlignmentState` (jeśli "ORIGINAL" lub "UI override").
*   **"Deep Content Research" (Niebieski Prostokąt):** W tym stanie, `Flow` zainicjuje `ResearchCrew` (z `ResearchAgent`), która wykona zadanie badawcze. `Flow` będzie czekał na zakończenie pracy `ResearchCrew` przed przejściem do następnego stanu.
*   **"Draft Generation" (Pomarańczowy Prostokąt):** Podobnie, `Flow` zainicjuje `WritingCrew` (z `ContentWriterAgent`) do generowania szkicu.
*   **"Human Review (UI Integration)" (Diament):**
    *   `Flow` przejdzie do specyficznego stanu `AWAITING_HUMAN_REVIEW`.
    *   W tym stanie, Core Application Service wyśle wygenerowany szkic do zewnętrznego interfejsu użytkownika (np. poprzez webhook lub API).
    *   `Flow` zostanie wstrzymany, czekając na wywołanie zwrotne z `/human_review_feedback` API, które dostarczy decyzję człowieka ("Minor Edits" lub "Content Changes").
    *   Po otrzymaniu danych zwrotnych, `Flow` wznowi działanie i przejdzie do odpowiedniego stanu: `StyleGuideValidationState` (dla "Minor Edits") lub z powrotem do `AudienceAlignmentState` / `DraftGenerationState` (dla "Content Changes").
*   **"Quality Check" (Diament):** `Flow` będzie zawierał stan, który po walidacji stylu oceni wynik `QualityControllerAgent`. Jeśli wynik to "PASS", `Flow` zakończy się sukcesem. Jeśli "FAIL", `Flow` przejdzie do stanu `RevisionLoopState`.
*   **"Revision Loop" (Czarny Prostokąt):** Ten stan w `Flow` będzie kierował proces z powrotem do `DraftGenerationState` (lub `AudienceAlignmentState`), umożliwiając agentom poprawę treści na podstawie informacji zwrotnych z kontroli jakości. `Flow` może śledzić liczbę rewizji, aby zapobiec nieskończonym pętlom.

## 4. Strategia Konteneryzacji Docker

### 4.1. Dockerfile dla Core Application Service

Będzie to wieloetapowy Dockerfile, aby wspierać zarówno ARM64 (Mac) jak i AMD64 (Ubuntu Server).

```dockerfile
# Etap budowania dla zależności
FROM --platform=$BUILDPLATFORM python:3.10-slim-buster AS builder

WORKDIR /app

# Ustawienie zmiennych środowiskowych dla architektury
ARG TARGETARCH
ENV TARGETARCH=$TARGETARCH

# Instalacja zależności systemowych, jeśli są potrzebne
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Etap końcowy
FROM --platform=$TARGETPLATFORM python:3.10-slim-buster

WORKDIR /app

# Kopiowanie zainstalowanych zależności z etapu budowania
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY..

# Ustawienie zmiennych środowiskowych dla CrewAI i LLM
ENV OPENAI_API_KEY="your_openai_api_key" # lub inna zmienna dla Twojego LLM
ENV CREW_AI_DB_URL="postgresql://user:password@db:5432/crewai_db" # lub sqlite:///./crewai.db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- `--platform=$BUILDPLATFORM` i `--platform=$TARGETPLATFORM` pozwalają Dockerowi na budowanie obrazów dla różnych architektur.
- `requirements.txt` będzie zawierał `crewai`, `fastapi`, `uvicorn`, `psycopg2-binary` (dla PostgreSQL) lub `sqlite3` (dla SQLite), biblioteki do RAG (np. `langchain`, `chromadb` jeśli używasz wbudowanej).



### 4.2. docker-compose.yml (dla lokalnego rozwoju)



YAML

```
version: '3.8'

services:
  app:
    build:
      context:.
      dockerfile: Dockerfile
      # Użyj buildx dla multi-arch, jeśli nie jest domyślnie skonfigurowany
      # platform: linux/arm64 # lub linux/amd64 w zależności od docelowej architektury
    ports:
      - "8000:8000"
    volumes:
      -.:/app # Montowanie kodu dla łatwego rozwoju
      - app_data:/app/data # Dla plików tymczasowych lub lokalnej bazy danych SQLite
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY} # Zmienna środowiskowa z pliku.env
      - CREW_AI_DB_URL=postgresql://user:password@db:5432/crewai_db
    depends_on:
      - db
      # - vector_db # Odkomentuj, jeśli używasz oddzielnej bazy wektorowej

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=crewai_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432" # Opcjonalne, do bezpośredniego dostępu do bazy danych

  # vector_db: # Odkomentuj, jeśli używasz oddzielnej bazy wektorowej (np. ChromaDB)
  #   image: chromadb/chroma:latest
  #   ports:
  #     - "8001:8000" # Domyślny port ChromaDB
  #   volumes:
  #     - vector_db_data:/chroma/data

volumes:
  app_data:
  db_data:
  # vector_db_data: # Odkomentuj, jeśli używasz oddzielnej bazy wektorowej
```



### 4.3. Plik `.env` (dla zmiennych środowiskowych)



Utwórz plik `.env` w tym samym katalogu co `docker-compose.yml`:

```
OPENAI_API_KEY="sk-your_actual_openai_api_key"
# Możesz dodać inne klucze API dla innych dostawców LLM
```



## 5. Uruchamianie





### Lokalnie (Mac z ARM64):



1. Upewnij się, że Docker Desktop jest zainstalowany i uruchomiony.
2. Przejdź do katalogu projektu w terminalu.
3. Uruchom `docker compose up --build`. Docker automatycznie zbuduje obraz dla architektury ARM64.



### Na Serwerze (Ubuntu z AMD64):



1. Zainstaluj Docker i Docker Compose na serwerze.
2. Przenieś pliki projektu (kod, Dockerfile, docker-compose.yml,.env) na serwer.
3. Przejdź do katalogu projektu w terminalu.
4. Uruchom `docker compose up --build`. Docker zbuduje obraz dla architektury AMD64.

Ta architektura zapewnia modularność, skalowalność i elastyczność, umożliwiając efektywne zarządzanie złożonym przepływem pracy AI Writing Flow, jednocześnie spełniając Twoje wymagania dotyczące konteneryzacji i wsparcia dla różnych architektur.