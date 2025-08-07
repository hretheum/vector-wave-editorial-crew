#!/usr/bin/env python
"""
CopilotKit Integration Server for Vector Wave CrewAI
Exposes our crews as CopilotKit actions
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from copilotkit.langchain import copilotkit_customize_config
from copilotkit.langchain import copilotkit_exit
from typing import Dict, Any
import sys
from pathlib import Path

# Add our modules to path
sys.path.append(str(Path(__file__).parents[3] / "ai_kolegium_redakcyjne/src"))
from ai_kolegium_redakcyjne.normalizer_crew import ContentNormalizerCrew
from ai_kolegium_redakcyjne.crew import AiKolegiumRedakcyjne

app = FastAPI()

@app.post("/copilotkit")
async def copilotkit_endpoint(request: Request):
    """Handle CopilotKit action requests"""
    data = await request.json()
    
    actions = [
        {
            "name": "analyze_content_folder",
            "description": "Analyze a content folder for editorial opportunities",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Path to the content folder"
                    }
                },
                "required": ["folder_path"]
            }
        },
        {
            "name": "run_editorial_pipeline",
            "description": "Run the complete editorial pipeline (normalization + kolegium)",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_path": {
                        "type": "string",
                        "description": "Path to raw content"
                    }
                },
                "required": ["content_path"]
            }
        }
    ]
    
    # If requesting available actions
    if data.get("type") == "actions":
        return JSONResponse({"actions": actions})
    
    # Handle action execution
    if data.get("type") == "execute":
        action_name = data.get("action")
        params = data.get("parameters", {})
        
        if action_name == "analyze_content_folder":
            # Run normalizer crew
            normalizer = ContentNormalizerCrew()
            result = normalizer.crew().kickoff({
                "content_directory": params["folder_path"]
            })
            
            return JSONResponse({
                "result": {
                    "analysis": str(result),
                    "status": "completed"
                }
            })
            
        elif action_name == "run_editorial_pipeline":
            # Run full pipeline
            normalizer = ContentNormalizerCrew()
            kolegium = AiKolegiumRedakcyjne()
            
            # First normalize
            norm_result = normalizer.crew().kickoff({
                "content_directory": params["content_path"]
            })
            
            # Then run kolegium
            kolegium_result = kolegium.crew().kickoff({
                "normalized_content_dir": "/content/normalized",
                "current_date": "2025-08-01"
            })
            
            return JSONResponse({
                "result": {
                    "normalization": str(norm_result),
                    "editorial": str(kolegium_result),
                    "status": "completed"
                }
            })
    
    return JSONResponse({"error": "Unknown request type"})

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CopilotKit CrewAI server on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)