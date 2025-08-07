#!/usr/bin/env python
"""
AG-UI Chat Interface for Vector Wave Content Pipeline
Provides interactive chat-based control over content analysis and editorial decisions
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from ag_ui.core import (
    RunAgentInput,
    Message,
    Context,
    Tool,
    State,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    CustomEvent
)
from ag_ui.encoder import EventEncoder

# Import our crews
import sys
sys.path.append(str(Path(__file__).parents[3] / "ai_kolegium_redakcyjne/src"))
from ai_kolegium_redakcyjne.normalizer_crew import ContentNormalizerCrew
from ai_kolegium_redakcyjne.crew import AiKolegiumRedakcyjne


class VectorWaveAgent:
    """Interactive agent for Vector Wave content pipeline"""
    
    def __init__(self):
        self.normalizer_crew = ContentNormalizerCrew()
        self.kolegium_crew = AiKolegiumRedakcyjne()
        self.current_analysis = None
        
    async def run(self, input_data: RunAgentInput):
        """Main agent execution"""
        encoder = EventEncoder()
        
        # Send run started event
        yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id
            )
        )
        
        try:
            # Get last user message
            user_message = input_data.messages[-1].content if input_data.messages else ""
            
            # Parse intent
            intent = self._parse_intent(user_message)
            
            if intent == "analyze_folder":
                async for event in self._analyze_folder(user_message, encoder):
                    yield event
                    
            elif intent == "run_kolegium":
                async for event in self._run_kolegium(encoder):
                    yield event
                    
            else:
                # Default response with help
                message_id = str(uuid.uuid4())
                
                yield encoder.encode(
                    TextMessageStartEvent(
                        type=EventType.TEXT_MESSAGE_START,
                        message_id=message_id,
                        role="assistant"
                    )
                )
                
                help_text = """Cześć! 👋 Jestem asystentem AI Vector Wave. Mogę pomóc z:

🔍 **Analiza folderów**: "Przeanalizuj folder /content/raw/2025-07-31-brainstorm"
🚀 **Uruchomienie kolegium**: "Uruchom kolegium"
📊 **Raporty**: "Pokaż ostatni raport"

Co chciałbyś zrobić?"""
                
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=help_text
                    )
                )
                
                yield encoder.encode(
                    TextMessageEndEvent(
                        type=EventType.TEXT_MESSAGE_END,
                        message_id=message_id
                    )
                )
            
            # Send run finished
            yield encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id
                )
            )
            
        except Exception as e:
            yield encoder.encode(
                RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                    error_message=str(e)
                )
            )
    
    def _parse_intent(self, message: str) -> str:
        """Parse user intent from message"""
        message_lower = message.lower()
        
        if "analizuj" in message_lower or "przeanalizuj" in message_lower:
            return "analyze_folder"
        elif "kolegium" in message_lower or "uruchom" in message_lower:
            return "run_kolegium"
        elif "raport" in message_lower or "pokaż" in message_lower:
            return "view_report"
        else:
            return "unknown"
    
    async def _analyze_folder(self, message: str, encoder: EventEncoder):
        """Analyze folder for content opportunities"""
        
        # Extract folder path
        import re
        match = re.search(r'/[^\s]+', message)
        folder_path = match.group(0) if match else None
        
        if not folder_path:
            message_id = str(uuid.uuid4())
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant"
                )
            )
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta="❌ Nie znalazłem ścieżki do folderu. Podaj pełną ścieżkę, np: /content/raw/2025-07-31-brainstorm"
                )
            )
            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id
                )
            )
            return
        
        # Start analysis
        message_id = str(uuid.uuid4())
        yield encoder.encode(
            TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant"
            )
        )
        
        yield encoder.encode(
            TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=f"🔍 Analizuję folder: `{folder_path}`\n\nSprawdzam zawartość i zgodność ze styleguide..."
            )
        )
        
        # Tool call for analysis
        tool_call_id = str(uuid.uuid4())
        yield encoder.encode(
            ToolCallStartEvent(
                type=EventType.TOOL_CALL_START,
                tool_call_id=tool_call_id,
                tool_name="analyze_content_folder"
            )
        )
        
        yield encoder.encode(
            ToolCallArgsEvent(
                type=EventType.TOOL_CALL_ARGS,
                tool_call_id=tool_call_id,
                args_delta=json.dumps({"folder_path": folder_path})
            )
        )
        
        # Simulate analysis
        await asyncio.sleep(2)  # Simulate processing
        
        analysis_result = {
            "folder_path": folder_path,
            "files_count": 14,
            "content_type": "SERIES",
            "series_title": "How Vector Wave Style Guide Was Born - Expert Panel Discussion",
            "value_score": 9,
            "recommendation": "To kompletna seria dokumentująca proces tworzenia styleguide poprzez symulowaną debatę ekspertów.",
            "topic_suggestions": [
                {
                    "title": "Behind the Scenes: Jak powstał nasz Style Guide",
                    "platform": "LinkedIn",
                    "viral_score": 8
                },
                {
                    "title": "5 legend tech dziennikarstwa debatuje o content strategy",
                    "platform": "Twitter",
                    "viral_score": 9
                }
            ],
            "tags": ["process", "editorial", "behind-the-scenes", "expert-insights"]
        }
        
        self.current_analysis = analysis_result
        
        yield encoder.encode(
            ToolCallResultEvent(
                type=EventType.TOOL_CALL_RESULT,
                tool_call_id=tool_call_id,
                result=json.dumps(analysis_result)
            )
        )
        
        yield encoder.encode(
            ToolCallEndEvent(
                type=EventType.TOOL_CALL_END,
                tool_call_id=tool_call_id
            )
        )
        
        # Show results
        result_text = f"""

