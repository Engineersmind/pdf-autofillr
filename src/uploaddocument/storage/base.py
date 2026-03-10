"""StorageBackend — abstract class all storage implementations extend."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Optional


class StorageBackend(ABC):
    """Abstract interface for all storage backends."""

    # ── Extraction results ─────────────────────────────────────────────
    @abstractmethod
    def get_extraction_result(self, user_id: str, session_id: str) -> Optional[dict]: ...

    @abstractmethod
    def save_extraction_result(self, user_id: str, session_id: str, data: dict) -> bool: ...

    @abstractmethod
    def get_extraction_result_flat(self, user_id: str, session_id: str) -> Optional[dict]: ...

    @abstractmethod
    def save_extraction_result_flat(self, user_id: str, session_id: str, data: dict) -> bool: ...

    # ── PDF workflow logs ──────────────────────────────────────────────
    @abstractmethod
    def get_pdf_filling_logs(self, user_id: str, session_id: str) -> Optional[dict]: ...

    @abstractmethod
    def save_pdf_filling_logs(self, user_id: str, session_id: str, data: dict) -> bool: ...

    # ── Execution logs ─────────────────────────────────────────────────
    @abstractmethod
    def save_execution_logs(self, user_id: str, session_id: str, data: dict) -> bool: ...

    # ── Session state ──────────────────────────────────────────────────
    @abstractmethod
    def get_session_state(self, user_id: str, session_id: str) -> Optional[dict]: ...

    @abstractmethod
    def save_session_state(self, user_id: str, session_id: str, state: dict) -> bool: ...

    # ── Utility ────────────────────────────────────────────────────────
    @abstractmethod
    def list_user_sessions(self, user_id: str) -> List[str]: ...

    @abstractmethod
    def delete_session(self, user_id: str, session_id: str) -> bool: ...

    # ── Config loaders ─────────────────────────────────────────────────
    @abstractmethod
    def load_config(self, filename: str) -> dict: ...
