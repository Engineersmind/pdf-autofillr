"""LocalStorage — filesystem backend. Ideal for development."""
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from typing import Any, List, Optional
from uploaddocument.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """
    Stores all data as JSON files on the local filesystem.

    Args:
        data_path:   Root directory for session/extraction data.
        config_path: Directory containing form_keys.json (read-only).
    """

    def __init__(self, data_path: str = "./uploaddoc_data", config_path: str = "./configs"):
        self.data_path = Path(data_path)
        self.config_path = Path(config_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, user_id: str, session_id: str) -> Path:
        p = self.data_path / user_id / "sessions" / session_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _read(self, path: Path) -> Optional[Any]:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path: Path, data: Any) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            print(f"❌ LocalStorage write error {path}: {e}")
            return False

    def get_extraction_result(self, user_id, session_id):
        return self._read(self._session_dir(user_id, session_id) / "extraction_result.json")

    def save_extraction_result(self, user_id, session_id, data):
        return self._write(self._session_dir(user_id, session_id) / "extraction_result.json", data)

    def get_extraction_result_flat(self, user_id, session_id):
        return self._read(self._session_dir(user_id, session_id) / "extraction_result_flat.json")

    def save_extraction_result_flat(self, user_id, session_id, data):
        return self._write(self._session_dir(user_id, session_id) / "extraction_result_flat.json", data)

    def get_pdf_filling_logs(self, user_id, session_id):
        return self._read(self._session_dir(user_id, session_id) / "calling_filling_logs.json")

    def save_pdf_filling_logs(self, user_id, session_id, data):
        return self._write(self._session_dir(user_id, session_id) / "calling_filling_logs.json", data)

    def save_execution_logs(self, user_id, session_id, data):
        return self._write(self._session_dir(user_id, session_id) / "execution_logs.json", data)

    def get_session_state(self, user_id, session_id):
        return self._read(self._session_dir(user_id, session_id) / "session_state.json")

    def save_session_state(self, user_id, session_id, state):
        return self._write(self._session_dir(user_id, session_id) / "session_state.json", state)

    def list_user_sessions(self, user_id):
        sessions_dir = self.data_path / user_id / "sessions"
        if not sessions_dir.exists():
            return []
        return [p.name for p in sessions_dir.iterdir() if p.is_dir()]

    def delete_session(self, user_id, session_id):
        session_dir = self.data_path / user_id / "sessions" / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
        return True

    def load_config(self, filename: str) -> dict:
        path = self.config_path / filename
        data = self._read(path)
        if data is None:
            raise FileNotFoundError(f"Config file not found: {path}")
        return data
