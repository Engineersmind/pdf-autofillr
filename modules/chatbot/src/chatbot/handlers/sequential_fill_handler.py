# chatbot/handlers/sequential_fill_handler.py
"""
Handles SEQUENTIAL_FILL state.

Used when bulk extraction repeatedly fails to capture a specific field.
Asks the user for exactly one field at a time and validates the answer
before moving on.

Entered from:  DataCollectionHandler, MissingFieldsHandler
Returns to:    DATA_COLLECTION (after filling the field or skip)
               MISSING_FIELDS_PROMPT (if still mandatory fields remain)
"""
from __future__ import annotations
from typing import List, Optional, Tuple

from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.logging.debug_logger import DebugLogger
from chatbot.utils.field_utils import (
    get_missing_mandatory_keys,
    format_field_name,
)
from chatbot.utils.intent_detection import is_skip_intent
from chatbot.validation.field_validator import validate_field


class SequentialFillHandler(BaseHandler):
    """
    Asks for one field at a time and validates the answer.

    Session keys read:  fields_being_asked (list of field_keys, uses index 0)
    Session keys set:   live_fill_flat (updates target field), fields_being_asked
    """

    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = State.SEQUENTIAL_FILL.value
        live_fill = session.get("live_fill_flat", {})
        mandatory_flat = session.get("mandatory_flat", {})
        fields = session.get("fields_being_asked", [])

        if not fields:
            # Nothing queued — back to normal collection
            return self._back_to_collection(session, user_input, state)

        current_field = fields[0]

        # Handle skip
        if is_skip_intent(user_input):
            debug and debug.log("sequential_fill", f"User skipped field: {current_field}")
            # Only allow skip if field is not mandatory
            if current_field in mandatory_flat:
                msg = (
                    f"This field is required. "
                    f"{self._ask_question(current_field)}"
                )
                self._log_turn(session, user_input, msg, state)
                return msg, State.SEQUENTIAL_FILL
            # Optional field — skip it
            return self._advance(session, user_input, state, live_fill, mandatory_flat, fields)

        # Try direct single-value extraction
        extracted = self._extract_single(user_input, current_field, session, live_fill)
        value = extracted.get(current_field)

        if value is not None and value != "":
            valid, err = validate_field(current_field, value)
            if valid or "_check" in current_field:
                live_fill[current_field] = value
                session["live_fill_flat"] = live_fill
                debug and debug.log("sequential_fill", f"Filled {current_field} = {value!r}")
                return self._advance(session, user_input, state, live_fill, mandatory_flat, fields)
            else:
                # Validation failed — ask again with error hint
                msg = f"{err}\n\n{self._ask_question(current_field)}"
                self._log_turn(session, user_input, msg, state)
                return msg, State.SEQUENTIAL_FILL
        else:
            # Couldn't extract — re-ask
            msg = (
                f"I couldn't get that. {self._ask_question(current_field)}"
            )
            self._log_turn(session, user_input, msg, state)
            return msg, State.SEQUENTIAL_FILL

    # ------------------------------------------------------------------

    def _extract_single(self, user_input: str, field_key: str, session: dict, live_fill: dict) -> dict:
        """Use LLM to extract just this one field."""
        try:
            extracted, _, _ = self.extractor.extract(
                user_input=user_input,
                conversation_history="",
                live_fill_flat={field_key: live_fill.get(field_key)},
                meta_form_keys=self.form_config.meta_form_keys,
                investor_type=session.get("investor_type", ""),
            )
            return extracted
        except Exception:
            # Naive fallback: use the raw input directly for text fields
            if "_check" not in field_key:
                return {field_key: user_input.strip()}
            return {}

    def _ask_question(self, field_key: str) -> str:
        question = self.form_config.get_question(field_key)
        if question:
            return question
        label = self.form_config.get_label(field_key) or format_field_name(field_key)
        return f"Please provide your {label.lower()}."

    def _advance(self, session, user_input, state, live_fill, mandatory_flat, fields):
        """Move to the next field or exit sequential fill."""
        remaining = fields[1:]
        session["fields_being_asked"] = remaining

        if remaining:
            # Ask the next field
            next_field = remaining[0]
            msg = self._ask_question(next_field)
            self._log_turn(session, user_input, msg, state)
            return msg, State.SEQUENTIAL_FILL

        # No more queued fields — check if mandatory complete
        missing = get_missing_mandatory_keys(live_fill, mandatory_flat)
        if missing:
            return self._back_to_collection(session, user_input, state)

        msg = "Thank you! I have all the required information."
        self._log_turn(session, user_input, msg, state)
        return msg, State.OPTIONAL_FIELDS_PROMPT

    def _back_to_collection(self, session, user_input, state):
        msg = "Let's continue. Please share any remaining information."
        self._log_turn(session, user_input, msg, state)
        return msg, State.DATA_COLLECTION