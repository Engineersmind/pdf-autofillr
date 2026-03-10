"""
TelemetryCollector — zero-overhead when disabled, async HTTP batching when enabled.

Privacy guarantee:
  - Field VALUES are NEVER included in any event.
  - user_id and session_id are one-way SHA-256 hashed before transmission.
  - Only metadata (counts, latencies, field keys, document format) is sent.

Modes:
  local        → prints events to console, nothing leaves the process
  self_hosted  → POSTs event batches to your own endpoint via requests
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from uploaddocument.telemetry.config import TelemetryConfig
from uploaddocument.telemetry.document_context import DocumentContext


def _hash_id(value: str) -> str:
    """One-way SHA-256 hash — user/session IDs are never sent in plain text."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


class TelemetryCollector:
    """
    Collects and ships telemetry events for the Upload Document SDK.

    When disabled (default) every call is a no-op with zero overhead.
    When enabled in local mode events print to stdout only.
    When enabled in self_hosted mode events are batched and POSTed
    to your endpoint in a background thread.
    """

    def __init__(
        self,
        config: Optional[TelemetryConfig] = None,
        document_context: Optional[DocumentContext] = None,
    ):
        self.config = config
        self.document_context = document_context
        self._enabled = bool(config and config.enabled)
        self._mode = config.mode if config else "local"
        self._endpoint = config.endpoint if config else ""
        self._api_key = config.sdk_api_key if config else ""
        self._batch_size = config.batch_size if config else 10
        self._debug = os.getenv("UPLOAD_DOC_DEBUG_LOGGING", "").lower() == "true"

        self._queue: deque = deque()
        self._lock = threading.Lock()

        if self._enabled and self._mode == "self_hosted" and self._endpoint:
            self._start_flush_thread(
                config.flush_interval_seconds if config else 30
            )

    # ── Public tracking methods ────────────────────────────────────────

    def track_extraction(
        self,
        user_id: str,
        session_id: str,
        document_format: str,
        fields_extracted: int,
        fields_in_schema: int,
        latency_seconds: float,
        method: str,                    # "llm" or "fallback"
        success: bool = True,
    ) -> None:
        """Track one document extraction attempt."""
        if not self._enabled:
            return
        payload = {
            "document_format": document_format,
            "fields_extracted": fields_extracted,
            "fields_in_schema": fields_in_schema,
            "completion_pct": round(fields_extracted / max(fields_in_schema, 1) * 100, 1),
            "latency_ms": int(latency_seconds * 1000),
            "method": method,
            "success": success,
        }
        self._emit("extraction_complete", user_id, session_id, payload)

    def track_pdf_fill(
        self,
        user_id: str,
        session_id: str,
        doc_id: str,
        success: bool,
        duration_seconds: float,
        error: Optional[str] = None,
    ) -> None:
        """Track one PDF fill attempt (Steps 3 → 5 → 6)."""
        if not self._enabled:
            return
        payload = {
            "doc_id_hash": _hash_id(doc_id) if doc_id else None,
            "success": success,
            "duration_ms": int(duration_seconds * 1000),
        }
        if error:
            payload["error_type"] = type(error).__name__ if not isinstance(error, str) else "Error"
        self._emit("pdf_fill_complete", user_id, session_id, payload)

    def track_error(
        self,
        user_id: str,
        session_id: str,
        error_type: str,
        stage: str,                    # "read", "extract", "embed", "fill"
    ) -> None:
        """Track a pipeline error without leaking PII."""
        if not self._enabled:
            return
        self._emit("pipeline_error", user_id, session_id, {
            "error_type": error_type,
            "stage": stage,
        })

    def track_document_processed(
        self,
        user_id: str,
        session_id: str,
        document_format: str,
        total_duration_seconds: float,
        pdf_filled: bool,
        success: bool,
    ) -> None:
        """
        Track end-to-end completion of the full pipeline.
        This is the summary event — always fired at the end of process_document().
        """
        if not self._enabled:
            return
        self._emit("document_processed", user_id, session_id, {
            "document_format": document_format,
            "total_duration_ms": int(total_duration_seconds * 1000),
            "pdf_filled": pdf_filled,
            "success": success,
        })

    # ── Internal ───────────────────────────────────────────────────────

    def _emit(self, event_type: str, user_id: str, session_id: str, payload: dict) -> None:
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id_hash": _hash_id(user_id) if user_id else None,
            "session_id_hash": _hash_id(session_id) if session_id else None,
            **payload,
        }
        if self.document_context:
            event.update(self.document_context.to_dict())

        if self._debug or self._mode == "local":
            print(f"[TELEMETRY] {event_type}: {payload}")

        if self._enabled and self._mode == "self_hosted" and self._endpoint:
            with self._lock:
                self._queue.append(event)
                if len(self._queue) >= self._batch_size:
                    self._flush_nowait()

    def _flush_nowait(self) -> None:
        if not self._queue:
            return
        with self._lock:
            batch = list(self._queue)
            self._queue.clear()
        threading.Thread(target=self._send_batch, args=(batch,), daemon=True).start()

    def _send_batch(self, batch: list) -> None:
        try:
            import requests
            headers = {
                "Content-Type": "application/json",
                "X-SDK-Key": self._api_key,
            }
            resp = requests.post(
                self._endpoint,
                data=json.dumps({"events": batch}, default=str),
                headers=headers,
                timeout=5,
            )
            if self._debug:
                print(f"[TELEMETRY] Sent {len(batch)} events → HTTP {resp.status_code}")
        except Exception as e:
            if self._debug:
                print(f"[TELEMETRY] Send error: {e}")

    def _start_flush_thread(self, interval_seconds: int) -> None:
        def _loop():
            while True:
                time.sleep(interval_seconds)
                try:
                    self._flush_nowait()
                except Exception:
                    pass
        threading.Thread(target=_loop, daemon=True).start()