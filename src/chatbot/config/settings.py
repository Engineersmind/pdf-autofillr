# chatbot/config/settings.py
"""SDK runtime settings — reads from environment variables or .env file."""
from __future__ import annotations

import os


class Settings:
    """SDK runtime settings. All values readable from environment variables."""

    def __init__(self):
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.storage_type: str = os.getenv("chatbot_STORAGE", "local")
        self.data_path: str = os.getenv("chatbot_DATA_PATH", "./chatbot_data")
        self.config_path: str = os.getenv("chatbot_CONFIG_PATH", "./configs")
        self.bot_name: str = os.getenv("chatbot_BOT_NAME", "Bot")
        self.greeting: str = os.getenv(
            "chatbot_GREETING",
            "Hi! I am here to help you fill out your investment documents.",
        )
        self.pdf_poll_interval: int = int(os.getenv("chatbot_PDF_POLL_INTERVAL", "10"))
        self.pdf_poll_timeout: int = int(os.getenv("chatbot_PDF_POLL_TIMEOUT", "150"))
        self.pdf_max_retries: int = int(os.getenv("chatbot_PDF_MAX_RETRIES", "3"))
        self.telemetry_enabled: bool = os.getenv("chatbot_TELEMETRY", "false").lower() == "true"
        self.telemetry_mode: str = os.getenv("chatbot_TELEMETRY_MODE", "local")
        self.telemetry_endpoint: str = os.getenv("chatbot_TELEMETRY_ENDPOINT", "")
        self.sdk_api_key: str = os.getenv("chatbot_SDK_API_KEY", "")
        self.rate_limit_enabled: bool = os.getenv("chatbot_RATE_LIMIT_ENABLED", "false").lower() == "true"
        self.debug_logging: bool = os.getenv("chatbot_DEBUG_LOGGING", "true").lower() == "true"
        self.log_level: str = os.getenv("chatbot_LOG_LEVEL", "INFO")