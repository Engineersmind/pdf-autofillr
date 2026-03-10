# finform/pdf/workflow.py
"""
PDFWorkflowManager — orchestration only.
Handles polling, retry, threading, and step logging.
The developer's PDFFillerInterface is called inside each step.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Optional

from uploaddocument.pdf.interface import PDFFillerInterface
from uploaddocument.storage.base import StorageBackend


class PDFWorkflowManager:
    """
    Manages the async PDF fill workflow.

    Steps:
        1. prepare_document   — called on investor type selection
        2. poll readiness     — polls check_document_ready up to max_poll_attempts
        3. fill_document      — called after conversation completes
    """

    def __init__(
        self,
        filler: PDFFillerInterface,
        storage: StorageBackend,
        settings=None,
    ):
        self.filler = filler
        self.storage = storage
        self.poll_interval = getattr(settings, "pdf_poll_interval", 10)
        self.poll_timeout = getattr(settings, "pdf_poll_timeout", 150)
        self.max_retries = getattr(settings, "pdf_max_retries", 3)
        self.max_poll_attempts = self.poll_timeout // max(self.poll_interval, 1)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def trigger_prepare_async(
        self,
        user_id: str,
        session_id: str,
        pdf_path: str,
        investor_type: str,
    ) -> None:
        """Trigger document preparation in a background thread."""
        t = threading.Thread(
            target=self._prepare_worker,
            args=(user_id, session_id, pdf_path, investor_type),
            daemon=True,
        )
        t.start()

    def trigger_async(
        self,
        user_id: str,
        session_id: str,
        pdf_path: str,
        investor_type: str,
        data_flat: dict,
    ) -> None:
        """Trigger the full fill workflow in a background thread."""
        t = threading.Thread(
            target=self._fill_worker,
            args=(user_id, session_id, pdf_path, investor_type, data_flat),
            daemon=True,
        )
        t.start()

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    def _prepare_worker(self, user_id, session_id, pdf_path, investor_type):
        try:
            doc_id = self.filler.prepare_document(pdf_path, investor_type)
            self._log_step(user_id, session_id, "prepare", success=True, doc_id=doc_id)
            # Persist doc_id back to session
            session = self.storage.get_session_state(user_id, session_id) or {}
            session["pdf_doc_id"] = doc_id
            self.storage.save_session_state(user_id, session_id, session)
        except Exception as e:
            self._log_step(user_id, session_id, "prepare", success=False, error=str(e))

    def _fill_worker(self, user_id, session_id, pdf_path, investor_type, data_flat):
        try:
            # Get doc_id (prepared earlier, or prepare now)
            session = self.storage.get_session_state(user_id, session_id) or {}
            doc_id = session.get("pdf_doc_id")

            if not doc_id:
                doc_id = self.filler.prepare_document(pdf_path, investor_type)
                session["pdf_doc_id"] = doc_id
                self.storage.save_session_state(user_id, session_id, session)
                self._log_step(user_id, session_id, "prepare", success=True, doc_id=doc_id)

            # Poll for readiness
            ready = self._poll_ready(user_id, session_id, doc_id)

            if not ready:
                # Retry prepare once
                doc_id = self.filler.prepare_document(pdf_path, investor_type)
                session["pdf_doc_id"] = doc_id
                self.storage.save_session_state(user_id, session_id, session)
                time.sleep(180)
                ready = self._poll_ready(user_id, session_id, doc_id)

            if not ready:
                self._log_step(user_id, session_id, "check", success=False, error="Timeout waiting for document")
                return

            # Fill with retries
            result = None
            for attempt in range(self.max_retries):
                try:
                    result = self.filler.fill_document(doc_id, data_flat)
                    if result:
                        break
                except Exception as e:
                    self._log_step(user_id, session_id, "fill", success=False, error=str(e), attempt=attempt)
                    time.sleep(5 * (attempt + 1))

            if result:
                self._log_step(user_id, session_id, "fill", success=True, result=str(result))
                # FIX E: removed the redundant read-then-overwrite of filling logs here.
                # _log_step() already persists the step above — re-reading and re-saving
                # the same data was a no-op that caused an extra unnecessary storage call.

        except Exception as e:
            self._log_step(user_id, session_id, "fill", success=False, error=str(e))

    def _poll_ready(self, user_id, session_id, doc_id) -> bool:
        for attempt in range(self.max_poll_attempts):
            try:
                if self.filler.check_document_ready(doc_id):
                    self._log_step(user_id, session_id, "check", success=True, attempt=attempt)
                    return True
            except Exception:
                pass
            self._log_step(user_id, session_id, "check", success=False, attempt=attempt, ready=False)
            time.sleep(self.poll_interval)
        return False

    # ------------------------------------------------------------------

    def _log_step(self, user_id, session_id, step, **kwargs):
        existing = self.storage.get_pdf_filling_logs(user_id, session_id) or {"steps": []}
        existing.setdefault("steps", []).append({
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        })
        self.storage.save_pdf_filling_logs(user_id, session_id, existing)