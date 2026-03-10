# chatbot/handlers/missing_fields_handler.py
"""
Handles MISSING_FIELDS_PROMPT state.

Entered after DataCollectionHandler determines all mandatory fields
are filled. This handler double-checks and either:
  - Passes through to OPTIONAL_FIELDS_PROMPT if truly complete.
  - Returns to DATA_COLLECTION with a targeted prompt if gaps remain.
  - Switches to SEQUENTIAL_FILL if the same fields keep being missed.
"""
from __future__ import annotations
from typing import Optional, Tuple, List

from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.logging.debug_logger import DebugLogger
from chatbot.utils.field_utils import (
    get_missing_mandatory_keys,
    format_field_name,
)
from chatbot.utils.intent_detection import is_skip_intent

# How many consecutive turns on the same missing fields before switching
# to sequential fill
SEQUENTIAL_THRESHOLD = 2


class MissingFieldsHandler(BaseHandler):
    """
    Validates mandatory completeness and routes accordingly.

    Session keys read:  live_fill_flat, mandatory_flat
    Session keys set:   _missing_attempts (counter), fields_being_asked
    """

    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = State.MISSING_FIELDS_PROMPT.value
        live_fill = session.get("live_fill_flat", {})
        mandatory_flat = session.get("mandatory_flat", {})

        missing = get_missing_mandatory_keys(live_fill, mandatory_flat)

        if not missing:
            # All mandatory fields present — move on
            debug and debug.log("missing_fields", "All mandatory fields complete")
            msg = "All required fields are complete. Let me check optional fields."
            self._log_turn(session, user_input, msg, state)
            return msg, State.OPTIONAL_FIELDS_PROMPT

        # Try to extract from current input before prompting
        if user_input.strip():
            extracted, _, _ = self.extractor.extract(
                user_input=user_input,
                conversation_history=self._build_history(session),
                live_fill_flat={k: live_fill[k] for k in missing if k in live_fill},
                meta_form_keys=self.form_config.meta_form_keys,
                mandatory_flat=mandatory_flat,
                investor_type=session.get("investor_type", ""),
            )
            for key, value in extracted.items():
                if key in live_fill and live_fill.get(key) in (None, "") and value not in (None, ""):
                    live_fill[key] = value
            session["live_fill_flat"] = live_fill

            # Re-check after extraction
            missing = get_missing_mandatory_keys(live_fill, mandatory_flat)
            if not missing:
                msg = "All required fields are complete. Let me check optional fields."
                self._log_turn(session, user_input, msg, state)
                return msg, State.OPTIONAL_FIELDS_PROMPT

        # Track how many times we've been stuck on the same missing fields
        attempts = session.get("_missing_attempts", 0) + 1
        session["_missing_attempts"] = attempts

        debug and debug.log(
            "missing_fields",
            f"Still missing {len(missing)} mandatory fields (attempt {attempts})",
            data={"missing": missing[:5]},
        )

        # After SEQUENTIAL_THRESHOLD attempts, ask one field at a time
        if attempts >= SEQUENTIAL_THRESHOLD:
            session["fields_being_asked"] = missing[:1]
            session["_missing_attempts"] = 0
            field_key = missing[0]
            question = self.form_config.get_question(field_key)
            label = self.form_config.get_label(field_key) or format_field_name(field_key)
            msg = question or f"Could you please provide your {label.lower()}?"
            self._log_turn(session, user_input, msg, state)
            return msg, State.SEQUENTIAL_FILL

        # Standard prompt listing what's missing
        msg = self._build_missing_prompt(missing)
        self._log_turn(session, user_input, msg, state)
        return msg, State.DATA_COLLECTION

    def _build_missing_prompt(self, missing: List[str]) -> str:
        lines = [
            f"I still need {len(missing)} required field(s) before we can complete your form:\n"
        ]
        for key in missing[:6]:
            question = self.form_config.get_question(key)
            label = self.form_config.get_label(key) or format_field_name(key)
            lines.append(f"  • {question or label}")
        if len(missing) > 6:
            lines.append(f"  • ... and {len(missing) - 6} more")
        lines.append("\nPlease provide this information to continue.")
        return "\n".join(lines)

    def _build_history(self, session: dict) -> str:
        log = session.get("conversation_log", [])
        lines = []
        for entry in log[-4:]:
            lines.append(f"User: {entry.get('user', '')}")
            lines.append(f"Bot: {entry.get('bot', '')}")
        return "\n".join(lines)