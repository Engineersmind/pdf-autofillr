# chatbot/pdf/interface.py
"""
PDFFillerInterface — abstract class for PDF filling integrations.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class PDFFillerInterface(ABC):
    """
    Implement this interface to connect any PDF filling service.

    The SDK provides all orchestration (polling, retry, threading, logging).
    You only implement the three steps below.

    Example::

        class MyPDFService(PDFFillerInterface):
            def prepare_document(self, pdf_path, investor_type):
                r = requests.post('https://api.my-pdf.com/prepare', json={...})
                return r.json()['doc_id']

            def check_document_ready(self, doc_id):
                r = requests.get(f'https://api.my-pdf.com/status/{doc_id}')
                return r.json()['status'] == 'ready'

            def fill_document(self, doc_id, data_flat):
                r = requests.post(f'https://api.my-pdf.com/fill/{doc_id}', json={...})
                return r.json()['download_url']
    """

    @abstractmethod
    def prepare_document(self, pdf_path: str, investor_type: str) -> str:
        """
        Prepare the PDF for filling (field mapping, embed, etc.).

        Called when investor type is selected.

        Args:
            pdf_path:      Local path or S3 key to the blank PDF.
            investor_type: Selected investor type (e.g. "Individual").

        Returns:
            doc_id — any string identifier for this prepared document.
            Equivalent to original Step 3 (make_embed_file).
        """

    @abstractmethod
    def check_document_ready(self, doc_id: str) -> bool:
        """
        Return True when the document is ready to be filled.

        The workflow manager handles polling — just return bool.
        Called up to ``max_poll_attempts`` times (default: 15).

        Equivalent to original Step 5 (check_embed_file).
        """

    @abstractmethod
    def fill_document(self, doc_id: str, data_flat: dict) -> Any:
        """
        Fill the prepared document with collected investor data.

        Called after conversation completes.

        Args:
            doc_id:    Identifier returned by ``prepare_document``.
            data_flat: The ``final_output_flat`` dict.

        Returns:
            Whatever your service returns — a URL, a local path, bytes, etc.
            Equivalent to original Step 6 (fill_pdf).
        """

    def get_result(self, doc_id: str) -> Any:
        """
        Optional: retrieve result after async fill completes.
        Override if your service stores results separately.
        """
        return None
