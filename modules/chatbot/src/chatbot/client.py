# chatbot/client.py
"""
chatbotClient — single entry point for the chatbot SDK.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from chatbot.config.form_config import FormConfig
from chatbot.config.settings import Settings
from chatbot.core.engine import ConversationEngine
from chatbot.core.session import SessionManager
from chatbot.limits.rate_limiter import RateLimiter, RateLimitExceeded
from chatbot.logging.debug_logger import DebugLogger
from chatbot.pdf.interface import PDFFillerInterface
from chatbot.storage.base import StorageBackend
from chatbot.telemetry.collector import TelemetryCollector
from chatbot.telemetry.config import TelemetryConfig
from chatbot.telemetry.document_context import DocumentContext


class chatbotClient:
    """
    Single entry point for the chatbot SDK.

    Example::

        client = chatbotClient(
            openai_api_key="sk-...",
            storage=LocalStorage("./data", "./configs"),
            form_config=FormConfig.from_directory("./configs"),
            pdf_filler=None,
        )

        response, complete, data = client.send_message(
            user_id="investor_123",
            session_id="session_abc",
            message="Hello",
        )
    """

    def __init__(
        self,
        openai_api_key: str,
        storage: StorageBackend,
        form_config: FormConfig,
        pdf_filler: Optional[PDFFillerInterface] = None,
        telemetry: Optional[TelemetryConfig] = None,
        document_context: Optional[DocumentContext] = None,
        rate_limiter: Optional[RateLimiter] = None,
        prompt_builder=None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or Settings()
        self.storage = storage
        self.form_config = form_config
        self.openai_api_key = openai_api_key
        self.rate_limiter = rate_limiter

        # Telemetry
        self.telemetry = TelemetryCollector(
            config=telemetry,
            document_context=document_context,
        )

        # Core session manager
        self.session_manager = SessionManager(storage=storage)

        # Conversation engine
        self.engine = ConversationEngine(
            storage=storage,
            form_config=form_config,
            openai_api_key=openai_api_key,
            pdf_filler=pdf_filler,
            telemetry=self.telemetry,
            prompt_builder=prompt_builder,
            settings=self.settings,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
    ) -> Tuple[str, bool, Optional[dict]]:
        """
        Process one message turn for a user.

        Args:
            user_id:    Unique identifier for the investor.
            session_id: Unique identifier for this conversation session.
            message:    The user's raw text input.

        Returns:
            (response_text, session_complete, session_data_if_complete)

        Raises:
            RateLimitExceeded: If any rate limit is breached.
            ValueError: If user_id or session_id are empty.
        """
        if not user_id or not session_id:
            raise ValueError("user_id and session_id are required")

        if self.rate_limiter:
            self.rate_limiter.check(user_id=user_id, session_id=session_id)

        debug = DebugLogger(user_id=user_id, session_id=session_id)

        response_text, session_complete = self.engine.process_message(
            user_id=user_id,
            session_id=session_id,
            user_input=message.strip(),
            debug=debug,
        )

        # FIX C: increment turn counter AFTER successful processing so
        # messages_per_session limit is actually enforced on the next call.
        if self.rate_limiter:
            self.rate_limiter.increment_message(session_id=session_id)

        # Save debug log
        self.storage.save_debug_conversation(
            user_id, session_id, debug.to_dict()
        )

        data = None
        if session_complete:
            data = self.storage.get_final_output_flat(user_id, session_id)

        return response_text, session_complete, data

    def create_session(
        self,
        user_id: str,
        session_id: str,
        pdf_path: Optional[str] = None,
    ) -> None:
        """
        Explicitly create a session and optionally associate a PDF path.

        If not called, the session is created automatically on the first
        ``send_message`` call.

        Args:
            user_id:    Unique identifier for the investor.
            session_id: Unique identifier for this conversation session.
            pdf_path:   Local filesystem path or S3 key to the blank PDF.
                        Required when using a PDFFillerInterface.
        """
        self.session_manager.create_session(
            user_id=user_id,
            session_id=session_id,
            pdf_path=pdf_path,
        )

    def get_fill_report(self, user_id: str, session_id: str) -> Optional[dict]:
        """
        Return the fill statistics report for a completed session.

        The report shows how many fields were in the config vs how many
        were filled, broken down by mandatory/optional.

        Returns:
            Report dict, or None if session not complete yet.
        """
        return self.storage.get_fill_report(user_id, session_id)

    def get_fill_report_text(self, user_id: str, session_id: str) -> Optional[str]:
        """
        Return the fill report as a human-readable text string.

        Returns:
            Formatted text, or None if session not complete yet.
        """
        report = self.get_fill_report(user_id, session_id)
        if report is None:
            return None
        from chatbot.pdf.fill_report import FillReport
        return FillReport.format_text(report)

    def get_session_data(self, user_id: str, session_id: str) -> Optional[dict]:
        """
        Return the final filled data dict for a completed session.

        Returns:
            The ``final_output_flat.json`` dict, or None if not complete yet.
        """
        return self.storage.get_final_output_flat(user_id, session_id)

    def list_sessions(self, user_id: str) -> list[str]:
        """Return all session IDs for a user."""
        return self.storage.list_user_sessions(user_id)

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete all data for a session."""
        return self.storage.delete_session(user_id, session_id)