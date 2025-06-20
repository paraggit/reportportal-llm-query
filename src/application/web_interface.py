import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..utils.config import Config
from .response_generator import ResponseGenerator
from .session_manager import SessionManager

app = FastAPI(title="Report Portal LLM Query API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
config = Config.from_yaml("config/config.yaml")
response_generator = ResponseGenerator(config)
session_manager = SessionManager(config)


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    session_id: str
    metadata: Optional[dict] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Report Portal LLM Query Interface"}


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Process a single query."""
    try:
        # Create session if not provided
        session_id = request.session_id or session_manager.create_session()

        # Generate response
        response = await response_generator.generate_response(request.query, session_id=session_id)

        return QueryResponse(
            answer=response.answer, session_id=session_id, metadata=response.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for streaming responses."""
    await websocket.accept()

    try:
        while True:
            # Receive query from client
            data = await websocket.receive_json()
            query = data.get("query")

            if not query:
                await websocket.send_json({"error": "No query provided"})
                continue

            # Stream response
            async for chunk in response_generator.generate_streaming_response(query, session_id):
                await websocket.send_json({"type": "chunk", "content": chunk})

            # Send completion signal
            await websocket.send_json({"type": "complete"})

    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get query history for a session."""
    history = session_manager.get_session_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": history}


# Simple web UI
@app.get("/ui", response_class=HTMLResponse)
async def serve_ui():
    """Serve a simple web UI."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Report Portal LLM Query Interface</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            #chat-container {
                border: 1px solid #ddd;
                height: 400px;
                overflow-y: scroll;
                padding: 10px;
                margin-bottom: 10px;
            }
            .message { margin: 10px 0; }
            .user { color: blue; }
            .assistant { color: green; }
            #query-input { width: 70%; padding: 5px; }
            #send-button { padding: 5px 20px; }
        </style>
    </head>
    <body>
        <h1>Report Portal LLM Query Interface</h1>
        <div id="chat-container"></div>
        <input type="text" id="query-input" placeholder="Ask about test executions...">
        <button id="send-button">Send</button>

        <script>
            const chatContainer = document.getElementById('chat-container');
            const queryInput = document.getElementById('query-input');
            const sendButton = document.getElementById('send-button');

            let sessionId = null;

            async function sendQuery() {
                const query = queryInput.value.trim();
                if (!query) return;

                // Display user message
                addMessage(query, 'user');
                queryInput.value = '';

                try {
                    const response = await fetch('/query', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            query: query,
                            session_id: sessionId
                        })
                    });

                    const data = await response.json();
                    sessionId = data.session_id;
                    addMessage(data.answer, 'assistant');
                } catch (error) {
                    addMessage('Error: ' + error.message, 'assistant');
                }
            }

            function addMessage(text, type) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + type;
                messageDiv.textContent = type === 'user' ? 'You: ' + text : 'Assistant: ' + text;
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            sendButton.onclick = sendQuery;
            queryInput.onkeypress = (e) => {
                if (e.key === 'Enter') sendQuery();
            };
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
