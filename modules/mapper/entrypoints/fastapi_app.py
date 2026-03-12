"""
FastAPI entrypoint — delegates to http_server.py.

http_server.py is the canonical FastAPI app. This module re-exports it so
that tooling that expects `entrypoints.fastapi_app:app` still works.
"""

from entrypoints.http_server import app  # noqa: F401  — re-export

if __name__ == "__main__":
    import uvicorn
    import os
    uvicorn.run(
        "entrypoints.fastapi_app:app",
        host=os.getenv("HTTP_HOST", "0.0.0.0"),
        port=int(os.getenv("HTTP_PORT", "8000")),
        log_level="info",
    )
