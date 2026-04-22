"""
AWS S3 storage configuration.

Path generation is fully delegated to StorageConfig + PathResolver.
This class handles S3 file transfer operations (download/upload/exists).
"""

import os
import logging
from typing import Dict, Any, Optional
from .base import BaseStorageConfig

logger = logging.getLogger(__name__)


class AWSStorageConfig(BaseStorageConfig):
    """AWS S3 storage implementation."""

    def __init__(self, env: str = None, developer_id: str = None):
        super().__init__(source_type="aws")
        self.s3_client = None
        self.rag_api_url = os.getenv('RAG_API_URL', '')
        self.rag_api_key = os.getenv('RAG_API_KEY', '')

        # Path resolution delegated to StorageConfig
        from pdf_autofillr_mapper.storage.storage_config import StorageConfig
        self._sc = StorageConfig(env=env, developer_id=developer_id)
        self.env_folder  = self._sc.env_folder
        self.user_type   = self._sc.user_type

    def _get_s3_client(self):
        if self.s3_client is None:
            from pdf_autofillr_mapper.clients.s3_client import S3Client
            self.s3_client = S3Client()
        return self.s3_client

    # ── File transfer ─────────────────────────────────────────────────────────

    def parse_path(self, file_path: str) -> Dict[str, str]:
        if not file_path.startswith("s3://"):
            raise ValueError(f"Invalid S3 path: {file_path}")
        path_without_prefix = file_path[5:]
        parts = path_without_prefix.split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        filename = key.split('/')[-1] if key else ""
        return {"type": "s3", "bucket": bucket, "key": key,
                "path": file_path, "filename": filename}

    def download_file(self, source_path: str, local_path: str) -> str:
        s3_client = self._get_s3_client()
        s3_client.download_file_from_s3(source_path, local_path)
        logger.info(f"Downloaded {source_path} to {local_path}")
        return local_path

    def upload_file(self, local_path: str, destination_path: str) -> str:
        s3_client = self._get_s3_client()
        s3_client.upload_file_to_s3(local_path, destination_path)
        logger.info(f"Uploaded {local_path} to {destination_path}")
        return destination_path

    def file_exists(self, file_path: str) -> bool:
        return self._get_s3_client().object_exists(file_path)

    def generate_output_path(self, input_path: str, suffix: str, extension: str = None) -> str:
        base = input_path.rsplit('.', 1)[0] if '.' in input_path.split('/')[-1] else input_path
        ext = f".{extension.lstrip('.')}" if extension else ('.' + input_path.rsplit('.', 1)[-1] if '.' in input_path else '')
        return f"{base}{suffix}{ext}"

    def get_storage_config(self, file_path: str) -> dict:
        parsed = self.parse_path(file_path)
        return {"type": "s3", "bucket": parsed["bucket"], "key": parsed["key"], "path": file_path}

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
        Return all pipeline paths for a job, using the prod bucket structure.
        All paths are S3 URIs.
        """
        pr = self.get_path_resolver()
        uid, sid, pid = str(user_id), str(session_id), str(pdf_doc_id)
        return {
            "source_type": "aws",
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
