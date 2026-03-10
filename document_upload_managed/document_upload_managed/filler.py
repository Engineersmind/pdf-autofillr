# # document_upload_managed/filler.py
# """
# DocUploadManagedPDFFiller — PRIVATE PACKAGE — document_upload_managed folder (do NOT commit to open-source SDK repo).

# This file lives in your private `document_upload_managed` pip package.
# It implements PDFFillerInterface using your Auth0 + PDF Lambda service.

# Install privately:
#     pip install ./document_upload_managed   # from private repo

# Then wire it:
#     from document_upload_managed.filler import DocUploadManagedPDFFiller
#     from uploaddocument import UploadDocumentClient

#     client = UploadDocumentClient(
#         ...,
#         pdf_filler=DocUploadManagedPDFFiller(
#             auth0_domain=os.environ["AUTH0_DOMAIN"],
#             auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
#             auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
#             auth0_audience=os.environ["AUTH0_AUDIENCE"],
#             pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
#             pdf_api_key=os.environ["PDF_API_KEY"],
#             backend_url=os.environ["BACKEND_URL"],
#             auth_token=os.environ["AUTH_TOKEN"],
#         )
#     )
# """
# from __future__ import annotations

# import time
# from typing import Any, Optional

# import requests

# from uploaddocument.pdf.interface import PDFFillerInterface


# class DocUploadManagedPDFFiller(PDFFillerInterface):
#     """
#     Connects to your private Auth0-authenticated PDF Lambda service.

#     Steps mapped to PDFFillerInterface:
#         prepare_document()     → Auth0 token  +  make_embed_file   (Step 3)
#         check_document_ready() → Auth0 token  +  check_embed_file  (Step 5)
#         fill_document()        → Auth0 token  +  fill_pdf          (Step 6)

#     Steps 1 & 2 (fetching the PDF doc ID from your backend REST API and
#     uploading the blank PDF to your static bucket) happen OUTSIDE this SDK —
#     in your existing backend. The sdk receives the pdf_path as an S3 key or
#     URL that your backend has already placed in the right location.
#     """

#     def __init__(
#         self,
#         auth0_domain: str,
#         auth0_client_id: str,
#         auth0_client_secret: str,
#         auth0_audience: str,
#         pdf_lambda_url: str,
#         pdf_api_key: str,
#         backend_url: str = "",
#         auth_token: str = "",
#         token_cache_buffer_seconds: int = 60,
#     ):
#         self._auth0_domain = auth0_domain
#         self._auth0_client_id = auth0_client_id
#         self._auth0_client_secret = auth0_client_secret
#         self._auth0_audience = auth0_audience
#         self._pdf_lambda_url = pdf_lambda_url
#         self._pdf_api_key = pdf_api_key
#         self._backend_url = backend_url
#         self._auth_token = auth_token
#         self._token_cache_buffer = token_cache_buffer_seconds

#         # Token cache — avoid re-fetching on every call
#         self._cached_token: Optional[str] = None
#         self._token_expires_at: float = 0.0

#     # ------------------------------------------------------------------
#     # PDFFillerInterface implementation
#     # ------------------------------------------------------------------

#     def prepare_document(self, pdf_path: str, document_type: str) -> str:
#         """
#         Step 3 — make_embed_file.
#         Calls your PDF Lambda with operation=make_embed_file.
#         Returns doc_id (the embed file ID from your service).
#         """
#         token = self._get_auth0_token()
#         payload = {
#             "operation": "make_embed_file",
#             "pdf_path": pdf_path,
#             "document_type": document_type,
#             "api_key": self._pdf_api_key,
#         }
#         resp = requests.post(
#             self._pdf_lambda_url,
#             json=payload,
#             headers=self._auth_headers(token),
#             timeout=30,
#         )
#         resp.raise_for_status()
#         data = resp.json()
#         doc_id = data.get("doc_id") or data.get("embed_id") or data.get("id")
#         if not doc_id:
#             raise ValueError(f"prepare_document: no doc_id in response: {data}")
#         return doc_id

#     def check_document_ready(self, doc_id: str) -> bool:
#         """
#         Step 5 — check_embed_file.
#         Returns True when the document is ready to be filled.
#         """
#         token = self._get_auth0_token()
#         payload = {
#             "operation": "check_embed_file",
#             "doc_id": doc_id,
#             "api_key": self._pdf_api_key,
#         }
#         resp = requests.post(
#             self._pdf_lambda_url,
#             json=payload,
#             headers=self._auth_headers(token),
#             timeout=15,
#         )
#         resp.raise_for_status()
#         data = resp.json()
#         status = data.get("status", "").lower()
#         return status in ("ready", "complete", "done", "success")

