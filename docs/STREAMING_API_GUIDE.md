# Streaming API Guide - Batch Analysis with Progress

## Overview
The `/api/analyze-custom-ideas-stream` endpoint provides real-time progress updates while analyzing multiple content ideas using Server-Sent Events (SSE).

## Endpoint Details

### URL
```
POST /api/analyze-custom-ideas-stream
```

### Request Body
```json
{
  "folder": "folder-name",
  "ideas": ["idea 1", "idea 2", "idea 3"],
  "platform": "LinkedIn"
}
```

### Response Format
Server-Sent Events stream with the following event types:

## Event Types

### 1. Start Event
```json
{
  "type": "start",
  "total_ideas": 3,
  "folder": "folder-name",
  "platform": "LinkedIn",
  "timestamp": "2025-08-06T08:14:29.841611"
}
```

### 2. Progress Event
```json
{
  "type": "progress",
  "current": 1,
  "total": 3,
  "percentage": 33,
  "analyzing": "Current idea being analyzed",
  "timestamp": "2025-08-06T08:14:29.841886"
}
```

### 3. Result Event
```json
{
  "type": "result",
  "idea_index": 0,
  "idea": "Original idea text",
  "analysis": {
    "idea": "Original idea text",
    "viral_score": 0.7,
    "content_alignment": 0.5,
    "available_material": 0.6,
    "overall_score": 0.61,
    "recommendation": "Improvement suggestions",
    "suggested_angle": "Alternative approach"
  },
  "timestamp": "2025-08-06T08:14:43.250849"
}
```

### 4. Error Event
```json
{
  "type": "error",
  "idea_index": 1,
  "idea": "Failed idea",
  "error": "Error message",
  "timestamp": "2025-08-06T08:14:43.250849"
}
```

### 5. Complete Event
```json
{
  "type": "complete",
  "total_analyzed": 3,
  "best_idea": {
    "idea": "Best scoring idea",
    "viral_score": 0.8,
    "content_alignment": 0.9,
    "available_material": 0.7,
    "overall_score": 0.81,
    "recommendation": "This idea has strong potential",
    "suggested_angle": null
  },
  "folder_context": {
    "total_files": 5,
    "main_topics": ["tech", "AI"],
    "content_type": "article",
    "technical_depth": "high"
  },
  "timestamp": "2025-08-06T08:14:55.609785"
}
```

### 6. Cached Result Event
When results are served from cache:
```json
{
  "type": "cached_result",
  "data": {
    "folder": "folder-name",
    "platform": "LinkedIn",
    "ideas": [...],
    "best_idea": {...},
    "folder_context": {...},
    "from_cache": true
  },
  "timestamp": "2025-08-06T08:14:55.609785"
}
```

## Testing with curl

### Basic Test
```bash
curl -N -X POST http://localhost:8003/api/analyze-custom-ideas-stream \
  -H "Content-Type: application/json" \
  -d '{
    "folder": "2025-08-05-hybrid-rag-crewai",
    "ideas": ["Idea 1", "Idea 2"],
    "platform": "LinkedIn"
  }'
```

### Options explained:
- `-N` or `--no-buffer`: Disable output buffering for real-time streaming
- `-X POST`: HTTP method
- `-H`: Headers

## Frontend Integration Example

### JavaScript EventSource
```javascript
async function analyzeIdeasWithProgress(folder, ideas, platform) {
  const response = await fetch('/api/analyze-custom-ideas-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder, ideas, platform })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.substring(6));
        handleSSEEvent(data);
      }
    }
  }
}

function handleSSEEvent(data) {
  switch (data.type) {
    case 'start':
      initProgressBar(data.total_ideas);
      break;
    
    case 'progress':
      updateProgressBar(data.percentage, data.analyzing);
      break;
    
    case 'result':
      addResultToUI(data.analysis);
      break;
    
    case 'error':
      showError(data.idea, data.error);
      break;
    
    case 'complete':
      showSummary(data.best_idea, data.folder_context);
      hideProgressBar();
      break;
    
    case 'cached_result':
      showCachedResults(data.data);
      break;
  }
}
```

### React Hook Example
```typescript
import { useState, useCallback } from 'react';

interface IdeaAnalysis {
  idea: string;
  viral_score: number;
  content_alignment: number;
  available_material: number;
  overall_score: number;
  recommendation: string;
  suggested_angle?: string;
}

interface ProgressState {
  isAnalyzing: boolean;
  currentIdea: string;
  percentage: number;
  results: IdeaAnalysis[];
  bestIdea?: IdeaAnalysis;
  error?: string;
}

export function useStreamingAnalysis() {
  const [progress, setProgress] = useState<ProgressState>({
    isAnalyzing: false,
    currentIdea: '',
    percentage: 0,
    results: []
  });

  const analyzeIdeas = useCallback(async (
    folder: string,
    ideas: string[],
    platform: string
  ) => {
    setProgress({
      isAnalyzing: true,
      currentIdea: '',
      percentage: 0,
      results: []
    });

    try {
      const response = await fetch('/api/analyze-custom-ideas-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder, ideas, platform })
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6));
            
            switch (data.type) {
              case 'progress':
                setProgress(prev => ({
                  ...prev,
                  currentIdea: data.analyzing,
                  percentage: data.percentage
                }));
                break;
              
              case 'result':
                setProgress(prev => ({
                  ...prev,
                  results: [...prev.results, data.analysis]
                }));
                break;
              
              case 'complete':
                setProgress(prev => ({
                  ...prev,
                  isAnalyzing: false,
                  bestIdea: data.best_idea,
                  percentage: 100
                }));
                break;
              
              case 'error':
                setProgress(prev => ({
                  ...prev,
                  error: data.error
                }));
                break;
            }
          }
        }
      }
    } catch (error) {
      setProgress(prev => ({
        ...prev,
        isAnalyzing: false,
        error: error.message
      }));
    }
  }, []);

  return { progress, analyzeIdeas };
}
```

## Performance Considerations

1. **Caching**: Results are cached for 5 minutes. Cached results are returned immediately via single `cached_result` event.

2. **Delays**: Small 100ms delay between idea analyses to prevent client overwhelm.

3. **Error Handling**: Individual idea failures don't stop the entire batch. Errors are reported per-idea.

4. **Headers**: 
   - `Cache-Control: no-cache` - Prevents proxy caching
   - `X-Accel-Buffering: no` - Disables nginx buffering for real-time streaming

## Benefits

1. **Real-time Feedback**: Users see progress as ideas are analyzed
2. **Partial Results**: Results stream as available, no waiting for entire batch
3. **Better UX**: Progress bar shows exact status
4. **Error Resilience**: Failed ideas don't block other analyses
5. **Cache Integration**: Fast response for repeated queries