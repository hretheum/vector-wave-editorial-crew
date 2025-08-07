#!/usr/bin/env python
"""
Simple test UI for Vector Wave - sprawdzamy czy w ogóle działa
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
async def get_ui():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vector Wave Test</title>
        <style>
            body {
                font-family: system-ui;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            #chat {
                border: 1px solid #ccc;
                height: 400px;
                overflow-y: auto;
                padding: 10px;
                margin-bottom: 10px;
                background: #f5f5f5;
            }
            #input-area {
                display: flex;
                gap: 10px;
            }
            #message-input {
                flex: 1;
                padding: 10px;
                font-size: 16px;
            }
            button {
                padding: 10px 20px;
                background: #007bff;
                color: white;
                border: none;
                cursor: pointer;
            }
            .message {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }
            .user {
                background: #e3f2fd;
                text-align: right;
            }
            .assistant {
                background: white;
            }
        </style>
    </head>
    <body>
        <h1>Vector Wave AI Assistant - Test</h1>
        <div id="chat">
            <div class="message assistant">Cześć! Jestem asystentem Vector Wave. Napisz coś!</div>
        </div>
        <div id="input-area">
            <input type="text" id="message-input" placeholder="Wpisz wiadomość..." />
            <button onclick="sendMessage()">Wyślij</button>
        </div>
        
        <script>
            const chat = document.getElementById('chat');
            const input = document.getElementById('message-input');
            
            async function sendMessage() {
                const message = input.value.trim();
                if (!message) return;
                
                // Add user message
                chat.innerHTML += `<div class="message user">${message}</div>`;
                input.value = '';
                
                // Add assistant response
                chat.innerHTML += `<div class="message assistant">Otrzymałem: "${message}"</div>`;
                
                // Auto scroll
                chat.scrollTop = chat.scrollHeight;
            }
            
            // Enter key support
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
            
            console.log('UI loaded successfully!');
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)