"""
AWS Lambda entrypoint for the chatbot module.

This is a thin wrapper that:
1. Parses the Lambda event (API Gateway proxy format or direct invocation)
2. Calls the chatbot client
3. Returns the Lambda response format

Deploy with:
    handler = entrypoints.aws_lambda.handler

Lambda event formats supported:

    Direct invocation::
        {
            "user_id": "investor_123",
            "session_id": "session_abc",
            "message": "Hello",
            "pdf_path": "/tmp/blank_form.pdf"    # optional
        }

    API Gateway proxy (automatically detected)::
        {
            "httpMethod": "POST",
            "path": "/chatbot/chat",
            "body": "{\"user_id\": ..., \"message\": ...}"
        }

Environment variables required (same as .env.example):
    OPENAI_API_KEY
    chatbot_STORAGE          (default: local — use s3 in Lambda)
    chatbot_CONFIG_PATH      (s3://bucket/configs/ or /tmp/configs)
    chatbot_PDF_FILLER       (default: none)
    ...

Note:
    For Lambda, set chatbot_STORAGE=s3 and chatbot_CONFIG_PATH to an S3 path
    pointing to your config_samples/ JSON files.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Allow imports from module root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chatbot import chatbotClient, LocalStorage, S3Storage, FormConfig
from src.chatbot.limits import RateLimitExceeded

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("chatbot_LOG_LEVEL", "INFO"))

# Module-level client — reused across Lambda warm invocations
_client: Optional[chatbotClient] = None


def _build_client() -> chatbotClient:
    storage_type = os.getenv("chatbot_STORAGE", "local").lower()

    if storage_type == "s3":
        storage = S3Storage(
            output_bucket=os.environ["AWS_OUTPUT_BUCKET"],
            config_bucket=os.environ["AWS_CONFIG_BUCKET"],
            region=os.getenv("AWS_REGION", "us-east-1"),
        )
    else:
        storage = LocalStorage(
            data_path=os.getenv("chatbot_DATA_PATH", "/tmp/chatbot_data"),
            config_path=os.getenv("chatbot_CONFIG_PATH", "/tmp/configs"),
        )

    config_path = os.getenv("chatbot_CONFIG_PATH", "/tmp/configs")
    form_config = FormConfig.from_directory(config_path)

    pdf_filler = None
    pdf_mode = os.getenv("chatbot_PDF_FILLER", "none").lower()
    if pdf_mode == "mapper":
        from src.chatbot.pdf.mapper_filler import MapperPDFFiller
        pdf_filler = MapperPDFFiller(
            mapper_api_url=os.getenv("MAPPER_API_URL", "http://localhost:8000"),
            mapper_api_key=os.getenv("MAPPER_API_KEY", ""),
        )

    return chatbotClient(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        storage=storage,
        form_config=form_config,
        pdf_filler=pdf_filler,
    )


def _get_client() -> chatbotClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _lambda_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def _parse_event(event: dict) -> dict:
    """Parse both direct invocation and API Gateway proxy events."""
    # API Gateway proxy event — body is a JSON string
    if "httpMethod" in event and "body" in event:
        body = event.get("body") or "{}"
        if isinstance(body, str):
            return json.loads(body)
        return body
    # Direct invocation — event IS the payload
    return event


def handler(event: Dict[str, Any], context: Any) -> dict:
    """Lambda handler function."""
    logger.info(f"Event type: {'api_gateway' if 'httpMethod' in event else 'direct'}")

    try:
        payload = _parse_event(event)

        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        message = payload.get("message", "")
        pdf_path = payload.get("pdf_path") or os.getenv("chatbot_PDF_PATH", "")

        if not user_id or not session_id:
            return _lambda_response(400, {"error": "user_id and session_id are required"})

        client = _get_client()

        if pdf_path:
            client.create_session(user_id, session_id, pdf_path=pdf_path)

        response, complete, data = client.send_message(
            user_id=user_id,
            session_id=session_id,
            message=message,
        )

        return _lambda_response(200, {
            "user_id": user_id,
            "session_id": session_id,
            "response": response,
            "session_complete": complete,
            "filled_data": data if complete else None,
        })

    except RateLimitExceeded as e:
        logger.warning(f"Rate limit: {e}")
        return _lambda_response(429, {"error": str(e)})
    except (KeyError, ValueError) as e:
        logger.warning(f"Bad request: {e}")
        return _lambda_response(400, {"error": str(e)})
    except Exception as e:
        logger.exception("Unhandled Lambda error")
        return _lambda_response(500, {"error": "Internal server error", "detail": str(e)})
