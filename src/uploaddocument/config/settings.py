"""SDK runtime settings — reads from environment variables."""
from __future__ import annotations
import os


class Settings:
    """All runtime settings readable from environment variables."""

    def __init__(self):
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.storage_type: str = os.getenv("UPLOAD_DOC_STORAGE", "local")
        self.data_path: str = os.getenv("UPLOAD_DOC_DATA_PATH", "./uploaddoc_data")
        self.config_path: str = os.getenv("UPLOAD_DOC_CONFIG_PATH", "./configs")
        self.static_bucket: str = os.getenv("STATIC_BUCKET", "")
        self.output_bucket: str = os.getenv("OUTPUT_BUCKET", "")
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-1")

        # PDF workflow
        self.pdf_poll_interval: int = int(os.getenv("UPLOAD_DOC_PDF_POLL_INTERVAL", "10"))
        self.pdf_poll_timeout: int = int(os.getenv("UPLOAD_DOC_PDF_POLL_TIMEOUT", "480"))
        self.pdf_max_retries: int = int(os.getenv("UPLOAD_DOC_PDF_MAX_RETRIES", "3"))

        # Telemetry
        self.telemetry_enabled: bool = os.getenv("UPLOAD_DOC_TELEMETRY", "false").lower() == "true"
        self.telemetry_mode: str = os.getenv("UPLOAD_DOC_TELEMETRY_MODE", "local")  # local | self_hosted
        self.telemetry_endpoint: str = os.getenv("UPLOAD_DOC_TELEMETRY_ENDPOINT", "")
        self.telemetry_api_key: str = os.getenv("UPLOAD_DOC_TELEMETRY_API_KEY", "")
        self.telemetry_batch_size: int = int(os.getenv("UPLOAD_DOC_TELEMETRY_BATCH_SIZE", "10"))
        self.telemetry_flush_interval: int = int(os.getenv("UPLOAD_DOC_TELEMETRY_FLUSH_INTERVAL", "30"))

        # Debug
        self.debug_logging: bool = os.getenv("UPLOAD_DOC_DEBUG_LOGGING", "true").lower() == "true"
        self.log_level: str = os.getenv("UPLOAD_DOC_LOG_LEVEL", "INFO")