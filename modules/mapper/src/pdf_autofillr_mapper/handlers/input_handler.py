"""
Input File Handler - downloads input files from source storage to local temp.

Delegates the actual transfer to the storage backend stored on config
(JobContext, AWSStorageConfig, LocalStorageConfig, etc.).
No if/elif routing on source_type — the backend handles that.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InputFileHandler:
    """
    Downloads files from any storage backend to the local processing directory.

    The storage backend (S3, Azure, GCS, local copy) is encapsulated in
    config.download_file(). This handler manages which logical file maps
    to which local path.
    """

    def __init__(self, config):
        self.config = config
        self.source_type = config.source_type

    def get_input(
        self,
        file_type: str,
        source_path: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Return local path for a file type, downloading from source if needed.

        Args:
            file_type:   Logical name, e.g. 'input_pdf', 'extracted_json'
            source_path: Explicit remote path (overrides config lookup)
            local_path:  Explicit local destination (overrides config lookup)

        Returns:
            Local path where the file is available, or None on failure.
        """
        if not local_path:
            local_path = getattr(self.config, f'local_{file_type}', None)

        if not local_path:
            logger.warning(f"No local path configured for '{file_type}'")
            return None

        # Already present locally — skip download
        if os.path.exists(local_path):
            logger.debug(f"File already local: {local_path}")
            return local_path

        # Resolve source path from config attributes (dest_ / s3_ / blob_ / gcs_ / source_)
        if not source_path:
            source_path = (
                getattr(self.config, f's3_{file_type}', None)
                or getattr(self.config, f'blob_{file_type}', None)
                or getattr(self.config, f'gcs_{file_type}', None)
                or getattr(self.config, f'source_{file_type}', None)
            )

        if not source_path:
            logger.warning(f"No source path configured for '{file_type}'")
            return None

        return self.download_input(source_path, local_path)

    def download_input(self, source_path: str, local_path: str) -> Optional[str]:
        """Download a file from source storage to a local path."""
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            result = self.config.download_file(source_path, local_path)
            logger.info(f"Downloaded: {source_path} → {local_path}")
            return result
        except Exception as e:
            logger.error(f"Download failed [{source_path}]: {e}", exc_info=True)
            return None

    def download_multiple_inputs(self, file_mappings: dict) -> dict:
        """Download multiple files. file_mappings: {file_type: source_path}"""
        results = {}
        for file_type, source_path in file_mappings.items():
            local_path = getattr(self.config, f'local_{file_type}', None)
            if local_path:
                downloaded = self.download_input(source_path, local_path)
                if downloaded:
                    results[file_type] = downloaded
        return results


def create_input_handler(config) -> InputFileHandler:
    return InputFileHandler(config)