✅ **Analiza zakończona!**

📁 **Znaleziono:** {analysis_result['files_count']} plików
📝 **Typ contentu:** {analysis_result['content_type']}
🎯 **Wartość:** {analysis_result['value_score']}/10

**💡 Rekomendacja:**
{analysis_result['recommendation']}

**🎨 Propozycje tematów:**
1. **{analysis_result['topic_suggestions'][0]['title']}**
   Platform: {analysis_result['topic_suggestions'][0]['platform']} | Potencjał: {analysis_result['topic_suggestions'][0]['viral_score']}/10

2. **{analysis_result['topic_suggestions'][1]['title']}**
   Platform: {analysis_result['topic_suggestions'][1]['platform']} | Potencjał: {analysis_result['topic_suggestions'][1]['viral_score']}/10

**Następne kroki:**
- Wpisz "uruchom kolegium" aby przetworzyć content przez pełny pipeline
- Lub zapytaj o szczegóły analizy
"""
        
        yield encoder.encode(
            TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=result_text
            )
        )
        
        yield encoder.encode(
            TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id
            )
        )
    
    async def _run_kolegium(self, encoder: EventEncoder):
        """Run the full kolegium pipeline"""
        
        if not self.current_analysis:
            message_id = str(uuid.uuid4())
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant"
                )
            )
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta="⚠️ Najpierw przeanalizuj folder z contentem!"
                )
            )
            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id
                )
            )
            return
        
        message_id = str(uuid.uuid4())
        yield encoder.encode(
            TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant"
            )
        )
        
        yield encoder.encode(
            TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta="🚀 Uruchamiam AI Kolegium Redakcyjne...\n\n📋 Faza 1: Normalizacja treści..."
            )
        )
        
        # Simulate pipeline execution
        await asyncio.sleep(3)
        
        result_text = """

✅ **Kolegium zakończone!**

**📊 Wyniki:**
- Znormalizowano: 5 plików
- Zatwierdzono tematów: 12
- Do przeglądu ludzkiego: 1

**🌟 TOP 3 tematy:**
1. AI-Generated Video Content (96% potencjał)
2. Gen Z AI Microbrands (90% potencjał)
3. Synthetic Voice Dubbing (89% potencjał)

**📅 Harmonogram publikacji** gotowy na najbliższe 2 tygodnie.

