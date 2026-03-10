# chatbot_managed/filler.py
"""
chatbotManagedPDFFiller — PRIVATE PACKAGE (do NOT commit to open-source SDK repo).

This file lives in your private `chatbot-managed` pip package.
It implements PDFFillerInterface using your Auth0 + PDF Lambda service.

Install privately:
    pip install ./chatbot-managed   # from private repo

Then wire it:
    from chatbot_managed.filler import chatbotManagedPDFFiller
    from chatbot import chatbotClient

    client = chatbotClient(
        ...,
        pdf_filler=chatbotManagedPDFFiller(
            auth0_domain=os.environ["AUTH0_DOMAIN"],
            auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
            auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
            auth0_audience=os.environ["AUTH0_AUDIENCE"],
            pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
            pdf_api_key=os.environ["PDF_API_KEY"],
            backend_url=os.environ["BACKEND_URL"],
            auth_token=os.environ["AUTH_TOKEN"],
        )
    )
"""
from __future__ import annotations

import time
from typing import Any, Optional

import requests

from chatbot.pdf.interface import PDFFillerInterface


class chatbotManagedPDFFiller(PDFFillerInterface):
    """
    Connects to your private Auth0-authenticated PDF Lambda service.

    Steps mapped to PDFFillerInterface:
        prepare_document()     → Auth0 token  +  make_embed_file   (Step 3)
        check_document_ready() → Auth0 token  +  check_embed_file  (Step 5)
        fill_document()        → Auth0 token  +  fill_pdf          (Step 6)

    Steps 1 & 2 (fetching the PDF doc ID from your backend REST API and
    uploading the blank PDF to your static bucket) happen OUTSIDE this SDK —
    in your existing backend. The sdk receives the pdf_path as an S3 key or
    URL that your backend has already placed in the right location.
    """

    def __init__(
        self,
        auth0_domain: str,
        auth0_client_id: str,
        auth0_client_secret: str,
        auth0_audience: str,
        pdf_lambda_url: str,
        pdf_api_key: str,
        backend_url: str = "",
        auth_token: str = "",
        token_cache_buffer_seconds: int = 60,
    ):
        self._auth0_domain = auth0_domain
        self._auth0_client_id = auth0_client_id
        self._auth0_client_secret = auth0_client_secret
        self._auth0_audience = auth0_audience
        self._pdf_lambda_url = pdf_lambda_url
        self._pdf_api_key = pdf_api_key
        self._backend_url = backend_url
        self._auth_token = auth_token
        self._token_cache_buffer = token_cache_buffer_seconds

        # Token cache — avoid re-fetching on every call
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # PDFFillerInterface implementation
    # ------------------------------------------------------------------

    def prepare_document(self, pdf_path: str, investor_type: str) -> str:
        """
        Step 3 — make_embed_file.
        Calls your PDF Lambda with operation=make_embed_file.
        Returns doc_id (the embed file ID from your service).
        """
        token = self._get_auth0_token()
        payload = {
            "operation": "make_embed_file",
            "pdf_path": pdf_path,
            "investor_type": investor_type,
            "api_key": self._pdf_api_key,
        }
        resp = requests.post(
            self._pdf_lambda_url,
            json=payload,
            headers=self._auth_headers(token),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        doc_id = data.get("doc_id") or data.get("embed_id") or data.get("id")
        if not doc_id:
            raise ValueError(f"prepare_document: no doc_id in response: {data}")
        return doc_id

    def check_document_ready(self, doc_id: str) -> bool:
        """
        Step 5 — check_embed_file.
        Returns True when the document is ready to be filled.
        """
        token = self._get_auth0_token()
        payload = {
            "operation": "check_embed_file",
            "doc_id": doc_id,
            "api_key": self._pdf_api_key,
        }
        resp = requests.post(
            self._pdf_lambda_url,
            json=payload,
            headers=self._auth_headers(token),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "").lower()
        return status in ("ready", "complete", "done", "success")

    def fill_document(self, doc_id: str, data_flat: dict) -> Any:
        """
        Step 6 — fill_pdf.
        Sends the collected investor data to fill the prepared PDF.
        Returns whatever your Lambda returns (typically a download URL or S3 key).
        """
        token = self._get_auth0_token()
        payload = {
            "operation": "fill_pdf",
            "doc_id": doc_id,
            "data": data_flat,
            "api_key": self._pdf_api_key,
        }
        resp = requests.post(
            self._pdf_lambda_url,
            json=payload,
            headers=self._auth_headers(token),
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _get_auth0_token(self) -> str:
        """Return a cached or freshly fetched Auth0 machine-to-machine token."""
        now = time.time()
        if self._cached_token and now < self._token_expires_at - self._token_cache_buffer:
            return self._cached_token

        resp = requests.post(
            f"https://{self._auth0_domain}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": self._auth0_client_id,
                "client_secret": self._auth0_client_secret,
                "audience": self._auth0_audience,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._cached_token = data["access_token"]
        self._token_expires_at = now + data.get("expires_in", 3600)
        return self._cached_token

    def _auth_headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }