# chatbot/handlers/another_info_handler.py
"""
Handles ANOTHER_INFO_PROMPT state.

The final checkpoint before COMPLETE.
"Is there anything else you'd like to add or correct before we finalise?"

  - yes  → DATA_COLLECTION (one more pass)
  - no   → COMPLETE
  - free-form text → treat as additional data, extract, then COMPLETE
"""
from __future__ import annotations
from typing import Optional, Tuple

from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.logging.debug_logger import DebugLogger
from chatbot.utils.intent_detection import is_affirmative, is_negative, is_exit_intent


class AnotherInfoHandler(BaseHandler):
    """
    Final yes/no before completing the session.

    Session keys read:  live_fill_flat, investor_type
    Session keys set:   live_fill_flat (if inline data provided)
    """

    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = State.ANOTHER_INFO_PROMPT.value
        live_fill = session.get("live_fill_flat", {})

        if is_negative(user_input) or is_exit_intent(user_input):
            debug and debug.log("another_info", "User confirmed no more info — completing")
            return self._complete(session, user_input, state)

        if is_affirmative(user_input):
            debug and debug.log("another_info", "User wants to add more info")
            msg = "Of course! What else would you like to add or correct?"
            self._log_turn(session, user_input, msg, state)
            return msg, State.DATA_COLLECTION

        # User may have provided extra data directly — try to extract it
        extracted, _, _ = self.extractor.extract(
            user_input=user_input,
            conversation_history=self._build_history(session),
            live_fill_flat=live_fill,
            meta_form_keys=self.form_config.meta_form_keys,
            investor_type=session.get("investor_type", ""),
        )

        if extracted:
            for key, value in extracted.items():
                if key in live_fill and value not in (None, ""):
                    live_fill[key] = value
            session["live_fill_flat"] = live_fill
            debug and debug.log(
                "another_info",
                f"Extracted {len(extracted)} additional fields — completing",
                data={"fields": list(extracted.keys())},
            )
            return self._complete(session, user_input, state)

        # Unclear — re-ask
        msg = (
            "Is there anything else you'd like to add or correct? "
            "Please reply yes or no."
        )
        self._log_turn(session, user_input, msg, state)
        return msg, State.ANOTHER_INFO_PROMPT

    def _complete(self, session, user_input, state):
        investor_type = session.get("investor_type", "investor")
        msg = (
            f"Thank you! Your {investor_type} onboarding information has been collected "
            "and your form is now complete. We'll be in touch shortly."
        )
        self._log_turn(session, user_input, msg, state)
        return msg, State.COMPLETE

    def _build_history(self, session: dict) -> str:
        log = session.get("conversation_log", [])
        lines = []
        for entry in log[-4:]:
            lines.append(f"User: {entry.get('user', '')}")
            lines.append(f"Bot: {entry.get('bot', '')}")
        return "\n".join(lines)