# AI Writing Flow - Diagram przepływu

## Podział odpowiedzialności między systemami

### Kolegium Redakcyjne (już zaimplementowane)
Odpowiada za wstępną analizę i selekcję tematów:

- **Topic Discovery** - odkrywanie trendów i tematów
- **Viral Analysis** - analiza potencjału wiralnego (viral score)
- **Content Type Detection** - STANDALONE vs SERIES
- **Ownership Analysis** - ORIGINAL vs EXTERNAL
- **Editorial Decision** - wstępna decyzja redakcyjna
- **Quality Assessment** - ocena jakości contentu

### AI Writing Flow (do implementacji)
Odpowiada za generowanie gotowych do publikacji materiałów:

```mermaid
graph TD
    A[Topic Selection<br/><i>Kolegium Redakcyjne</i>] --> B{Content Type?}
    
    subgraph "AI Writing Flow"
        B -->|EXTERNAL| C[Deep Content Research<br/><i>Research Agent</i>]
        B -->|ORIGINAL<br/>or UI override| D[Audience Alignment<br/><i>Audience Mapper</i>]
        C --> D
        D --> E[Draft Generation<br/><i>Content Writer</i>]
        E --> P{Human Review<br/><i>UI Integration</i>}
        P -->|Minor Edits| F[Style Guide Validation<br/><i>Style Validator</i>]
        P -->|Content Changes| D
        P -->|Direction Change| C
        F --> G{Quality Check<br/><i>Quality Controller</i>}
        G -->|Fail| I[Revision Loop]
        I --> E
    end
    
    G -->|Pass| H
    
    subgraph "AI Distribution Flow"
        H[Platform Adaptation<br/><i>Platform Optimizer</i>]
        H --> J[Final Polish<br/><i>Quality Controller</i>]
        J --> K[Publication Package]
        K --> L{Publishing Decision}
        L -->|Immediate| M[Publish Now<br/><i>Publishing Agent</i>]
        L -->|Scheduled| N[Schedule Publication<br/><i>Scheduling Agent</i>]
        M --> O[Track Performance<br/><i>Analytics Agent</i>]
        N --> O
    end
    
    style A fill:#424242,color:#fff
    style B fill:#ff9800,color:#fff
    style C fill:#1976d2,color:#fff
    style D fill:#388e3c,color:#fff
    style E fill:#f57c00,color:#fff
    style F fill:#c2185b,color:#fff
    style G fill:#7b1fa2,color:#fff
    style H fill:#00796b,color:#fff
    style J fill:#7b1fa2,color:#fff
    style K fill:#616161,color:#fff
    style L fill:#ff9800,color:#fff
    style M fill:#d32f2f,color:#fff
    style N fill:#1976d2,color:#fff
    style O fill:#388e3c,color:#fff
    style P fill:#ff5722,color:#fff
```

### Przepływ danych między systemami

**Kolegium przekazuje do Writing Flow:**
- `topic_title` - wybrany temat
- `viral_score` - potencjał wiralny
- `content_type` - typ contentu (STANDALONE/SERIES)
- `folder_path` - ścieżka do źródeł
- `content_ownership` - własność contentu (ORIGINAL/EXTERNAL)
- `editorial_recommendations` - rekomendacje redakcyjne

**Opcje UI:**
- Checkbox: "Pomiń research dla contentu własnego" - pozwala ręcznie pominąć Deep Content Research nawet dla contentu EXTERNAL

**Writing Flow zwraca:**
- `final_draft` - gotowy artykuł
- `platform_variants` - wersje dla różnych platform
- `publication_metadata` - metadane do publikacji
- `quality_score` - finalna ocena jakościjak 