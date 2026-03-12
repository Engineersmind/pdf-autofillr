# chatbot/config/settings.py
"""SDK runtime settings — reads from environment variables or .env file."""
from __future__ import annotations

import os
import warnings


class Settings:
    """SDK runtime settings. All values readable from environment variables."""

    def __init__(self, validate: bool = True):
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

        # PDF filler mode: "none" | "mapper" | "managed" | "custom"
        self.pdf_filler_mode: str = os.getenv("chatbot_PDF_FILLER", "none").lower()
        self.pdf_path: str = os.getenv("chatbot_PDF_PATH", "")

        # Mapper connection (used when pdf_filler_mode == "mapper")
        self.mapper_api_url: str = os.getenv("MAPPER_API_URL", "http://localhost:8000")
        self.mapper_api_key: str = os.getenv("MAPPER_API_KEY", "")

        if validate:
            self._validate()

    # ------------------------------------------------------------------
    # Validation — emit clear warnings for missing required env vars
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        errors = []
        warns = []

        # ── Core ───────────────────────────────────────────────────────
        if not self.openai_api_key:
            errors.append(
                "OPENAI_API_KEY is not set.\n"
                "  Export it: export OPENAI_API_KEY=sk-..."
            )

        # ── Storage: S3 ────────────────────────────────────────────────
        if self.storage_type == "s3":
            missing_s3 = []
            if not os.getenv("AWS_OUTPUT_BUCKET"):
                missing_s3.append("AWS_OUTPUT_BUCKET")
            if not os.getenv("AWS_CONFIG_BUCKET"):
                missing_s3.append("AWS_CONFIG_BUCKET")
            has_creds = (
                os.getenv("AWS_ACCESS_KEY_ID")
                or os.getenv("AWS_PROFILE")
                or os.getenv("AWS_ROLE_ARN")
                or os.getenv("AWS_EXECUTION_ENV")
                or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
            )
            if not has_creds:
                missing_s3.append(
                    "AWS credentials (AWS_ACCESS_KEY_ID+AWS_SECRET_ACCESS_KEY, "
                    "AWS_PROFILE, or IAM role)"
                )
            if missing_s3:
                errors.append(
                    "chatbot_STORAGE=s3 is set but the following are missing:\n"
                    + "\n".join(f"  - {v}" for v in missing_s3)
                    + "\n  See .env.example for details."
                )

        # ── PDF filler ─────────────────────────────────────────────────
        if self.pdf_filler_mode != "none":
            if not self.pdf_path:
                errors.append(
                    "chatbot_PDF_FILLER is set but chatbot_PDF_PATH is missing.\n"
                    "  Set the path to the blank PDF that should be filled:\n"
                    "  chatbot_PDF_PATH=/path/to/blank_form.pdf   (local)\n"
                    "  chatbot_PDF_PATH=s3://your-bucket/blank_form.pdf  (S3)"
                )

            if self.pdf_filler_mode == "mapper":
                if not self.mapper_api_url:
                    warns.append(
                        "chatbot_PDF_FILLER=mapper but MAPPER_API_URL is not set.\n"
                        "  Defaulting to http://localhost:8000.\n"
                        "  Set MAPPER_API_URL to your mapper API server URL."
                    )
                if not self.mapper_api_key:
                    warns.append(
                        "MAPPER_API_KEY is not set — mapper API calls will have no auth header.\n"
                        "  Set MAPPER_API_KEY if your mapper server requires authentication."
                    )

            elif self.pdf_filler_mode == "managed":
                managed_required = [
                    "AUTH0_DOMAIN",
                    "AUTH0_CLIENT_ID",
                    "AUTH0_CLIENT_SECRET",
                    "AUTH0_AUDIENCE",
                    "FILL_PDF_LAMBDA_URL",
                    "PDF_API_KEY",
                ]
                missing_managed = [v for v in managed_required if not os.getenv(v)]
                if missing_managed:
                    errors.append(
                        "chatbot_PDF_FILLER=managed but the following are missing:\n"
                        + "\n".join(f"  - {v}" for v in missing_managed)
                        + "\n  These are required for the managed Auth0 PDF Lambda service."
                    )

        # ── Telemetry ──────────────────────────────────────────────────
        if self.telemetry_enabled:
            if self.telemetry_mode == "local" and not self.telemetry_endpoint:
                warns.append(
                    "chatbot_TELEMETRY=true + chatbot_TELEMETRY_MODE=local but "
                    "chatbot_TELEMETRY_ENDPOINT is not set.\n"
                    "  Events will be queued but never sent.\n"
                    "  Set chatbot_TELEMETRY_ENDPOINT=http://localhost:9000/events"
                )
            elif self.telemetry_mode in ("self_hosted", "managed") and not self.telemetry_endpoint:
                errors.append(
                    f"chatbot_TELEMETRY=true + chatbot_TELEMETRY_MODE={self.telemetry_mode} "
                    "but chatbot_TELEMETRY_ENDPOINT is not set."
                )

        # ── Emit ───────────────────────────────────────────────────────
        for w in warns:
            warnings.warn(f"[chatbot-sdk] {w}", stacklevel=3)

        if errors:
            raise EnvironmentError(
                "\n\n[chatbot-sdk] Configuration errors:\n\n"
                + "\n\n".join(f"  X {e}" for e in errors)
                + "\n\nFix the above and restart. See .env.example for all options.\n"
            )