#     def fill_document(self, doc_id: str, data_flat: dict) -> Any:
#         """
#         Step 6 — fill_pdf.
#         Sends the collected investor data to fill the prepared PDF.
#         Returns whatever your Lambda returns (typically a download URL or S3 key).
#         """
#         token = self._get_auth0_token()
#         payload = {
#             "operation": "fill_pdf",
#             "doc_id": doc_id,
#             "data": data_flat,
#             "api_key": self._pdf_api_key,
#         }
#         resp = requests.post(
#             self._pdf_lambda_url,
#             json=payload,
#             headers=self._auth_headers(token),
#             timeout=60,
#         )
#         resp.raise_for_status()
#         return resp.json()

#     # ------------------------------------------------------------------
#     # Auth helpers
#     # ------------------------------------------------------------------

#     def _get_auth0_token(self) -> str:
#         """Return a cached or freshly fetched Auth0 machine-to-machine token."""
#         now = time.time()
#         if self._cached_token and now < self._token_expires_at - self._token_cache_buffer:
#             return self._cached_token

#         resp = requests.post(
#             f"https://{self._auth0_domain}/oauth/token",
#             json={
#                 "grant_type": "client_credentials",
#                 "client_id": self._auth0_client_id,
#                 "client_secret": self._auth0_client_secret,
#                 "audience": self._auth0_audience,
#             },
#             timeout=10,
#         )
#         resp.raise_for_status()
#         data = resp.json()
#         self._cached_token = data["access_token"]
#         self._token_expires_at = now + data.get("expires_in", 3600)
#         return self._cached_token

#     def _auth_headers(self, token: str) -> dict:
#         return {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json",
#         }















