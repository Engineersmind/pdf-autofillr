"""
Command-line interface for the chatbot module.

Usage::

    # Interactive session (default)
    python -m entrypoints.cli

    # Single turn (useful for scripting / testing)
    python -m entrypoints.cli --user-id u1 --session-id s1 --message "Hello"

    # Provide PDF path
    python -m entrypoints.cli --pdf-path /path/to/blank.pdf

    # Non-interactive: pipe messages from a file
    cat messages.txt | python -m entrypoints.cli --user-id u1 --session-id s1

Options:
    --user-id     USER_ID     (default: cli_user)
    --session-id  SESSION_ID  (default: random UUID)
    --message     MESSAGE     Single message — exits after one turn
    --pdf-path    PDF_PATH    Path to blank PDF
    --output      PATH        Save final filled data to JSON file
    --report                  Print fill report at end
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="chatbot",
        description="chatbot conversational investor onboarding CLI",
    )
    parser.add_argument("--user-id", default="cli_user", help="User identifier")
    parser.add_argument("--session-id", default=None, help="Session identifier (default: random UUID)")
    parser.add_argument("--message", default=None, help="Single message — non-interactive mode")
    parser.add_argument("--pdf-path", default=None, help="Path to blank PDF to fill")
    parser.add_argument("--output", default=None, help="Save filled data to this JSON file path")
    parser.add_argument("--report", action="store_true", help="Print fill report at session end")
    parser.add_argument("--log-level", default="WARNING", help="Log level (default: WARNING)")
    return parser.parse_args()


def build_client():
    from src.chatbot import chatbotClient, LocalStorage, S3Storage, FormConfig

    storage_type = os.getenv("chatbot_STORAGE", "local").lower()
    if storage_type == "s3":
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


def run_single_turn(args):
    """Non-interactive: send one message and print response."""
    client = build_client()
    session_id = args.session_id or str(uuid.uuid4())
    pdf_path = args.pdf_path or os.getenv("chatbot_PDF_PATH", "")

    if pdf_path:
        client.create_session(args.user_id, session_id, pdf_path=pdf_path)

    response, complete, data = client.send_message(
        user_id=args.user_id,
        session_id=session_id,
        message=args.message,
    )
    print(response)

    if complete:
        if args.output and data:
            Path(args.output).write_text(json.dumps(data, indent=2, default=str))
            print(f"\n✅ Filled data saved to: {args.output}", file=sys.stderr)
        if args.report:
            report = client.get_fill_report_text(args.user_id, session_id)
            if report:
                print("\n" + report, file=sys.stderr)


def run_interactive(args):
    """Interactive REPL session."""
    logging.basicConfig(level=logging.WARNING)

    client = build_client()
    session_id = args.session_id or str(uuid.uuid4())
    pdf_path = args.pdf_path or os.getenv("chatbot_PDF_PATH", "")

    print("\n" + "=" * 60)
    print("  chatbot — Interactive CLI")
    print("=" * 60)
    if pdf_path:
        print(f"  PDF: {pdf_path}")
    print(f"  Session: {session_id}")
    print("  Type 'exit' to quit.\n")
    print("-" * 60 + "\n")

    if pdf_path:
        client.create_session(args.user_id, session_id, pdf_path=pdf_path)

    # Trigger greeting
    response, complete, data = client.send_message(args.user_id, session_id, "")
    print(f"Bot: {response}\n")

    while not complete:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            print("Session ended.")
            break

        response, complete, data = client.send_message(args.user_id, session_id, user_input)
        print(f"\nBot: {response}\n")

    if complete:
        print("\n" + "=" * 60)
        print("  Session complete!")
        print("=" * 60)
        if data:
            print(json.dumps(data, indent=2, default=str))
        if args.output and data:
            Path(args.output).write_text(json.dumps(data, indent=2, default=str))
            print(f"\n✅ Saved to: {args.output}")
        if args.report:
            report = client.get_fill_report_text(args.user_id, session_id)
            if report:
                print("\nFill Report:\n" + report)


def main():
    args = parse_args()
    logging.basicConfig(level=args.log_level)

    try:
        if args.message is not None:
            run_single_turn(args)
        else:
            run_interactive(args)
    except EnvironmentError as e:
        print(f"\n❌ Configuration error:\n{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
