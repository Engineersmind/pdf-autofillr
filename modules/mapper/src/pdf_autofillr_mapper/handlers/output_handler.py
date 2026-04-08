"""
Output File Handler - saves output files to source storage.

Delegates the actual transfer to the storage backend stored on config.
No if/elif routing on source_type — the backend handles that.

Destination paths come from config.dest_* attributes (set by JobContext
or the old attribute-bag configs).
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OutputFileHandler:
    """
    Uploads files from local temp to any storage backend.

    The storage backend (S3, Azure, GCS, local copy) is encapsulated in
    config.upload_file(). Destination paths are resolved from config
    attributes in priority order: dest_ > s3_ > blob_ > gcs_.
    """

    def __init__(self, config):
        self.config = config
        self.source_type = config.source_type

    def save_output(
        self,
        local_path: str,
        file_type: str,
        destination_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upload a local file to source storage.

        Args:
            local_path:        Path to the file in /tmp/processing/
            file_type:         Logical name, e.g. 'extracted_json', 'embedded_pdf'
            destination_path:  Explicit remote path (overrides config lookup)

        Returns:
            Destination path where the file was saved, or None on failure.
        """
        if not os.path.exists(local_path):
            logger.warning(f"File not found, skipping save: {local_path}")
            return None

        if not destination_path:
            destination_path = (
                getattr(self.config, f'dest_{file_type}', None)
                or getattr(self.config, f's3_{file_type}', None)
                or getattr(self.config, f'blob_{file_type}', None)
                or getattr(self.config, f'gcs_{file_type}', None)
            )

        if not destination_path:
            logger.warning(f"No destination path for '{file_type}', skipping")
            return None

        try:
            result = self.config.upload_file(local_path, destination_path)
            logger.info(f"Saved: {local_path} → {destination_path}")
            return result
        except Exception as e:
            logger.error(f"Save failed [{local_path}]: {e}", exc_info=True)
            return None

    def save_multiple_outputs(self, file_mappings: dict) -> dict:
        """Save multiple files. file_mappings: {file_type: local_path}"""
        results = {}
        for file_type, local_path in file_mappings.items():
            dest = self.save_output(local_path, file_type)
            if dest:
                results[file_type] = dest
        return results


def create_output_handler(config) -> OutputFileHandler:
    return OutputFileHandler(config)
