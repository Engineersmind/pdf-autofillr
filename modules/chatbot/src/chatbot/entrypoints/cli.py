"""
chatbot-cli — interactive terminal session.

After `pip install pdf-autofillr-chatbot`:
    chatbot-cli
    chatbot-cli --pdf-path /path/to/blank.pdf --output filled.json --report
"""
from __future__ import annotations
import argparse, json, logging, os, sys, uuid
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(prog="chatbot-cli",
        description="pdf-autofillr-chatbot — conversational investor onboarding")
    p.add_argument("--user-id",    default="cli_user")
    p.add_argument("--session-id", default=None)
    p.add_argument("--message",    default=None, help="Single message (non-interactive)")
    p.add_argument("--pdf-path",   default=None)
    p.add_argument("--output",     default=None, help="Save filled data to JSON file")
    p.add_argument("--report",     action="store_true")
    p.add_argument("--log-level",  default="WARNING")
    return p.parse_args()


def build_client():
    from chatbot import chatbotClient, LocalStorage, S3Storage, FormConfig

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

    config_path = os.getenv("chatbot_CONFIG_PATH", "./configs")
    form_config = FormConfig.from_directory(config_path)

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
        form_config=form_config,
        pdf_filler=pdf_filler,
    )


def run_single_turn(args):
    client = build_client()
    session_id = args.session_id or str(uuid.uuid4())
    pdf_path = args.pdf_path or os.getenv("chatbot_PDF_PATH", "")
    if pdf_path:
        client.create_session(args.user_id, session_id, pdf_path=pdf_path)
    response, complete, data = client.send_message(args.user_id, session_id, args.message)
    print(response)
    if complete:
        if args.output and data:
            Path(args.output).write_text(json.dumps(data, indent=2, default=str))
        if args.report:
            report = client.get_fill_report_text(args.user_id, session_id)
            if report:
                print("\n" + report, file=sys.stderr)


def run_interactive(args):
    client = build_client()
    session_id = args.session_id or str(uuid.uuid4())
    pdf_path = args.pdf_path or os.getenv("chatbot_PDF_PATH", "")

    print("\n" + "=" * 60)
    print("  pdf-autofillr-chatbot")
    print("=" * 60)
    if pdf_path:
        print(f"  PDF: {pdf_path}")
    print(f"  Session: {session_id}")
    print("  Type 'exit' to quit.\n" + "-" * 60 + "\n")

    if pdf_path:
        client.create_session(args.user_id, session_id, pdf_path=pdf_path)

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
        print("\n" + "=" * 60 + "\n  Session complete!\n" + "=" * 60)
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
        print(f"\n❌ Config error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()