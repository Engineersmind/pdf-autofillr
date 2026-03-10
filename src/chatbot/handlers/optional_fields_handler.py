# chatbot/handlers/optional_fields_handler.py
"""
Handles OPTIONAL_FIELDS_PROMPT state.

Reached after all mandatory fields are confirmed. Asks the user whether
they want to provide optional (non-mandatory) fields such as wiring
details, date of birth, secondary contact, etc.
"""
from __future__ import annotations
from typing import List, Optional, Tuple

from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.logging.debug_logger import DebugLogger
from chatbot.utils.field_utils import get_optional_fields, format_field_name
from chatbot.utils.intent_detection import is_affirmative, is_negative, is_skip_intent

MAX_OPTIONAL_DISPLAY = 8


class OptionalFieldsHandler(BaseHandler):
    """
    Session keys read:  live_fill_flat, mandatory_flat
    Session keys set:   _optional_prompted, _collecting_optional
    """

    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = State.OPTIONAL_FIELDS_PROMPT.value
        live_fill = session.get("live_fill_flat", {})
        mandatory_flat = session.get("mandatory_flat", {})

        optional_empty = get_optional_fields(live_fill, mandatory_flat)

        # No optional fields at all — proceed straight to ANOTHER_INFO
        if not optional_empty:
            debug and debug.log("optional_fields", "No optional fields — skipping to another_info")
            return self._go_to_another_info(session, user_input, state)

        # First visit — show the list and ask
        if not session.get("_optional_prompted"):
            session["_optional_prompted"] = True
            msg = self._build_optional_prompt(optional_empty)
            self._log_turn(session, user_input, msg, state)
            return msg, State.OPTIONAL_FIELDS_PROMPT

        # Second visit — user has responded
        if is_negative(user_input) or is_skip_intent(user_input):
            debug and debug.log("optional_fields", "User skipped optional fields")
            return self._go_to_another_info(session, user_input, state)

        if is_affirmative(user_input):
            debug and debug.log("optional_fields", "User wants to fill optional fields")
            msg = (
                "Of course! Please share any additional information you'd like "
                "to include — wiring details, date of birth, etc."
            )
            session["_collecting_optional"] = True
            self._log_turn(session, user_input, msg, state)
            return msg, State.DATA_COLLECTION

        # User might have directly provided optional data inline
        extracted, _, _ = self.extractor.extract(
            user_input=user_input,
            conversation_history=self._build_history(session),
            live_fill_flat={k: live_fill[k] for k in optional_empty if k in live_fill},
            meta_form_keys=self.form_config.meta_form_keys,
            investor_type=session.get("investor_type", ""),
        )
        if extracted:
            for key, value in extracted.items():
                if key in live_fill and value not in (None, ""):
                    live_fill[key] = value
            session["live_fill_flat"] = live_fill
            debug and debug.log("optional_fields", f"Extracted {len(extracted)} optional fields inline")
            return self._go_to_another_info(session, user_input, state)

        # Unclear — re-ask
        msg = (
            "Would you like to provide any optional information such as "
            f"{self._list_sample(optional_empty)}? (yes / no)"
        )
        self._log_turn(session, user_input, msg, state)
        return msg, State.OPTIONAL_FIELDS_PROMPT

    def _build_optional_prompt(self, optional_empty: List[str]) -> str:
        display = optional_empty[:MAX_OPTIONAL_DISPLAY]
        lines = [
            "You've completed all required fields!\n",
            "There are some optional fields you may want to fill in:\n",
        ]
        for key in display:
            label = self.form_config.get_label(key) or format_field_name(key)
            lines.append(f"  • {label}")
        if len(optional_empty) > MAX_OPTIONAL_DISPLAY:
            lines.append(f"  • ... and {len(optional_empty) - MAX_OPTIONAL_DISPLAY} more")
        lines.append("\nWould you like to fill these in? (yes / no)")
        return "\n".join(lines)

    def _list_sample(self, keys: List[str]) -> str:
        sample = [
            self.form_config.get_label(k) or format_field_name(k)
            for k in keys[:3]
        ]
        return ", ".join(sample)

    def _go_to_another_info(self, session, user_input, state):
        msg = (
            "Is there anything else you'd like to add or correct "
            "before we finalise your form? (yes / no)"
        )
        self._log_turn(session, user_input, msg, state)
        return msg, State.ANOTHER_INFO_PROMPT

    def _build_history(self, session: dict) -> str:
        log = session.get("conversation_log", [])
        lines = []
        for entry in log[-4:]:
            lines.append(f"User: {entry.get('user', '')}")
            lines.append(f"Bot: {entry.get('bot', '')}")
        return "\n".join(lines)