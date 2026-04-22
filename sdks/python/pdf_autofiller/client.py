"""MapperClient — talks to the PDF Autofiller mapper Lambda Function URL."""

import httpx
import os
from typing import Optional

from .exceptions import APIError, AuthenticationError, TimeoutError, ValidationError

# Production Lambda Function URL.
# - In the open-source repo this is None (never committed).
# - The PyPI release pipeline injects the real URL before building the wheel.
# - Override at runtime via PDF_AUTOFILLER_FUNCTION_URL (local dev / staging).
_DEFAULT_FUNCTION_URL: Optional[str] = os.environ.get("PDF_AUTOFILLER_FUNCTION_URL") or None
# <<INJECT_FUNCTION_URL>>  ← CI replaces this line with: _DEFAULT_FUNCTION_URL = "https://..."


class MapperClient:
    """
    Client for the PDF Autofiller mapper Lambda.

    Consumers only need an **API key** — the endpoint URL is baked in::

        client = MapperClient(api_key="your-api-key")

        # API 1 — extract, map, and embed a PDF (run before fill_pdf)
        result = client.make_embed_file(
            user_id=1,
            pdf_doc_id=42,
            session_id="sess-abc",
            env="prod",
        )

        # API 3 — check whether the embed file is cached / ready
        status = client.check_embed_file(
            user_id=1, pdf_doc_id=42, session_id="sess-abc", env="prod"
        )

        # API 2 — fill the PDF with user data
        fill = client.fill_pdf(
            user_id=1, pdf_doc_id=42, session_id="sess-abc", env="prod"
        )

    For local development, override the endpoint::

        client = MapperClient(api_key="dev-key", function_url="http://localhost:8000")

    Or via environment variable::

        PDF_AUTOFILLER_FUNCTION_URL=http://localhost:8000 python your_script.py

    Use as a context manager to ensure the HTTP connection is closed::

        with MapperClient(api_key="your-api-key") as client:
            client.make_embed_file(...)
    """

    def __init__(
        self,
        api_key: str,
        function_url: Optional[str] = None,
        timeout: float = 600.0,
    ):
        """
        Args:
            api_key:      API key issued by Engineersmind. Required.
            function_url: Override the default Lambda endpoint.  Leave unset
                          for production use — only needed for local dev or staging.
                          Can also be set via the ``PDF_AUTOFILLER_FUNCTION_URL``
                          environment variable.
            timeout:      Seconds before the request is aborted.
                          Defaults to 600 s (10 min) — embed operations are slow.
        """
        if not api_key:
            raise ValidationError("api_key is required")

        resolved_url = function_url or _DEFAULT_FUNCTION_URL
        if not resolved_url:
            raise ValidationError(
                "No endpoint URL found. Set the PDF_AUTOFILLER_FUNCTION_URL environment "
                "variable, or pass function_url= explicitly (e.g. for local dev)."
            )

        self._url = resolved_url.rstrip("/")
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
        )

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def make_embed_file(
        self,
        user_id: int,
        pdf_doc_id: int,
        session_id: str,
        env: str,
        developer_id: Optional[str] = None,
        investor_type: str = "individual",
        use_second_mapper: bool = False,
    ) -> dict:
        """
        API 1 — Extract fields, map them, and embed the result into the PDF.

        Run this once per PDF before calling :meth:`fill_pdf`.
        The result is cached in S3; subsequent calls for the same PDF return
        the cached version via :meth:`check_embed_file`.

        Args:
            user_id:           Numeric user ID from your backend.
            pdf_doc_id:        Document ID of the uploaded PDF.
            session_id:        Active session identifier.
            env:               Deployment environment (``"prod"`` or ``"dev"``).
            developer_id:      Optional developer / partner identifier.
            investor_type:     Investor profile hint (default ``"individual"``).
            use_second_mapper: Use the RAG-based second-pass mapper (default ``False``).

        Returns:
            ``result`` dict from the Lambda response body.
        """
        payload = {
            "operation": "make_embed_file",
            "user_id": user_id,
            "pdf_doc_id": pdf_doc_id,
            "session_id": session_id,
            "env": env,
            "investor_type": investor_type,
            "use_second_mapper": use_second_mapper,
        }
        if developer_id is not None:
            payload["developer_id"] = developer_id

        return self._post(payload)

    def fill_pdf(
        self,
        user_id: int,
        pdf_doc_id: int,
        session_id: str,
        env: str,
        developer_id: Optional[str] = None,
    ) -> dict:
        """
        API 2 — Fill the embedded PDF with the user's data.

        Requires :meth:`make_embed_file` to have been called first for this PDF.

        Args:
            user_id:      Numeric user ID.
            pdf_doc_id:   Document ID of the embedded PDF.
            session_id:   Active session identifier.
            env:          Deployment environment (``"prod"`` or ``"dev"``).
            developer_id: Optional developer / partner identifier.

        Returns:
            ``result`` dict from the Lambda response body, including the S3
            URL of the filled PDF.
        """
        payload = {
            "operation": "fill_pdf",
            "user_id": user_id,
            "pdf_doc_id": pdf_doc_id,
            "session_id": session_id,
            "env": env,
        }
        if developer_id is not None:
            payload["developer_id"] = developer_id

        return self._post(payload)

    def check_embed_file(
        self,
        user_id: int,
        pdf_doc_id: int,
        session_id: str,
        env: str,
        developer_id: Optional[str] = None,
    ) -> dict:
        """
        API 3 — Check whether the embed file for this PDF is cached and ready.

        Use this to avoid re-running :meth:`make_embed_file` for a PDF that
        has already been processed.

        Args:
            user_id:      Numeric user ID.
            pdf_doc_id:   Document ID to check.
            session_id:   Active session identifier.
            env:          Deployment environment (``"prod"`` or ``"dev"``).
            developer_id: Optional developer / partner identifier.

        Returns:
            ``result`` dict.  Inspect ``result["cache_hit"]`` (bool) to decide
            whether to call :meth:`make_embed_file`.
        """
        payload = {
            "operation": "check_embed_file",
            "user_id": user_id,
            "pdf_doc_id": pdf_doc_id,
            "session_id": session_id,
            "env": env,
        }
        if developer_id is not None:
            payload["developer_id"] = developer_id

        return self._post(payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, payload: dict) -> dict:
        """POST ``payload`` to the Lambda Function URL and return the result dict."""
        try:
            response = self._client.post(self._url, json=payload)
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Request timed out for operation '{payload.get('operation')}'"
            ) from exc
        except httpx.RequestError as exc:
            raise APIError(f"Network error: {exc}") from exc

        if response.status_code == 401:
            raise AuthenticationError("Invalid or missing X-API-Key header")
        if response.status_code == 403:
            raise AuthenticationError("API key is not authorised")

        try:
            body = response.json()
        except Exception:
            body = {}

        # Lambda Function URL wraps the handler's return value differently
        # depending on invocation mode.  Normalise both shapes here.
        if isinstance(body, dict) and "body" in body:
            # Function URL passthrough: {"statusCode": N, "body": "{...}"}
            import json as _json
            raw_body = body["body"]
            if isinstance(raw_body, str):
                try:
                    body = _json.loads(raw_body)
                except Exception:
                    body = {"message": raw_body}
            else:
                body = raw_body

        status = response.status_code
        if status == 400:
            raise ValidationError(body.get("message", "Validation error"))
        if status >= 500:
            raise APIError(
                body.get("error", "Lambda error"),
                status_code=status,
                response=body,
            )
        if status >= 400:
            raise APIError(
                body.get("message", f"HTTP {status}"),
                status_code=status,
                response=body,
            )

        return body.get("result", body)

    def close(self):
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
