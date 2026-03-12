# chatbot/pdf/mapper_filler.py
"""
MapperPDFFiller — connects chatbot SDK to the pdf-autofillr mapper module.

Implements PDFFillerInterface using the mapper's REST API (via PDFMapperClient).

Install the mapper SDK alongside this package:
    pip install pdf-autofiller-sdk          # from mapper sdks/python/
    # or install locally: pip install -e path/to/sdks/python/

Usage::

    from chatbot.pdf.mapper_filler import MapperPDFFiller

    filler = MapperPDFFiller(
        mapper_api_url="http://localhost:8000",
        mapper_api_key=os.getenv("MAPPER_API_KEY", ""),
    )

    client = chatbotClient(
        ...,
        pdf_filler=filler,
    )

IMPORTANT — URL convention:
    The mapper api_server.py registers routes under /mapper/* prefix
    (e.g. POST /mapper/make-embed-file).  Set MAPPER_API_URL to the
    server root WITHOUT the /mapper suffix:
        MAPPER_API_URL=http://localhost:8000
    This class appends /mapper internally.

    If you are pointing at the bare fastapi_app.py (no prefix), set:
        MAPPER_API_URL=http://localhost:8000
        MAPPER_URL_PREFIX=   (empty string)
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from chatbot.pdf.interface import PDFFillerInterface

logger = logging.getLogger(__name__)


class MapperPDFFiller(PDFFillerInterface):
    """
    Connects chatbot conversation output → pdf-autofillr mapper module.

    Maps the 3 PDFFillerInterface steps to mapper API calls:

        prepare_document()     → POST /mapper/make-embed-file
                                 Runs Extract + Map + Embed pipeline on the PDF.
                                 Returns the embedded PDF path as doc_id.

        check_document_ready() → POST /mapper/check-embed-file
                                 Returns True when the embedded PDF file exists
                                 and is ready to fill.

        fill_document()        → POST /mapper/fill
                                 Fills the embedded PDF with collected investor data.
                                 Returns the fill result dict from the mapper.

    Args:
        mapper_api_url: Base URL of the running mapper API server (no /mapper suffix).
                        Defaults to MAPPER_API_URL env var, then http://localhost:8000.
        mapper_api_key: API key for the mapper server (X-API-Key header).
                        Defaults to MAPPER_API_KEY env var.
        url_prefix:     Route prefix used by the mapper server. Defaults to "/mapper"
                        which matches api_server.py. Set to "" for fastapi_app.py.
        timeout:        HTTP timeout in seconds (default 300 — mapper LLM calls are slow).
    """

    def __init__(
        self,
        mapper_api_url: Optional[str] = None,
        mapper_api_key: Optional[str] = None,
        url_prefix: Optional[str] = None,
        timeout: float = 300.0,
    ):
        base = (
            mapper_api_url
            or os.getenv("MAPPER_API_URL", "http://localhost:8000")
        ).rstrip("/")

        # Default prefix is /mapper — matches api_server.py which registers
        # all routes as /mapper/extract, /mapper/fill, etc.
        # MAPPER_URL_PREFIX env var allows override without code change.
        prefix = (
            url_prefix
            if url_prefix is not None
            else os.getenv("MAPPER_URL_PREFIX", "/mapper")
        )
        self._api_url = base + prefix

        self._api_key = mapper_api_key or os.getenv("MAPPER_API_KEY", "")
        self._timeout = timeout
        self._client = None  # lazy-initialised in _get_client()

    # ------------------------------------------------------------------
    # PDFFillerInterface implementation
    # ------------------------------------------------------------------

    def prepare_document(self, pdf_path: str, investor_type: str) -> str:
        """
        Step 3 — make_embed_file.

        Calls the mapper's Extract + Map + Embed pipeline on the blank PDF.
        Triggered when the investor selects their type (runs in a background thread).

        Args:
            pdf_path:      Local path or S3 key to the blank PDF.
            investor_type: e.g. "Individual", "Corporation" — passed to the mapper
                           so it can apply investor-type-specific mapping rules
                           (e.g. SSN exclusion for entities, EIN exclusion for
                           individuals).

        Returns:
            doc_id — the embedded_pdf path returned by the mapper, used in
            check_document_ready() and fill_document().
        """
        client = self._get_client()

        # Pass investor_type via session_id label so the mapper can log it.
        # NOTE: mapper SDK make_embed_file() only accepts pdf_path + session_id.
        # investor_type is encoded in session_id for traceability.  When the
        # mapper SDK gains a native investor_type param, switch to that.
        session_label = f"chatbot-{investor_type.lower().replace(' ', '_')}"

        logger.debug(
            "MapperPDFFiller.prepare_document: pdf=%s investor_type=%s",
            pdf_path,
            investor_type,
        )

        result = client.mapper.make_embed_file(
            pdf_path=pdf_path,
            session_id=session_label,
        )

        # The mapper wraps its response as:
        #   OperationResponse { success, data: { operation, outputs: { embedded_pdf, ... } } }
        # Extract the embedded_pdf path for use as doc_id in subsequent steps.
        data = result.get("data", result)  # handle both flat and wrapped responses
        outputs = data.get("outputs", {})
        doc_id = (
            outputs.get("embedded_pdf")
            or data.get("embedded_pdf")
            or data.get("embedded_pdf_path")
        )

        if not doc_id:
            # Fallback: use the input pdf_path and log a warning so it's visible.
            logger.warning(
                "MapperPDFFiller.prepare_document: could not extract embedded_pdf "
                "from mapper response — falling back to input pdf_path. "
                "Response keys: %s",
                list(data.keys()),
            )
            doc_id = pdf_path

        logger.debug("MapperPDFFiller.prepare_document: doc_id=%s", doc_id)
        return doc_id

    def check_document_ready(self, doc_id: str) -> bool:
        """
        Step 5 — check_embed_file.

        Polls whether the mapper has finished embedding metadata into the PDF.
        Called up to max_poll_attempts times by PDFWorkflowManager.

        The mapper check_embed_file operation returns:
            { "exists": True/False, "status": "success"/"not_found"/"error", ... }

        Args:
            doc_id: The embedded PDF path returned by prepare_document().

        Returns:
            True when the embedded PDF file exists and is ready to fill.
        """
        client = self._get_client()
        result = client.mapper.check_embed_file(pdf_path=doc_id)

        # Unwrap OperationResponse wrapper if present
        data = result.get("data", result)

        # Primary signal: "exists" key from handle_check_embed_file_operation
        if "exists" in data:
            return bool(data["exists"])

        # Secondary: status string
        status = data.get("status", "").lower()
        if status in ("success", "ready", "complete", "done"):
            return True
        if status in ("not_found", "error"):
            return False

        # Tertiary: legacy keys from other mapper versions
        return bool(data.get("has_metadata") or data.get("ready"))

    def fill_document(self, doc_id: str, data_flat: dict) -> Any:
        """
        Step 6 — fill.

        Sends the collected investor data to fill the prepared (embedded) PDF.

        Args:
            doc_id:    Embedded PDF path returned by prepare_document().
            data_flat: The final_output_flat dict from the chatbot session.

        Returns:
            Dict with fill result from the mapper (includes filled_pdf path,
            filled_presigned_url if S3, etc.).
        """
        client = self._get_client()
        result = client.mapper.fill(
            pdf_path=doc_id,
            data=data_flat,
        )
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_client(self):
        """Lazy-init the PDFMapperClient (avoids import error if sdk not installed)."""
        if self._client is None:
            try:
                from pdf_autofiller import PDFMapperClient  # mapper SDK
            except ImportError:
                raise ImportError(
                    "pdf-autofiller-sdk is required for MapperPDFFiller.\n"
                    "Install it with:\n"
                    "  pip install pdf-autofiller-sdk\n"
                    "Or install locally from the rv1 repo:\n"
                    "  pip install -e path/to/pdf-autofillr-rv1/sdks/python/"
                )
            self._client = PDFMapperClient(
                api_key=self._api_key,
                base_url=self._api_url,
                timeout=self._timeout,
            )
        return self._client