# document_upload_managed/filler.py
"""
DocUploadManagedPDFFiller — PRIVATE PACKAGE — document_upload_managed folder.
DO NOT commit this file to the open-source SDK repo.

This file lives in your private `document_upload_managed` pip package.
It implements PDFFillerInterface using your Auth0 + PDF Lambda service.

Install privately:
    pip install ./document_upload_managed   # from repo root, never via PyPI

Wire it:
    from document_upload_managed.filler import DocUploadManagedPDFFiller
    from uploaddocument import UploadDocumentClient

    client = UploadDocumentClient(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        storage=S3Storage(...),
        schema_config=SchemaConfig.from_s3(...),
        pdf_filler=DocUploadManagedPDFFiller(
            auth0_domain=os.environ["AUTH0_DOMAIN"],
            auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
            auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
            auth0_audience=os.environ["AUTH0_AUDIENCE"],
            pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
            pdf_api_key=os.environ["PDF_API_KEY"],
        ),
    )

    result = client.process_document(
        document_path="s3://your-bucket/docs/investor_pack.pdf",
        user_id="123",           # must be convertible to int — matches your Lambda
        session_id="session_abc",
        pdf_path="s3://your-bucket/blank/subscription.pdf",
        pdf_doc_id="456",        # the blank PDF's doc ID in your system (int-castable)
        filled_doc_pdf_id="789", # the investor's filled-doc ID in your system (int-castable)
        investor_type="Individual",
    )

HOW THE LAMBDA FIELDS MAP
--------------------------
Your Lambda (lambda_function.py) reads these fields from the request body:

    user_id           → int — the investor's user account ID
    session_id        → str — the session being processed
    filled_doc_pdf_id → int — ID used for S3 output paths (the "left"/filled doc)
    pdf_doc_id        → int — ID sent to the PDF-embed API calls (the "right"/blank doc)
    pdf_location      → str — S3 URI of the source document to extract from
    investor_type     → str — e.g. "Individual", "Corporation" (default "Individual")

The PDFFillerInterface methods receive these via **context kwargs injected
by ParallelRunner (see parallel_runner.py changes). The filler caches them
in _ctx for reuse across prepare_document → check_document_ready → fill_document.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import requests

from uploaddocument.pdf.interface import PDFFillerInterface


class DocUploadManagedPDFFiller(PDFFillerInterface):
    """
    Connects to your private Auth0-authenticated PDF Lambda service.

    PDFFillerInterface method → Lambda operation mapping:
        prepare_document()     →  make_embed_file   (Step 3 / Thread B)
        check_document_ready() →  check_embed_file  (Step 5 / Thread B polling)
        fill_document()        →  fill_pdf          (Step 6 / sequential after both threads)

    Steps 1 & 2 (Auth0 token fetch for user login, and fetching pdf_doc_id
    from your backend) happen in your existing backend before calling the SDK.
    The SDK receives pdf_doc_id, filled_doc_pdf_id, and investor_type as
    extra kwargs passed to process_document(), which ParallelRunner injects
    into each interface call via **context.
    """

    def __init__(
        self,
        auth0_domain: str,
        auth0_client_id: str,
        auth0_client_secret: str,
        auth0_audience: str,
        pdf_lambda_url: str,
        pdf_api_key: str,
        token_cache_buffer_seconds: int = 60,
        make_embed_timeout: int = 30,
        check_embed_timeout: int = 15,
        fill_pdf_timeout: int = 200,
        use_second_mapper: bool = True,
        use_profile_info: bool = True,
    ):
        self._auth0_domain = auth0_domain
        self._auth0_client_id = auth0_client_id
        self._auth0_client_secret = auth0_client_secret
        self._auth0_audience = auth0_audience
        self._pdf_lambda_url = pdf_lambda_url
        self._pdf_api_key = pdf_api_key
        self._token_cache_buffer = token_cache_buffer_seconds
        self._make_embed_timeout = make_embed_timeout
        self._check_embed_timeout = check_embed_timeout
        self._fill_pdf_timeout = fill_pdf_timeout
        self._use_second_mapper = use_second_mapper
        self._use_profile_info = use_profile_info

        # Auth0 token cache — one token reused across all three Lambda calls
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

        # Runtime context set by ParallelRunner for each process_document() call.
        # Keys: user_id, session_id, pdf_doc_id, filled_doc_pdf_id, investor_type
        self._ctx: dict = {}

    # ------------------------------------------------------------------
    # Context injection — called by ParallelRunner before Thread B starts
    # ------------------------------------------------------------------

    def set_context(
        self,
        user_id: str,
        session_id: str,
        pdf_doc_id: str,
        filled_doc_pdf_id: str,
        investor_type: str = "Individual",
    ) -> None:
        """
        Store per-call context so all three interface methods can read it.
        Called once by ParallelRunner at the start of each pipeline run.
        """
        self._ctx = {
            "user_id": user_id,
            "session_id": session_id,
            "pdf_doc_id": pdf_doc_id,
            "filled_doc_pdf_id": filled_doc_pdf_id,
            "investor_type": investor_type,
        }

    # ------------------------------------------------------------------
    # PDFFillerInterface — Step 3: prepare_document → make_embed_file
    # ------------------------------------------------------------------

    def prepare_document(self, pdf_path: str, document_type: str) -> str:
        """
        Step 3 — make_embed_file.

        Calls your PDF Lambda with operation=make_embed_file.
        pdf_path and document_type come from the SDK interface but are not
        forwarded to your Lambda (your Lambda locates the PDF via pdf_doc_id).

        Returns:
            A string token that encodes (user_id, session_id, pdf_doc_id) so
            check_document_ready and fill_document can use it without needing
            a separate doc_id concept that your Lambda doesn't have.
        """
        user_id = self._ctx.get("user_id", "")
        session_id = self._ctx.get("session_id", "")
        pdf_doc_id = self._ctx.get("pdf_doc_id", "")
        investor_type = self._ctx.get("investor_type", "Individual")

        self._validate_ctx("prepare_document")

        token = self._get_auth0_token()

        payload = {
            "operation": "make_embed_file",
            "user_id": _to_int(user_id, "user_id"),
            "pdf_doc_id": _to_int(pdf_doc_id, "pdf_doc_id"),
            "session_id": session_id,
            "investor_type": investor_type,
            "use_second_mapper": self._use_second_mapper,
        }

        resp = requests.post(
            self._pdf_lambda_url,
            json=payload,
            headers=self._lambda_headers(token),
            timeout=self._make_embed_timeout,
        )
        resp.raise_for_status()

        # Return a composite token — the Lambda has no concept of a "doc_id".
        # check_document_ready and fill_document decode this to reconstruct the
        # fields they need.
        return _encode_ctx(user_id, session_id, pdf_doc_id, investor_type)

    # ------------------------------------------------------------------
    # PDFFillerInterface — Step 5: check_document_ready → check_embed_file
    # ------------------------------------------------------------------

    def check_document_ready(self, doc_id: str) -> bool:
        """
        Step 5 — check_embed_file.

        doc_id is the composite token returned by prepare_document.
        Decodes it to get user_id, pdf_doc_id, investor_type.

        Returns True when result.embedded_pdf_created is True in the Lambda
        response — matching the actual Lambda response format exactly.
        """
        user_id, session_id, pdf_doc_id, investor_type = _decode_ctx(doc_id)

        token = self._get_auth0_token()

        payload = {
            "operation": "check_embed_file",
            "user_id": _to_int(user_id, "user_id"),
            "pdf_doc_id": _to_int(pdf_doc_id, "pdf_doc_id"),
            "investor_type": investor_type,
        }

        resp = requests.post(
            self._pdf_lambda_url,
            json=payload,
            headers=self._lambda_headers(token),
            timeout=self._check_embed_timeout,
        )
        resp.raise_for_status()

        data = resp.json()

        # Your Lambda returns:  { "result": { "embedded_pdf_created": true/false,
        #                                     "embedded_pdf_path": "..." } }
        result = data.get("result", {})
        return bool(result.get("embedded_pdf_created", False))

    # ------------------------------------------------------------------
    # PDFFillerInterface — Step 6: fill_document → fill_pdf
    # ------------------------------------------------------------------

    def fill_document(self, doc_id: str, data_flat: dict) -> Any:
        """
        Step 6 — fill_pdf.

        doc_id is the composite token returned by prepare_document.
        data_flat is the flat extracted dict — forwarded to the Lambda as-is
        (your Lambda reads the flat JSON from S3, not from the request body,
        so data_flat is not in the payload — the Lambda reads it from S3 using
        user_id + session_id to locate final_output_flat.json).

        Returns the full Lambda response dict (contains status + output S3 path).
        """
        user_id, session_id, pdf_doc_id, investor_type = _decode_ctx(doc_id)

        token = self._get_auth0_token()

        payload = {
            "operation": "fill_pdf",
            "user_id": _to_int(user_id, "user_id"),
            "pdf_doc_id": _to_int(pdf_doc_id, "pdf_doc_id"),
            "session_id": session_id,
            "use_profile_info": self._use_profile_info,
        }

        resp = requests.post(
            self._pdf_lambda_url,
            json=payload,
            headers=self._lambda_headers(token),
            timeout=self._fill_pdf_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Auth0 helpers
    # ------------------------------------------------------------------

    def _get_auth0_token(self) -> str:
        """Return a cached or freshly fetched Auth0 M2M token."""
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

    def _lambda_headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "X-API-Key": self._pdf_api_key,
            "Content-Type": "application/json",
        }

    def _validate_ctx(self, method: str) -> None:
        required = ("user_id", "session_id", "pdf_doc_id")
        missing = [k for k in required if not self._ctx.get(k)]
        if missing:
            raise RuntimeError(
                f"DocUploadManagedPDFFiller.{method}() called without context. "
                f"Missing fields: {missing}. "
                "Pass pdf_doc_id, filled_doc_pdf_id, and investor_type to "
                "client.process_document() so ParallelRunner can call set_context()."
            )


# ------------------------------------------------------------------
# Helpers — encode/decode composite context token
# ------------------------------------------------------------------
# The PDFFillerInterface only passes a single string "doc_id" between
# prepare_document → check_document_ready → fill_document.
# Your Lambda doesn't use a doc_id — it uses (user_id, session_id, pdf_doc_id).
# We pack those into a pipe-delimited string so the interface contract is met
# without changing the abstract interface signature.

_SEP = "|"


def _encode_ctx(user_id: str, session_id: str, pdf_doc_id: str, investor_type: str) -> str:
    for v in (user_id, session_id, pdf_doc_id, investor_type):
        if _SEP in str(v):
            raise ValueError(f"Context value contains reserved separator '{_SEP}': {v!r}")
    return _SEP.join([str(user_id), str(session_id), str(pdf_doc_id), str(investor_type)])


def _decode_ctx(token: str) -> tuple:
    """Returns (user_id, session_id, pdf_doc_id, investor_type)."""
    parts = token.split(_SEP)
    if len(parts) != 4:
        raise ValueError(
            f"Invalid doc_id token — expected 4 pipe-separated parts, got: {token!r}. "
            "This usually means prepare_document() was not called, or set_context() "
            "was not called by ParallelRunner."
        )
    return parts[0], parts[1], parts[2], parts[3]


def _to_int(value: str, field_name: str) -> int:
    """Cast value to int — your Lambda requires integer user_id and pdf_doc_id."""
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"DocUploadManagedPDFFiller: {field_name}={value!r} cannot be cast to int. "
            "Your Lambda requires integer IDs. Pass a numeric string."
        ) from e