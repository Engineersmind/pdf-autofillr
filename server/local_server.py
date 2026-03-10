# server/local_server.py
"""
FastAPI reference server for local development.

Run with (from the project root):
    uvicorn server.local_server:app --reload --port 8000

Then test with:
    curl -X POST http://localhost:8000/chat \
      -H 'Content-Type: application/json' \
      -d '{"user_id": "test_user", "session_id": "test_session", "message": ""}'
"""
from __future__ import annotations

import os
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:
    raise ImportError("FastAPI required: pip install chatbot-sdk[server]")

from chatbot import chatbotClient, LocalStorage, FormConfig
from chatbot.limits import RateLimitExceeded

app = FastAPI(title="chatbot SDK — Local Development Server", version="0.1.0")

# ── Init client ───────────────────────────────────────────────────────

_client: Optional[chatbotClient] = None


def get_client() -> chatbotClient:
    global _client
    if _client is None:
        data_path = os.getenv("chatbot_DATA_PATH", "./chatbot_data")
        config_path = os.getenv("chatbot_CONFIG_PATH", "./configs")
        _client = chatbotClient(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            storage=LocalStorage(data_path=data_path, config_path=config_path),
            form_config=FormConfig.from_directory(config_path),
            pdf_filler=None,
        )
    return _client


# ── Request / response models ─────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str = ""
    pdf_path: Optional[str] = None


class ChatResponse(BaseModel):
    user_id: str
    session_id: str
    response: str
    session_complete: bool
    filled_data: Optional[dict] = None


# ── Endpoints ─────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Process one chat message."""
    try:
        client = get_client()

        # Create session with PDF path if provided
        if req.pdf_path:
            client.create_session(req.user_id, req.session_id, pdf_path=req.pdf_path)

        response, complete, data = client.send_message(
            user_id=req.user_id,
            session_id=req.session_id,
            message=req.message,
        )

        return ChatResponse(
            user_id=req.user_id,
            session_id=req.session_id,
            response=response,
            session_complete=complete,
            filled_data=data if complete else None,
        )

    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.get("/session/{user_id}/{session_id}")
def get_session(user_id: str, session_id: str):
    """Get filled data for a completed session."""
    client = get_client()
    data = client.get_session_data(user_id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or not complete")
    return {"user_id": user_id, "session_id": session_id, "data": data}


@app.delete("/session/{user_id}/{session_id}")
def delete_session(user_id: str, session_id: str):
    """Delete all data for a session."""
    client = get_client()
    client.delete_session(user_id, session_id)
    return {"deleted": True}


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}