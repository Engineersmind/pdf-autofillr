"""
FastAPI app entrypoint (no /chatbot prefix — bare routes).

Use this when you want to mount the chatbot app as a sub-application
or when running behind a reverse proxy that adds the prefix.

Routes:
    POST   /chat
    GET    /session/{user_id}/{session_id}
    GET    /session/{user_id}/{session_id}/fill-report
    DELETE /session/{user_id}/{session_id}
    GET    /health

Compared with api_server.py, this app uses /chat instead of /chatbot/chat.
The api_server.py is the recommended entrypoint for standalone deployment.
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Reuse the same client factory and models from api_server
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_server import (
    get_client,
    ChatRequest,
    ChatResponse,
    SessionDataResponse,
)
from src.chatbot.limits import RateLimitExceeded

logger = logging.getLogger(__name__)

app = FastAPI(
    title="chatbot App (bare routes)",
    description="chatbot with /chat instead of /chatbot/chat — for sub-app mounting.",
    version="0.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        client = get_client()
        pdf_path = req.pdf_path or os.getenv("chatbot_PDF_PATH", "")
        if pdf_path:
            client.create_session(req.user_id, req.session_id, pdf_path=pdf_path)
        response, complete, data = client.send_message(req.user_id, req.session_id, req.message)
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
        logger.exception("Error in /chat")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{user_id}/{session_id}", response_model=SessionDataResponse)
def get_session(user_id: str, session_id: str):
    data = get_client().get_session_data(user_id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or not complete.")
    return SessionDataResponse(user_id=user_id, session_id=session_id, data=data)


@app.get("/session/{user_id}/{session_id}/fill-report")
def get_fill_report(user_id: str, session_id: str, format: str = "json"):
    client = get_client()
    if format == "text":
        text = client.get_fill_report_text(user_id, session_id)
        if text is None:
            raise HTTPException(status_code=404, detail="Fill report not found.")
        return {"report": text}
    report = client.get_fill_report(user_id, session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Fill report not found.")
    return report


@app.delete("/session/{user_id}/{session_id}")
def delete_session(user_id: str, session_id: str):
    get_client().delete_session(user_id, session_id)
    return {"deleted": True}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "storage": os.getenv("chatbot_STORAGE", "local"),
        "pdf_filler": os.getenv("chatbot_PDF_FILLER", "none"),
    }
