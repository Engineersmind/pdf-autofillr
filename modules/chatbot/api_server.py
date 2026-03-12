"""
FastAPI server for the chatbot module.

Run with:
    python api_server.py

Or directly with uvicorn:
    uvicorn api_server:app --reload --port 8001

API docs available at:
    http://localhost:8001/docs
    http://localhost:8001/redoc

PDF filler mode (set in .env):
    chatbot_PDF_FILLER=none      ← data-only (default)
    chatbot_PDF_FILLER=mapper    ← connect to mapper module on MAPPER_API_URL
    chatbot_PDF_FILLER=managed   ← private Auth0+Lambda filler
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    raise ImportError(
        "FastAPI is required to run the API server.\n"
        "Install it with:  pip install -r requirements-api.txt"
    )

from src.chatbot import chatbotClient, LocalStorage, S3Storage, FormConfig
from src.chatbot.limits import RateLimitExceeded

logger = logging.getLogger(__name__)


# ============================================================================
# App
# ============================================================================

app = FastAPI(
    title="chatbot Onboarding API",
    description=(
        "Conversational investor onboarding chatbot — "
        "collects investor data through natural language and fills PDF forms."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Client singleton
# ============================================================================

_client: Optional[chatbotClient] = None


def _build_pdf_filler():
    """Return the correct PDFFillerInterface from chatbot_PDF_FILLER env."""
    mode = os.getenv("chatbot_PDF_FILLER", "none").lower()

    if mode == "none":
        return None

    if mode == "mapper":
        from src.chatbot.pdf.mapper_filler import MapperPDFFiller
        return MapperPDFFiller(
            mapper_api_url=os.getenv("MAPPER_API_URL", "http://localhost:8000"),
            mapper_api_key=os.getenv("MAPPER_API_KEY", ""),
        )

    if mode == "managed":
        try:
            from chatbot_managed.filler import chatbotManagedPDFFiller
        except ImportError:
            raise ImportError(
                "chatbot_PDF_FILLER=managed requires the private chatbot-managed package.\n"
                "Install it: pip install git+https://github.com/yourorg/chatbot-managed.git"
            )
        return chatbotManagedPDFFiller(
            auth0_domain=os.environ["AUTH0_DOMAIN"],
            auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
            auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
            auth0_audience=os.environ["AUTH0_AUDIENCE"],
            pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
            pdf_api_key=os.environ["PDF_API_KEY"],
            backend_url=os.getenv("BACKEND_URL", ""),
            auth_token=os.getenv("AUTH_TOKEN", ""),
        )

    raise ValueError(
        f"Unknown chatbot_PDF_FILLER value: {mode!r}. "
        "Accepted values: none | mapper | managed"
    )


def _build_storage():
    storage_type = os.getenv("chatbot_STORAGE", "local").lower()
    if storage_type == "s3":
        return S3Storage(
            output_bucket=os.environ["AWS_OUTPUT_BUCKET"],
            config_bucket=os.environ["AWS_CONFIG_BUCKET"],
            region=os.getenv("AWS_REGION", "us-east-1"),
        )
    return LocalStorage(
        data_path=os.getenv("chatbot_DATA_PATH", "./chatbot_data"),
        config_path=os.getenv("chatbot_CONFIG_PATH", "./config_samples"),
    )


def get_client() -> chatbotClient:
    global _client
    if _client is None:
        storage = _build_storage()
        config_path = os.getenv("chatbot_CONFIG_PATH", "./config_samples")
        _client = chatbotClient(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            storage=storage,
            form_config=FormConfig.from_directory(config_path),
            pdf_filler=_build_pdf_filler(),
        )
    return _client


# ============================================================================
# Request / Response models
# ============================================================================

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the investor")
    session_id: str = Field(..., description="Unique identifier for this conversation session")
    message: str = Field(default="", description="User's message text")
    pdf_path: Optional[str] = Field(
        default=None,
        description=(
            "Path to the blank PDF to fill. Overrides chatbot_PDF_PATH env var. "
            "Only needed on the first message of a session."
        ),
    )


class ChatResponse(BaseModel):
    user_id: str
    session_id: str
    response: str
    session_complete: bool
    filled_data: Optional[dict] = None


class SessionDataResponse(BaseModel):
    user_id: str
    session_id: str
    data: Optional[dict]


class FillReportResponse(BaseModel):
    user_id: str
    session_id: str
    report: dict


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
def root():
    """API info."""
    return {
        "name": "chatbot Onboarding API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "chat":        "POST /chatbot/chat",
            "session":     "GET  /chatbot/session/{user_id}/{session_id}",
            "fill_report": "GET  /chatbot/session/{user_id}/{session_id}/fill-report",
            "delete":      "DELETE /chatbot/session/{user_id}/{session_id}",
            "health":      "GET  /health",
            "docs":        "GET  /docs",
        },
    }


@app.post("/chatbot/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Process one conversational message turn.

    On session creation pass ``pdf_path`` to associate a blank PDF.
    On subsequent turns ``pdf_path`` can be omitted.
    """
    try:
        client = get_client()

        # Associate PDF path if provided (idempotent — safe to call on every turn)
        pdf_path = req.pdf_path or os.getenv("chatbot_PDF_PATH", "")
        if pdf_path:
            client.create_session(req.user_id, req.session_id, pdf_path=pdf_path)

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
        logger.exception("Unhandled error in /chatbot/chat")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.get("/chatbot/session/{user_id}/{session_id}", response_model=SessionDataResponse)
def get_session(user_id: str, session_id: str):
    """Return the filled data dict for a completed session."""
    client = get_client()
    data = client.get_session_data(user_id, session_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or not yet complete.",
        )
    return SessionDataResponse(user_id=user_id, session_id=session_id, data=data)


@app.get("/chatbot/session/{user_id}/{session_id}/fill-report")
def get_fill_report(user_id: str, session_id: str, format: str = "json"):
    """
    Return the fill statistics report for a completed session.

    Query params:
        format=json  (default) — full report dict
        format=text            — human-readable text summary
    """
    client = get_client()
    if format == "text":
        text = client.get_fill_report_text(user_id, session_id)
        if text is None:
            raise HTTPException(status_code=404, detail="Fill report not found.")
        return {"user_id": user_id, "session_id": session_id, "report": text}

    report = client.get_fill_report(user_id, session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Fill report not found.")
    return FillReportResponse(user_id=user_id, session_id=session_id, report=report)


@app.delete("/chatbot/session/{user_id}/{session_id}")
def delete_session(user_id: str, session_id: str):
    """Delete all data for a session."""
    client = get_client()
    client.delete_session(user_id, session_id)
    return {"deleted": True, "user_id": user_id, "session_id": session_id}


@app.get("/health")
def health():
    """Health check — returns storage and PDF filler mode."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "storage": os.getenv("chatbot_STORAGE", "local"),
        "pdf_filler": os.getenv("chatbot_PDF_FILLER", "none"),
    }


# ============================================================================
# Error handler
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    log_level = os.getenv("chatbot_LOG_LEVEL", "info").lower()
    port = int(os.getenv("PORT", "8001"))

    logger.info("Starting chatbot API server...")
    logger.info(f"Server: http://localhost:{port}")
    logger.info(f"Docs:   http://localhost:{port}/docs")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level=log_level)
