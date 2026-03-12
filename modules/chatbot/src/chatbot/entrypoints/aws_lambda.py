"""
AWS Lambda handler for pdf-autofillr-chatbot.

Deploy as a Lambda function — drop this in as your handler.

Lambda handler: chatbot.entrypoints.aws_lambda.handler

Expected event format:
    {
        "user_id": "investor_123",
        "session_id": "session_abc",
        "message": "my name is John Smith",
        "pdf_path": "s3://your-bucket/blank_form.pdf"   # optional
    }
"""
from __future__ import annotations
import json, os, logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def _get_client():
    from chatbot import chatbotClient, LocalStorage, S3Storage, FormConfig

    if os.getenv("chatbot_STORAGE", "local").lower() == "s3":
        storage = S3Storage(
            output_bucket=os.environ["AWS_OUTPUT_BUCKET"],
            config_bucket=os.environ["AWS_CONFIG_BUCKET"],
            region=os.getenv("AWS_REGION", "us-east-1"),
        )
    else:
        storage = LocalStorage(
            data_path=os.getenv("chatbot_DATA_PATH", "/tmp/chatbot_data"),
            config_path=os.getenv("chatbot_CONFIG_PATH", "./configs"),
        )

    pdf_filler = None
    if os.getenv("chatbot_PDF_FILLER", "none").lower() == "mapper":
        from chatbot.pdf.mapper_filler import MapperPDFFiller
        pdf_filler = MapperPDFFiller(
            mapper_api_url=os.getenv("MAPPER_API_URL", "http://localhost:8000"),
            mapper_api_key=os.getenv("MAPPER_API_KEY", ""),
        )

    return chatbotClient(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        storage=storage,
        form_config=FormConfig.from_directory(os.getenv("chatbot_CONFIG_PATH", "./configs")),
        pdf_filler=pdf_filler,
    )


_client = None


def handler(event, context):
    global _client
    try:
        if _client is None:
            _client = _get_client()

        user_id    = event["user_id"]
        session_id = event["session_id"]
        message    = event.get("message", "")
        pdf_path   = event.get("pdf_path") or os.getenv("chatbot_PDF_PATH", "")

        if pdf_path:
            _client.create_session(user_id, session_id, pdf_path=pdf_path)

        response, complete, data = _client.send_message(user_id, session_id, message)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "user_id": user_id,
                "session_id": session_id,
                "response": response,
                "session_complete": complete,
                "filled_data": data if complete else None,
            })
        }
    except Exception as e:
        logger.exception("Lambda handler error")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }