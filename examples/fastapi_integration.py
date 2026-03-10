# examples/fastapi_integration.py
"""
Full FastAPI integration example with telemetry and rate limiting.
Requires: pip install chatbot-sdk[server]
"""
import os
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from chatbot import chatbotClient, LocalStorage, FormConfig
from chatbot.limits import RateLimiter, RateLimitConfig, RateLimitExceeded
from chatbot.telemetry import TelemetryConfig, DocumentContext

app = FastAPI()

# ── Client setup ─────────────────────────────────────────────────────

storage = LocalStorage("./chatbot_data", "./configs")

client = chatbotClient(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    storage=storage,
    form_config=FormConfig.from_directory("./configs"),
    pdf_filler=None,
    document_context=DocumentContext(
        category="Private Markets",
        sub_category="Private Equity",
        document_type="LP Subscription Agreement",
    ),
    telemetry=TelemetryConfig(
        enabled=True,
        mode="self_hosted",
        endpoint=os.getenv("chatbot_TELEMETRY_ENDPOINT", ""),
        sdk_api_key=os.getenv("chatbot_SDK_API_KEY", ""),
    ),
    rate_limiter=RateLimiter(
        config=RateLimitConfig(
            messages_per_session=100,
            sessions_per_user_per_day=5,
        ),
        backend="local",
    ),
)

# ── Request model ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str = ""


# ── Endpoint ──────────────────────────────────────────────────────────

@app.post("/chat")
def chat(req: ChatRequest, x_api_key: Optional[str] = Header(None)):
    expected = os.getenv("API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        response, complete, data = client.send_message(
            user_id=req.user_id,
            session_id=req.session_id,
            message=req.message,
        )
        return {
            "response": response,
            "session_complete": complete,
            "filled_data": data,
        }
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
