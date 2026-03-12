"""
Local deployment entrypoint.

Provides a simple Python-callable interface for running the chatbot
in local/CLI mode without spinning up a FastAPI server.

Usage::

    from entrypoints.local import run_session

    for user_msg in ["", "Alice Johnson", "alice@example.com", ...]:
        response, complete, data = run_session("user_1", "session_1", user_msg)
        print(f"Bot: {response}")
        if complete:
            print("Filled data:", data)
            break

Or run as a script for interactive local testing::

    python -m entrypoints.local
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

# Allow running from the module root
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

logger = logging.getLogger(__name__)


def _build_client():
    """Build chatbotClient from environment variables."""
    from src.chatbot import chatbotClient, LocalStorage, S3Storage, FormConfig
    from src.chatbot.pdf.mapper_filler import MapperPDFFiller

    storage_type = os.getenv("chatbot_STORAGE", "local").lower()
    if storage_type == "s3":
        from src.chatbot import S3Storage
        storage = S3Storage(
            output_bucket=os.environ["AWS_OUTPUT_BUCKET"],
            config_bucket=os.environ["AWS_CONFIG_BUCKET"],
            region=os.getenv("AWS_REGION", "us-east-1"),
        )
    else:
        storage = LocalStorage(
            data_path=os.getenv("chatbot_DATA_PATH", "./chatbot_data"),
            config_path=os.getenv("chatbot_CONFIG_PATH", "./config_samples"),
        )

    config_path = os.getenv("chatbot_CONFIG_PATH", "./config_samples")
    form_config = FormConfig.from_directory(config_path)

    pdf_filler = None
    pdf_mode = os.getenv("chatbot_PDF_FILLER", "none").lower()
    if pdf_mode == "mapper":
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


def run_session(
    user_id: str,
    session_id: str,
    message: str,
    pdf_path: Optional[str] = None,
    client=None,
) -> Tuple[str, bool, Optional[dict]]:
    """
    Send one message in a session.

    Args:
        user_id:    Unique user identifier.
        session_id: Unique session identifier.
        message:    The user's message text.
        pdf_path:   Optional path to the blank PDF (first turn only).
        client:     Optional pre-built chatbotClient. Built from env if not provided.

    Returns:
        (response_text, session_complete, filled_data_if_complete)
    """
    if client is None:
        client = _build_client()

    if pdf_path:
        client.create_session(user_id, session_id, pdf_path=pdf_path)

    return client.send_message(user_id=user_id, session_id=session_id, message=message)


def run_interactive():
    """
    Run an interactive chat session in the terminal.
    Press Ctrl+C or type 'exit' to stop.
    """
    import uuid
    logging.basicConfig(level=logging.WARNING)

    print("\n" + "=" * 60)
    print("  chatbot — Interactive Local Session")
    print("=" * 60)
    print("Type your responses and press Enter.")
    print("Type 'exit' to quit.\n")

    client = _build_client()
    user_id = "local_user"
    session_id = str(uuid.uuid4())
    pdf_path = os.getenv("chatbot_PDF_PATH", "")

    if pdf_path:
        client.create_session(user_id, session_id, pdf_path=pdf_path)
        print(f"PDF: {pdf_path}\n")

    print("-" * 60)

    # Start conversation with empty message (triggers greeting)
    try:
        response, complete, data = client.send_message(user_id, session_id, "")
        print(f"Bot: {response}\n")

        while not complete:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nSession ended.")
                break

            if user_input.lower() in ("exit", "quit", "q"):
                print("Session ended.")
                break

            response, complete, data = client.send_message(user_id, session_id, user_input)
            print(f"\nBot: {response}\n")

        if complete:
            print("\n" + "=" * 60)
            print("  Session complete! Data collected:")
            print("=" * 60)
            if data:
                import json
                print(json.dumps(data, indent=2, default=str))

            report = client.get_fill_report_text(user_id, session_id)
            if report:
                print("\nFill Report:")
                print(report)

    except EnvironmentError as e:
        print(f"\n❌ Configuration error:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    run_interactive()
