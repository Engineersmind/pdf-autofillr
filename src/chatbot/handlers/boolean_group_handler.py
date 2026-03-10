# chatbot/handlers/boolean_group_handler.py
"""
Handles BOOLEAN_GROUP_SELECT state.

Presents a group of boolean (yes/no) checkboxes to the user —
e.g. investor type checkboxes (individual_check, corporation_check, etc.)
or eligibility checkboxes (accredited_investor_check, etc.).

The user can answer field by field or provide all at once.
"""
from __future__ import annotations
from typing import List, Optional, Tuple

from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.logging.debug_logger import DebugLogger
from chatbot.utils.field_utils import format_field_name
from chatbot.utils.intent_detection import is_affirmative, is_negative, is_skip_intent


class BooleanGroupHandler(BaseHandler):
    """
    Processes user yes/no answers for a group of boolean fields.

    Session keys used:
        fields_being_asked : list of field_key strings for this group
        current_group      : same list (set by DataCollectionHandler)
    """

    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = State.BOOLEAN_GROUP_SELECT.value
        live_fill = session.get("live_fill_flat", {})
        fields = session.get("fields_being_asked", [])

        if not fields:
            return self._back_to_collection(session, user_input, state)

        # Try to extract boolean values from user input via LLM
        extracted, _, method = self.extractor.extract(
            user_input=user_input,
            conversation_history=self._build_history(session),
            live_fill_flat={k: live_fill[k] for k in fields if k in live_fill},
            meta_form_keys=self.form_config.meta_form_keys,
            investor_type=session.get("investor_type", ""),
        )

        debug and debug.log("boolean_group", f"Extracted {len(extracted)} booleans via {method}")

        # Merge extracted boolean values
        any_filled = False
        for key in fields:
            if key in extracted and extracted[key] in (True, False):
                live_fill[key] = extracted[key]
                any_filled = True

        # Fallback: single-field group with simple yes/no
        if not any_filled and len(fields) == 1:
            key = fields[0]
            if is_affirmative(user_input):
                live_fill[key] = True
                any_filled = True
            elif is_negative(user_input) or is_skip_intent(user_input):
                live_fill[key] = False
                any_filled = True

        session["live_fill_flat"] = live_fill

        # Still unfilled fields in this group?
        still_empty = [f for f in fields if live_fill.get(f) is None]

        if still_empty and not any_filled:
            # Re-prompt for the same group
            labels = [format_field_name(f) for f in still_empty]
            lines = ["Please answer yes or no for each of the following:\n"]
            for label in labels:
                lines.append(f"  • {label}")
            msg = "\n".join(lines)
            self._log_turn(session, user_input, msg, state)
            return msg, State.BOOLEAN_GROUP_SELECT

        if still_empty:
            # Partially filled — ask for remaining
            labels = [format_field_name(f) for f in still_empty]
            lines = ["Almost there! Please answer for:\n"]
            for label in labels:
                lines.append(f"  • {label} (yes / no)")
            msg = "\n".join(lines)
            session["fields_being_asked"] = still_empty
            self._log_turn(session, user_input, msg, state)
            return msg, State.BOOLEAN_GROUP_SELECT

        # All filled — back to data collection
        return self._back_to_collection(session, user_input, state)

    def _back_to_collection(self, session, user_input, state):
        session["fields_being_asked"] = []
        session["current_group"] = None
        msg = "Got it! Let's continue. Please share any remaining information."
        self._log_turn(session, user_input, msg, state)
        return msg, State.DATA_COLLECTION

    def _build_history(self, session: dict) -> str:
        log = session.get("conversation_log", [])
        lines = []
        for entry in log[-4:]:
            lines.append(f"User: {entry.get('user', '')}")
            lines.append(f"Bot: {entry.get('bot', '')}")
        return "\n".join(lines)