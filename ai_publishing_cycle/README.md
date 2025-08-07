# AI Publishing Cycle - Vector Wave Content Pipeline

This CrewAI Flow orchestrates the complete content publishing pipeline for Vector Wave, managing the sequential execution of content normalization followed by editorial review.

## 🎯 Overview

The AI Publishing Cycle Flow automates the entire content pipeline:

1. **Content Normalization** - Preprocesses raw content from various sources into standardized format
2. **Editorial Review** - AI Kolegium analyzes normalized content and makes editorial decisions
3. **Pipeline Reporting** - Generates comprehensive reports on the entire process

## 🏗️ Architecture

```
Raw Content → Normalization Crew → Normalized Content → AI Kolegium → Editorial Decisions
     ↓                                      ↓                               ↓
/content/raw                        /content/normalized              editorial_report.json
```

## 📁 Flow Structure

- **PublishingState**: Pydantic model tracking the entire pipeline state
- **AIPublishingFlow**: Main flow class with three sequential phases:
  - `normalize_content()` - Runs ContentNormalizerCrew
  - `editorial_review()` - Runs AiKolegiumRedakcyjne crew
  - `generate_pipeline_report()` - Creates final pipeline report

## 🚀 Running the Pipeline

### Prerequisites

1. Ensure you have the AI Kolegium Redakcyjne project set up
2. Place raw content in `/Users/hretheum/dev/bezrobocie/vector-wave/content/raw`
3. Install dependencies:

```bash
crewai install
```

### Execute the Flow

```bash
# From the ai_publishing_cycle directory
crewai run

# Or directly
python src/ai_publishing_cycle/main.py
```

### Visualize the Flow

```bash
crewai flow plot
```

## 📊 Output

The flow generates:

1. **Normalized Content** in `/content/normalized/`
   - Preprocessed files with standardized metadata
   - Content classification (SOURCE/DRAFT/SUGGESTION)
   
2. **Editorial Report** as `editorial_report.json`
   - Approved/rejected topics
   - Resource allocation
   - Performance predictions
   
3. **Pipeline Report** as `pipeline_report.json`
   - Complete execution summary
   - Metrics from both phases
   - Error tracking

## 🔧 Configuration

The flow uses crews from the AI Kolegium Redakcyjne project:

- **ContentNormalizerCrew**: 3 agents for content preprocessing
- **AiKolegiumRedakcyjne**: 5 agents for editorial decisions

Both crews are imported dynamically from the parent project.

## 📈 Monitoring

The flow provides real-time status updates:

- Phase transitions with timestamps
- Success/failure indicators
- Error messages and recovery status
- Final metrics summary

## 🛠️ Customization

To modify the pipeline:

1. Edit `PublishingState` to track additional data
2. Add new phases using `@listen` decorators
3. Integrate additional crews or tools
4. Customize report generation logic

## 🔍 Troubleshooting

Common issues:

- **Import errors**: Ensure the AI Kolegium Redakcyjne project is in the correct path
- **No content found**: Check raw content folder has .md files
- **Normalization fails**: Verify write permissions to normalized folder

## 📚 Related Documentation

- [CrewAI Flows Documentation](https://docs.crewai.com/en/guides/flows/first-flow)
- [AI Kolegium Redakcyjne README](../ai_kolegium_redakcyjne/README.md)
- [Vector Wave Styleguide](../../../styleguides/)