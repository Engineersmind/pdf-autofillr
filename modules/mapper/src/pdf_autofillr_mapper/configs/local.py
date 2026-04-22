"""
Local filesystem storage configuration.

Mirrors the prod bucket structure under a local data root.
Path generation is delegated to StorageConfig + PathResolver.
This class handles local file copy operations (download/upload/exists).
"""

import os
import shutil
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from .base import BaseStorageConfig

logger = logging.getLogger(__name__)


class LocalStorageConfig(BaseStorageConfig):
    """Local filesystem storage implementation."""

    def __init__(self, env: str = None, developer_id: str = None, base_dir: str = None):
        super().__init__(source_type="local")

        # Override MAPPER_DATA_PATH if base_dir provided (mainly for tests)
        if base_dir:
            os.environ.setdefault("MAPPER_DATA_PATH", base_dir)

        # Path resolution delegated to StorageConfig
        from pdf_autofillr_mapper.storage.storage_config import StorageConfig
        self._sc = StorageConfig(env=env, developer_id=developer_id)
        self.env_folder  = self._sc.env_folder
        self.user_type   = self._sc.user_type
        self.base_dir    = self._sc._root

        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    # ── File transfer ─────────────────────────────────────────────────────────

    def parse_path(self, file_path: str) -> Dict[str, str]:
        abs_path = os.path.abspath(file_path)
        return {
            "type": "local",
            "path": abs_path,
            "directory": os.path.dirname(abs_path),
            "filename": os.path.basename(abs_path),
        }

    def download_file(self, source_path: str, local_path: str) -> str:
        """For local storage, download = copy."""
        source_abs = os.path.abspath(source_path)
        dest_abs = os.path.abspath(local_path)
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
        shutil.copy2(source_abs, dest_abs)
        logger.info(f"Copied {source_abs} to {dest_abs}")
        return dest_abs

    def upload_file(self, local_path: str, destination_path: str) -> str:
        """For local storage, upload = copy."""
        source_abs = os.path.abspath(local_path)
        dest_abs = os.path.abspath(destination_path)
        if source_abs == dest_abs:
            return dest_abs
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
        shutil.copy2(source_abs, dest_abs)
        logger.info(f"Copied {source_abs} to {dest_abs}")
        return dest_abs

    def file_exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)

    # ── Path generation — delegates to StorageConfig + PathResolver ───────────

    def get_path_resolver(self):
        from pdf_autofillr_mapper.storage.paths.resolver import PathResolver
        return PathResolver(self._sc)

    def get_complete_file_config(
        self,
        user_id: int,
        session_id: str,
        pdf_doc_id: int,
    ) -> Dict[str, Any]:
        """
        Return all pipeline paths for a job, using the prod folder structure locally.
        All paths are absolute local filesystem paths.
        """
        pr = self.get_path_resolver()
        uid, sid, pid = str(user_id), str(session_id), str(pdf_doc_id)
        return {
            "source_type": "local",
            "input_pdf":              pr.remote_input_pdf(uid, sid, pid),
            "global_json":            pr.remote_global_json(),
            "input_json":             pr.remote_input_json(uid, sid),
            "extracted_json":         pr.remote_extracted(uid, sid, pid),
            "mapped_json":            pr.remote_mapped(uid, sid, pid),
            "radio_groups_json":      pr.remote_radio(uid, sid, pid),
            "headers_with_fields":    pr.remote_headers_with_fields(uid, sid, pid),
            "final_form_fields":      pr.remote_final_form_fields(uid, sid, pid),
            "java_mapping":           pr.remote_java_mapping(uid, sid, pid),
            "embedded_pdf":           pr.remote_embedded(uid, sid, pid),
            "filled_pdf":             pr.remote_filled(uid, sid, pid),
            "header_file":            pr.remote_header_file(uid, sid, pid),
            "section_file":           pr.remote_section_file(uid, sid, pid),
            "rag_predictions":        pr.remote_rag_predictions(uid, sid, pid),
            "llm_predictions":        pr.remote_llm_predictions(uid, sid, pid),
            "final_predictions":      pr.remote_final_predictions(uid, sid, pid),
            "cache_registry":         pr.remote_cache_registry(),
            "filled_pdf_store":       pr.remote_filled_pdf_store(uid, sid, pid),
        }
