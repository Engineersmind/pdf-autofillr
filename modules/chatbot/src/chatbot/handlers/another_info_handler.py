# chatbot/handlers/another_info_handler.py
"""
Handles ANOTHER_INFO_PROMPT state.

Mid-collection yes/no checkpoint after every DATA_COLLECTION turn.

  yes  → "Alright! Please enter details..." → DATA_COLLECTION
  no   → delegate directly to MissingFieldsHandler (no intermediate message)
  free-form text → extract, loop back
"""
from __future__ import annotations

from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.utils.intent_detection import is_affirmative, is_negative, is_exit_intent


class AnotherInfoHandler(BaseHandler):

    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = State.ANOTHER_INFO_PROMPT.value
        live_fill = session.get("live_fill_flat", {})
        mandatory_flat = session.get("mandatory_flat", {})
        investor_type = session.get("investor_type", "")

        if is_exit_intent(user_input):
            msg = "Session ended. Your progress has been saved. Goodbye!"
            self._log_turn(session, user_input, msg, state)
            return msg, State.COMPLETE

        if is_affirmative(user_input):
            debug and debug.log("another_info", "User wants to add more info")
            msg = "Alright! Please enter details in the chat whenever you're ready."
            self._log_turn(session, user_input, msg, state)
            return msg, State.DATA_COLLECTION

        if is_negative(user_input):
            debug and debug.log("another_info", "User said no — delegating to MissingFieldsHandler")
            # Delegate directly to MissingFieldsHandler — no intermediate message shown
            from chatbot.handlers.missing_fields_handler import MissingFieldsHandler
            handler = MissingFieldsHandler(self.engine)
            return handler.handle(session, user_input, user_id, session_id, debug)

        # Free-form text — try to extract additional data then ask again
        extracted, _, _ = self.extractor.extract(
            user_input=user_input,
            conversation_history=self._build_history(session),
            live_fill_flat=live_fill,
            meta_form_keys=self.form_config.meta_form_keys,
            mandatory_flat=mandatory_flat,
            investor_type=investor_type,
        )

        if extracted:
            for key, value in extracted.items():
                if key in live_fill and value not in (None, ""):
                    live_fill[key] = value
            session["live_fill_flat"] = live_fill
            debug and debug.log(
                "another_info",
                f"Extracted {len(extracted)} fields from free-form",
                data={"fields": list(extracted.keys())},
            )

        msg = "Do you have any other information you'd like to provide? (yes/no):"
        self._log_turn(session, user_input, msg, state)
        return msg, State.ANOTHER_INFO_PROMPT

    def _build_history(self, session: dict) -> str:
        log = session.get("conversation_log", [])
        lines = []
        for entry in log[-4:]:
            lines.append(f"User: {entry.get('user', '')}")
            lines.append(f"Bot: {entry.get('bot', '')}")
        return "\n".join(lines)