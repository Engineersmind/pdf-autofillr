# chatbot/core/engine.py
"""
ConversationEngine — main orchestrator.

Owns the session lifecycle, routes each turn to the correct handler,
and coordinates extraction, storage, telemetry, and PDF workflow.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

from chatbot.config.form_config import FormConfig
from chatbot.config.settings import Settings
from chatbot.core.router import StateRouter
from chatbot.core.session import SessionManager
from chatbot.core.states import State
from chatbot.extraction.extractor import Extractor
from chatbot.logging.debug_logger import DebugLogger
from chatbot.pdf.interface import PDFFillerInterface
from chatbot.pdf.workflow import PDFWorkflowManager
from chatbot.storage.base import StorageBackend
from chatbot.telemetry.collector import TelemetryCollector
from chatbot.utils.dict_utils import unflatten_dict


class ConversationEngine:
    """
    Orchestrates one message turn end-to-end.

    Called by chatbotClient.send_message(); never called directly.
    """

    def __init__(
        self,
        storage: StorageBackend,
        form_config: FormConfig,
        openai_api_key: str,
        pdf_filler: Optional[PDFFillerInterface],
        telemetry: TelemetryCollector,
        prompt_builder=None,
        settings: Optional[Settings] = None,
    ):
        self.storage = storage
        self.form_config = form_config
        self.openai_api_key = openai_api_key
        self.telemetry = telemetry
        self.settings = settings or Settings()

        self.session_manager = SessionManager(storage=storage)

        self.extractor = Extractor(
            openai_api_key=openai_api_key,
            prompt_builder=prompt_builder,
        )

        self.pdf_workflow: Optional[PDFWorkflowManager] = (
            PDFWorkflowManager(
                filler=pdf_filler,
                storage=storage,
                settings=settings,
            )
            if pdf_filler
            else None
        )

        self._router: Optional[StateRouter] = None

    @property
    def router(self) -> StateRouter:
        if self._router is None:
            self._router = StateRouter.build(self)
        return self._router

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_message(
        self,
        user_id: str,
        session_id: str,
        user_input: str,
        debug: Optional[DebugLogger] = None,
    ) -> Tuple[str, bool]:
        """
        Process one message turn.

        Returns:
            (response_text, session_complete)
        """
        start = time.time()

        session = self.session_manager.load_or_create(user_id, session_id)
        state = State(session.get("state", State.INIT.value))

        debug and debug.log(
            "state_machine",
            f"Turn received | state={state.value} | input_len={len(user_input)}",
            data={"user_input": user_input[:200]},
        )

        # ── PDF workflow resume check ──────────────────────────────────
        # Mirrors Lambda's _check_and_resume_pdf_workflow().
        # On every message, check if a PDF workflow was interrupted
        # (e.g. server restart mid-fill) and resume it if needed.
        self._check_and_resume_pdf_workflow(user_id, session_id, session, debug)

        # Route to handler
        handler = self.router.get_handler(state)
        response_text, next_state = handler.handle(
            session=session,
            user_input=user_input,
            user_id=user_id,
            session_id=session_id,
            debug=debug,
        )

        # Persist state
        session["state"] = next_state.value if isinstance(next_state, State) else next_state
        self.session_manager.save(user_id, session_id, session)

        session_complete = session["state"] == State.COMPLETE.value

        self.telemetry.track_state_transition(
            from_state=state.value,
            to_state=session["state"],
            turn_number=len(session.get("conversation_log", [])),
            latency=time.time() - start,
            user_id=user_id,
            session_id=session_id,
        )

        if session_complete:
            self._finalise_session(user_id, session_id, session, debug)

        debug and debug.log(
            "state_machine",
            f"Turn complete | next_state={session['state']} | "
            f"complete={session_complete} | latency={time.time()-start:.2f}s",
        )

        return response_text, session_complete

    # ------------------------------------------------------------------
    # PDF workflow resume — mirrors Lambda _check_and_resume_pdf_workflow()
    # ------------------------------------------------------------------

    def _check_and_resume_pdf_workflow(
        self,
        user_id: str,
        session_id: str,
        session: dict,
        debug: Optional[DebugLogger],
    ) -> None:
        """
        Check whether a PDF workflow was interrupted and resume it.

        Called on every message turn. If the session is complete and a
        pdf_path is set but the fill workflow never finished (no successful
        'fill' step in the logs), re-trigger the fill worker.

        Mirrors Lambda's _check_and_resume_pdf_workflow() called at top of
        every process_message() invocation.
        """
        if not self.pdf_workflow:
            return

        # Only applies to completed sessions with a pdf_path configured
        if session.get("state") != State.COMPLETE.value:
            return
        if not session.get("pdf_path"):
            return

        # Check the filling logs for a successful fill step
        logs = self.storage.get_pdf_filling_logs(user_id, session_id) or {}
        steps = logs.get("steps", [])

        fill_succeeded = any(
            s.get("step") == "fill" and s.get("success") is True
            for s in steps
        )

        if fill_succeeded:
            return  # Already done — nothing to resume

        # Check if a prepare step succeeded (we have a doc_id)
        prepare_succeeded = any(
            s.get("step") == "prepare" and s.get("success") is True
            for s in steps
        )

        live_fill_flat = session.get("live_fill_flat", {})
        if not live_fill_flat:
            # Try loading from storage (session was finalised but in-memory is stale)
            live_fill_flat = self.storage.get_final_output_flat(user_id, session_id) or {}

        if not live_fill_flat:
            debug and debug.log(
                "pdf_resume",
                "Cannot resume PDF workflow — no fill data available",
                level="warning",
            )
            return

        debug and debug.log(
            "pdf_resume",
            f"Resuming interrupted PDF workflow | "
            f"prepare_done={prepare_succeeded} | fill_done=False",
        )

        self.pdf_workflow.trigger_async(
            user_id=user_id,
            session_id=session_id,
            pdf_path=session["pdf_path"],
            investor_type=session.get("investor_type", ""),
            data_flat=live_fill_flat,
        )

    # ------------------------------------------------------------------
    # Finalisation helpers
    # ------------------------------------------------------------------

    def _finalise_session(
        self,
        user_id: str,
        session_id: str,
        session: dict,
        debug: Optional[DebugLogger],
    ) -> None:
        """Save final output files and optionally trigger PDF workflow."""
        live_fill_flat = session.get("live_fill_flat", {})

        self.storage.save_final_output_flat(user_id, session_id, live_fill_flat)

        nested = unflatten_dict(live_fill_flat)
        self.storage.save_final_output(user_id, session_id, nested)

        self._update_integrated_info(user_id, live_fill_flat)

        if self.pdf_workflow and session.get("pdf_path"):
            self.pdf_workflow.trigger_async(
                user_id=user_id,
                session_id=session_id,
                pdf_path=session["pdf_path"],
                investor_type=session.get("investor_type", ""),
                data_flat=live_fill_flat,
            )

        debug and debug.log("state_machine", "Session finalised — outputs saved")

    def _update_integrated_info(self, user_id: str, live_fill_flat: dict) -> None:
        existing = self.storage.get_user_integrated_info(user_id) or {}
        merged = {
            **existing,
            **{k: v for k, v in live_fill_flat.items() if v not in (None, "", [])},
        }
        self.storage.save_user_integrated_info(user_id, merged)