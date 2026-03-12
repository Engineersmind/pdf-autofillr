"""
FastAPI app for pdf-autofillr-chatbot.

Standalone:  chatbot-server
Mount in your app:
    from chatbot.entrypoints.fastapi_app import app as chatbot_app
    main_app.mount("/onboarding", chatbot_app)
"""
from __future__ import annotations
import os, logging
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from chatbot import chatbotClient, LocalStorage, S3Storage, FormConfig
from chatbot.limits import RateLimitExceeded

logger = logging.getLogger(__name__)

app = FastAPI(
    title="pdf-autofillr-chatbot API",
    description="Conversational investor onboarding — collects data and fills PDF forms.",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Client singleton ──────────────────────────────────────────────────────────

_client: Optional[chatbotClient] = None


def _build_pdf_filler():
    mode = os.getenv("chatbot_PDF_FILLER", "none").lower()
    if mode == "none":
        return None
    if mode == "mapper":
        from chatbot.pdf.mapper_filler import MapperPDFFiller
        return MapperPDFFiller(
            mapper_api_url=os.getenv("MAPPER_API_URL", "http://localhost:8000"),
            mapper_api_key=os.getenv("MAPPER_API_KEY", ""),
        )
    if mode == "managed":
        try:
            from chatbot_managed.filler import chatbotManagedPDFFiller
        except ImportError:
            raise ImportError("chatbot_PDF_FILLER=managed requires the chatbot-managed package.")
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
    raise ValueError(f"Unknown chatbot_PDF_FILLER: {mode!r}. Use: none | mapper | managed")


def get_client() -> chatbotClient:
    global _client
    if _client is None:
        if os.getenv("chatbot_STORAGE", "local").lower() == "s3":
            storage = S3Storage(
                output_bucket=os.environ["AWS_OUTPUT_BUCKET"],
                config_bucket=os.environ["AWS_CONFIG_BUCKET"],
                region=os.getenv("AWS_REGION", "us-east-1"),
            )
        else:
            storage = LocalStorage(
                data_path=os.getenv("chatbot_DATA_PATH", "./chatbot_data"),
                config_path=os.getenv("chatbot_CONFIG_PATH", "./configs"),
            )
        _client = chatbotClient(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            storage=storage,
            form_config=FormConfig.from_directory(os.getenv("chatbot_CONFIG_PATH", "./configs")),
            pdf_filler=_build_pdf_filler(),
        )
    return _client


# ── Models ────────────────────────────────────────────────────────────────────

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


class SessionDataResponse(BaseModel):
    user_id: str
    session_id: str
    data: Optional[dict]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "pdf-autofillr-chatbot", "version": "0.1.0", "docs": "/docs"}


@app.post("/chatbot/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        client = get_client()
        pdf_path = req.pdf_path or os.getenv("chatbot_PDF_PATH", "")
        if pdf_path:
            client.create_session(req.user_id, req.session_id, pdf_path=pdf_path)
        response, complete, data = client.send_message(req.user_id, req.session_id, req.message)
        return ChatResponse(user_id=req.user_id, session_id=req.session_id,
                            response=response, session_complete=complete,
                            filled_data=data if complete else None)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error in /chatbot/chat")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chatbot/session/{user_id}/{session_id}", response_model=SessionDataResponse)
def get_session(user_id: str, session_id: str):
    data = get_client().get_session_data(user_id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or not complete.")
    return SessionDataResponse(user_id=user_id, session_id=session_id, data=data)


@app.get("/chatbot/session/{user_id}/{session_id}/fill-report")
def get_fill_report(user_id: str, session_id: str, format: str = "json"):
    client = get_client()
    if format == "text":
        text = client.get_fill_report_text(user_id, session_id)
        if text is None:
            raise HTTPException(status_code=404, detail="Fill report not found.")
        return {"user_id": user_id, "session_id": session_id, "report": text}
    report = client.get_fill_report(user_id, session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Fill report not found.")
    return {"user_id": user_id, "session_id": session_id, "report": report}


@app.delete("/chatbot/session/{user_id}/{session_id}")
def delete_session(user_id: str, session_id: str):
    get_client().delete_session(user_id, session_id)
    return {"deleted": True, "user_id": user_id, "session_id": session_id}


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0",
            "storage": os.getenv("chatbot_STORAGE", "local"),
            "pdf_filler": os.getenv("chatbot_PDF_FILLER", "none")}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"error": str(exc)})