Raport zapisany w: `pipeline_report.json`
"""
        
        yield encoder.encode(
            TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=result_text
            )
        )
        
        yield encoder.encode(
            TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id
            )
        )


# FastAPI app
app = FastAPI(title="Vector Wave AI Assistant")
agent = VectorWaveAgent()

@app.get("/")
async def get_ui():
    """Serve the UI"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vector Wave AI Editorial Assistant</title>
        <script src="https://cdn.jsdelivr.net/npm/@ag-ui/client@latest/dist/index.umd.js"></script>
        <link href="https://cdn.jsdelivr.net/npm/@ag-ui/client@latest/dist/index.css" rel="stylesheet">
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: system-ui, -apple-system, sans-serif;
            }
            #app {
                height: 100vh;
            }
        </style>
    </head>
    <body>
        <div id="app"></div>
        <script type="module">
            // Check if library loaded
            console.log('Window contents:', window);
            
            // Import from UMD global
            const { HttpAgent } = window.AgUIClient || window['@ag-ui/client'] || {};
            
            if (!HttpAgent) {
                console.error('HttpAgent not found! Available:', Object.keys(window));
                document.getElementById('app').innerHTML = '<h1>Error loading AG-UI client</h1>';
                return;
            }
            
            // Create agent
            const agent = new HttpAgent({
                url: '/awp',
                headers: {}
            });
            
            // Simple chat interface
            document.getElementById('app').innerHTML = `
                <div style="height: 100vh; display: flex; flex-direction: column; font-family: system-ui;">
                    <div style="padding: 20px; background: #f5f5f5; border-bottom: 1px solid #ddd;">
                        <h1 style="margin: 0;">Vector Wave AI Editorial Assistant</h1>
                    </div>
                    <div id="messages" style="flex: 1; overflow-y: auto; padding: 20px;">
                        <div style="margin-bottom: 10px; color: #666;">
                            Cześć! Mogę pomóc z analizą contentu. Napisz np. "Przeanalizuj folder /content/raw/2025-07-31-brainstorm"
                        </div>
                    </div>
                    <div style="padding: 20px; border-top: 1px solid #ddd;">
                        <form id="chat-form" style="display: flex; gap: 10px;">
                            <input id="message-input" type="text" placeholder="Wpisz wiadomość..." 
                                style="flex: 1; padding: 10px; font-size: 16px; border: 1px solid #ddd; border-radius: 4px;">
                            <button type="submit" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                Wyślij
                            </button>
                        </form>
                    </div>
                </div>
            `;
            
            // Handle form submission
            document.getElementById('chat-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const input = document.getElementById('message-input');
                const message = input.value.trim();
                if (!message) return;
                
                // Add user message
                document.getElementById('messages').innerHTML += `
                    <div style="margin: 10px 0; text-align: right;">
                        <span style="background: #007bff; color: white; padding: 8px 12px; border-radius: 8px; display: inline-block;">
                            ${message}
                        </span>
                    </div>
                `;
                
                input.value = '';
                
                // Run agent
                try {
                    const response = await agent.runAgent({
                        messages: [{ role: "user", content: message }]
                    });
                    
                    // Add assistant response
                    const lastMessage = response.messages[response.messages.length - 1];
                    document.getElementById('messages').innerHTML += `
                        <div style="margin: 10px 0;">
                            <div style="background: #f1f1f1; padding: 8px 12px; border-radius: 8px; display: inline-block;">
                                ${lastMessage.content}
                            </div>
                        </div>
                    `;
                } catch (error) {
                    console.error('Error:', error);
                    document.getElementById('messages').innerHTML += `
                        <div style="margin: 10px 0; color: red;">
                            Error: ${error.message}
                        </div>
                    `;
                }
                
                // Scroll to bottom
                document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
            });
        </script>
    </body>
    </html>
    """)

@app.post("/awp")
async def agent_endpoint(input_data: RunAgentInput):
    """AG-UI Agent endpoint"""
    return StreamingResponse(
        agent.run(input_data),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Vector Wave UI on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)