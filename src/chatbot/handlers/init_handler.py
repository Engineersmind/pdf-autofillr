# chatbot/handlers/init_handler.py
"""
Handles INIT and SAVED_INFO_CHECK states.
"""
from __future__ import annotations
from typing import Optional, Tuple
from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.logging.debug_logger import DebugLogger


class InitHandler(BaseHandler):
    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = session.get("state", State.INIT.value)

        # First ever call — send greeting
        if state == State.INIT.value and not session.get("conversation_log"):
            greeting = self._get_greeting()
            self._log_turn(session, user_input, greeting, state)
            return greeting, State.SAVED_INFO_CHECK

        # Check for existing user data
        if state == State.SAVED_INFO_CHECK.value or state == State.INIT.value:
            existing = self.storage.get_user_integrated_info(user_id)
            if existing:
                msg = (
                    "Welcome back! I have some information from your previous session. "
                    "Would you like to use it to pre-fill this form? (yes / no)"
                )
                session["_pending_existing_data"] = existing
                self._log_turn(session, user_input, msg, state)
                return msg, State.UPDATE_EXISTING_PROMPT

            # No existing data — go straight to investor type selection
            return self._show_investor_type_menu(session, user_input, state)

        return self._show_investor_type_menu(session, user_input, state)

    def _show_investor_type_menu(self, session, user_input, state):
        from chatbot.core.states import INVESTOR_TYPES
        lines = ["Please select your investor type:\n"]
        for i, t in enumerate(INVESTOR_TYPES, 1):
            lines.append(f"  {i}. {t}")
        msg = "\n".join(lines)
        self._log_turn(session, user_input, msg, state)
        return msg, State.INVESTOR_TYPE_SELECT
