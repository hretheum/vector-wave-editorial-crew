Na podstawie dogłębnej analizy dostarczonych materiałów, **rekomenduję całkowite przepisanie aplikacji od nowa.**

Obecny stan projektu cechuje fundamentalny konflikt architektoniczny (dwie konkurencyjne implementacje przepływu) oraz brak kluczowych, nieliniowych funkcji, takich jak routing czy pętle rewizji. Próba refaktoryzacji obecnego, liniowego kodu w celu dopasowania go do docelowej, warunkowej architektury byłaby bardziej skomplikowana i ryzykowna niż stworzenie nowej, czystej implementacji od podstaw. Takie podejście pozwoli od razu zaimplementować najlepsze praktyki i uniknąć kompromisów technicznych.

Poniżej przedstawiam szczegółowy plan przejścia od stanu obecnego do rekomendowanego, opartego na architekturze CrewAI `Flow` i `Crews`.

------



## 🗺️ Plan Transformacji: Od "As-Is" do Architektury Docelowej



Plan podzielony jest na cztery główne fazy, które zapewnią uporządkowane i iteracyjne wdrożenie nowej architektury.



### Faza 1: Fundament - Core Flow i Routing



Celem tej fazy jest stworzenie szkieletu nowej aplikacji, implementując kluczową logikę biznesową opisaną w diagramie.

1. **Stworzenie `MasterWritingFlow`:**
   - Utwórz nowy plik, np. `master_writing_flow.py`, który będzie zawierał główną klasę przepływu.
   - Zdefiniuj w nim logikę startową (`@start`), która będzie odpowiedzialna za analizę typu treści (Content Type Decision).
   - Wykorzystaj dekorator **`@router`** do zaimplementowania kluczowego rozgałęzienia:
     - Jeśli `content_ownership` to **`EXTERNAL`**, skieruj przepływ do zadania `deep_research`.
     - Jeśli `content_ownership` to **`ORIGINAL`**, skieruj przepływ bezpośrednio do `audience_alignment`, **pomijając research**.
2. **Integracja Istniejących Agentów:**
   - Podłącz istniejących, dobrze zaimplementowanych agentów (`ResearchAgent`, `ContentAnalysisAgent`, `WriterAgent`) do nowego `MasterWritingFlow`.
   - Upewnij się, że agenci są wywoływani w odpowiednich krokach zdefiniowanych przez logikę `@router` i `@listen`.
3. **Usunięcie Konfliktu Architektonicznego:**
   - Całkowicie usuń przestarzały `linear_flow.py` oraz jego `LinearDraftExecutor`.
   - Zaktualizuj `copilot_backend.py`, aby importował i używał wyłącznie nowego `MasterWritingFlow`. Pozwoli to na ujednolicenie architektury.

------



------



### Faza 3: Uruchomienie Aplikacji i Frontend



W tej fazie skupimy się na architekturze systemowej, konteneryzacji i budowie interfejsu użytkownika.

1. **Konteneryzacja Usług (Docker):**
   - Zgodnie z dokumentem `Architektura Aplikacji AI Writing Flow.md`, przygotuj pliki `Dockerfile` dla poszczególnych serwisów.
   - Stwórz plik `docker-compose.yml`, który zorkiestruje uruchomienie:
     - **Core Application Service**: Aplikacja z `MasterWritingFlow`.
     - **Database Service**: Baza danych (np. PostgreSQL) do przechowywania stanu przepływów i treści.
     - **File Storage**: Wolumen do przechowywania plików.
2. **integracja z frontendem odpowiednio** — użyj dotychczasowego frontu wraz z edytorem jako implementacji  Człowieka w Pętli (Human-in-the-Loop)
   1. Implementacja `Human Review Checkpoint`:**
      - W `MasterWritingFlow`, po kroku generowania draftu (`Draft Generation`), dodaj zadanie (`@listen`), które będzie pauzować przepływ i czekać na decyzję człowieka.
      - Stwórz w `copilot_backend.py` nowy endpoint API (np. `/human_review_feedback`), który będzie przyjmował decyzję z frontendu.
   2. **Routing Decyzji z Human Review:**
      - Użyj kolejnego dekoratora `@router` do obsługi trzech możliwych ścieżek po recenzji:
        - **Minor Edits**: Przekieruj do walidacji stylu (`Style Guide Validation`).
        - **Content Changes**: Wróć do etapu generowania draftu (`Draft Generation`), tworząc pętlę.
        - **Direction Change**: Wróć na sam początek, do decyzji o typie treści (`Content Type Decision`), umożliwiając pełny restart.
   3. **Implementacja `Revision Loop` po Kontroli Jakości:**
      - Po kroku kontroli jakości (`Quality Check`), dodaj logikę warunkową (`@router`):
        - Jeśli jakość **przeszła** (`Pass`), zakończ przepływ sukcesem.
        - Jeśli jakość **nie przeszła** (`Fail`), zaimplementuj pętlę rewizji, wracając do `Human Review` lub innego zdefiniowanego etapu.

------



### Faza 4: Zaawansowane Funkcje i Optymalizacja



Po uruchomieniu rdzenia aplikacji, można ją rozbudować o dodatkowe, zaawansowane możliwości.

1. **Wdrożenie Vector Database dla Style Guide:**

   - Aby agenci mogli dynamicznie korzystać z przewodnika stylu, zaimplementuj go jako narzędzie RAG (Retrieval-Augmented Generation).
   - Zintegruj bazę wektorową (np. ChromaDB) z agentami odpowiedzialnymi za styl i jakość.

2. **Monitoring i Persystencja:**

   - Wdrożenie i rozbudowa istniejących mechanizmów logowania, monitoringu i persystencji stanu, aby zapewnić stabilność i audytowalność działania aplikacji w środowisku produkcyjnym.

     