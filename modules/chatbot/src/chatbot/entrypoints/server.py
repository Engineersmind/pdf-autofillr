"""
chatbot-server — starts the FastAPI API server.

After `pip install "pdf-autofillr-chatbot[server]"`:
    chatbot-server

Env vars:
    PORT               default 8001
    HOST               default 0.0.0.0
    chatbot_LOG_LEVEL  default info
"""
from __future__ import annotations
import os, sys


def main():
    try:
        import uvicorn
    except ImportError:
        print("❌ Run: pip install 'pdf-autofillr-chatbot[server]'", file=sys.stderr)
        sys.exit(1)

    from dotenv import load_dotenv
    load_dotenv()

    from chatbot.entrypoints.fastapi_app import app

    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")
    log_level = os.getenv("chatbot_LOG_LEVEL", "info").lower()

    print(f"\n🚀 pdf-autofillr-chatbot API → http://{host}:{port}")
    print(f"   Docs: http://localhost:{port}/docs\n")
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()