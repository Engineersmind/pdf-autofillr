# chatbot/handlers/data_collection_handler.py
"""
Handles DATA_COLLECTION state — the main field-extraction workhorse.

Flow:
  1. Run LLM extraction on the user's message.
  2. Merge extracted values into live_fill_flat.
  3. Apply form_pf filtering if registered country is now known (non-US investors).
  4. Populate internal split fields (telephone_part_, fax_part_) from full numbers.
  5. Save updated live_fill (for cross-turn persistence).
  6. If any boolean groups have un-asked fields → BOOLEAN_GROUP_SELECT.
  7. If mailing address fields exist and not yet checked → MAILING_ADDRESS_CHECK.
  8. If all mandatory fields filled → OPTIONAL_FIELDS_PROMPT.
  9. Otherwise stay in DATA_COLLECTION and ask for more.
"""
from __future__ import annotations
from typing import Optional, Tuple, List

from chatbot.core.states import State
from chatbot.handlers.base_handler import BaseHandler
from chatbot.logging.debug_logger import DebugLogger
from chatbot.utils.address_utils import check_mailing_fields
from chatbot.utils.dict_utils import flatten_dict
from chatbot.utils.field_utils import (
    get_missing_mandatory_keys,
    classify_fields_by_type,
    format_field_name,
    filter_form_pf_fields,
    filter_user_facing_fields,
    get_registered_country,
    is_internal_split_field,
)
from chatbot.utils.intent_detection import is_exit_intent
from chatbot.validation.field_validator import validate_field
from chatbot.validation.phone_validator import split_phone_parts

# How many mandatory fields to list when prompting user
MAX_MISSING_DISPLAY = 6
# Min extracted fields before we consider the turn "productive"
MIN_EXTRACTED = 1

# Field key suffixes that indicate a phone or fax full-number field
PHONE_FAX_FULL_FIELD_SUFFIXES = ("telephone", "phone", "mobile", "fax", "tel")


class DataCollectionHandler(BaseHandler):
    """Collects investor data by running LLM extraction each turn."""

    def handle(self, session, user_input, user_id, session_id, debug=None):
        state = State.DATA_COLLECTION.value

        if is_exit_intent(user_input):
            msg = "Session ended. Your progress has been saved. Goodbye!"
            self._log_turn(session, user_input, msg, state)
            return msg, State.COMPLETE

        live_fill = session.setdefault("live_fill_flat", {})
        mandatory_flat = session.get("mandatory_flat", {})
        investor_type = session.get("investor_type", "")

        # Build conversation history string for LLM context
        history = self._build_history(session)

        # ── Extraction (only user-facing fields sent to LLM) ───────────
        user_facing = filter_user_facing_fields(live_fill)

        extracted, latency, method = self.extractor.extract(
            user_input=user_input,
            conversation_history=history,
            live_fill_flat=user_facing,
            meta_form_keys=self.form_config.meta_form_keys,
            mandatory_flat=mandatory_flat,
            investor_type=investor_type,
        )

        debug and debug.log(
            "data_collection",
            f"Extracted {len(extracted)} fields via {method} in {latency:.2f}s",
            data={"fields": list(extracted.keys())},
        )

        # Validate and merge extracted values
        merged_count = 0
        for key, value in extracted.items():
            if key not in live_fill:
                continue
            if is_internal_split_field(key):
                continue  # never write split fields from LLM output
            valid, err = validate_field(key, value)
            if valid or value in (True, False, None):
                if live_fill.get(key) in (None, ""):
                    live_fill[key] = value
                    merged_count += 1
                elif value not in (None, ""):
                    live_fill[key] = value
                    merged_count += 1
            else:
                debug and debug.log(
                    "data_collection",
                    f"Validation failed for {key}: {err}",
                    level="warning",
                )

        # ── Populate internal split fields from full phone/fax numbers ──
        # Mirrors Lambda: telephone_part_ and fax_part_ fields are auto-populated
        # from the full number and NEVER asked of the user directly.
        self._populate_split_fields(live_fill, debug)

        # ── form_pf filtering — strip non-US fields once country is known ──
        registered_country = get_registered_country(live_fill)
        if registered_country and not session.get("_form_pf_filtered"):
            filtered = filter_form_pf_fields(live_fill, registered_country)
            if len(filtered) < len(live_fill):
                removed = len(live_fill) - len(filtered)
                live_fill.clear()
                live_fill.update(filtered)
                # Also remove from mandatory_flat if present
                for key in list(mandatory_flat.keys()):
                    if key not in live_fill:
                        del mandatory_flat[key]
                session["mandatory_flat"] = mandatory_flat
                debug and debug.log(
                    "data_collection",
                    f"form_pf filtering: removed {removed} fields for non-US investor "
                    f"(country={registered_country})",
                )
            session["_form_pf_filtered"] = True

        session["live_fill_flat"] = live_fill

        # ── Routing decisions ──────────────────────────────────────────

        # 1. Boolean groups not yet confirmed?
        boolean_group = self._next_unasked_boolean_group(live_fill, session)
        if boolean_group:
            session["current_group"] = boolean_group
            session["fields_being_asked"] = boolean_group
            msg = self._build_boolean_group_prompt(boolean_group)
            self._log_turn(session, user_input, msg, state)
            return msg, State.BOOLEAN_GROUP_SELECT

        # 2. Mailing address not yet checked?
        if (
            check_mailing_fields(live_fill)
            and not session.get("_mailing_checked")
            and self._registered_address_filled(live_fill)
        ):
            msg = (
                "Is your mailing address the same as your registered address? "
                "(yes / no)"
            )
            self._log_turn(session, user_input, msg, state)
            return msg, State.MAILING_ADDRESS_CHECK

        # 3. Check mandatory completeness
        missing = get_missing_mandatory_keys(live_fill, mandatory_flat)

        if not missing:
            msg = (
                "Thank you! I have all the required information. "
                "Let me check if there's anything optional you'd like to add."
            )
            self._log_turn(session, user_input, msg, state)
            return msg, State.OPTIONAL_FIELDS_PROMPT

        # 4. Productive turn — ask for more
        if merged_count >= MIN_EXTRACTED or not session.get("conversation_log"):
            msg = self._build_continue_prompt(missing, merged_count)
        else:
            # Nothing extracted — switch to sequential fill for one field at a time
            session["fields_being_asked"] = missing[:1]
            msg = self._build_sequential_prompt(missing[0])
            self._log_turn(session, user_input, msg, state)
            return msg, State.SEQUENTIAL_FILL

        self._log_turn(session, user_input, msg, state)
        return msg, State.DATA_COLLECTION

    # ------------------------------------------------------------------
    # Internal split field population
    # ------------------------------------------------------------------

    def _populate_split_fields(self, live_fill: dict, debug) -> None:
        """
        For every full phone/fax field that has a value, auto-populate the
        corresponding telephone_part_ / fax_part_ split fields if they exist.
        These split fields are used by the PDF filler and are NEVER shown to users.
        """
        for key, value in list(live_fill.items()):
            if not value or not isinstance(value, str):
                continue
            leaf = key.split(".")[-1]
            # Identify full-number fields (not already a split part)
            is_phone_field = any(leaf.endswith(s) or leaf == s for s in PHONE_FAX_FULL_FIELD_SUFFIXES)
            if not is_phone_field:
                continue

            parts = split_phone_parts(value)
            prefix = key.rsplit(".", 1)[0] if "." in key else ""

            # Determine split field prefix: telephone_part_ or fax_part_
            if "fax" in leaf:
                split_prefix = "fax_part_"
            else:
                split_prefix = "telephone_part_"

            mapping = {
                f"{split_prefix}country_code": parts["country_code"],
                f"{split_prefix}1":            parts["part1"],
                f"{split_prefix}2":            parts["part2"],
                f"{split_prefix}3":            parts["part3"],
            }

            for split_leaf, split_val in mapping.items():
                full_key = f"{prefix}.{split_leaf}" if prefix else split_leaf
                if full_key in live_fill:
                    live_fill[full_key] = split_val

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_history(self, session: dict) -> str:
        log = session.get("conversation_log", [])
        lines = []
        for entry in log[-6:]:
            lines.append(f"User: {entry.get('user', '')}")
            lines.append(f"Bot: {entry.get('bot', '')}")
        return "\n".join(lines)

    def _next_unasked_boolean_group(self, live_fill: dict, session: dict):
        """Return the next boolean group (list of field keys) not yet asked."""
        asked_groups = session.get("_asked_boolean_groups", [])
        groups = self._get_boolean_groups(live_fill)
        for group_key, fields in groups.items():
            if group_key not in asked_groups:
                if any(live_fill.get(f) is None for f in fields):
                    session.setdefault("_asked_boolean_groups", []).append(group_key)
                    return fields
        return None

    def _get_boolean_groups(self, live_fill: dict) -> dict:
        """Group boolean fields by their section prefix."""
        from collections import defaultdict
        groups = defaultdict(list)
        for key in live_fill:
            if "_check" in key:
                section = key.split(".")[0] if "." in key else "general"
                groups[section].append(key)
        return dict(groups)

    def _build_boolean_group_prompt(self, fields: list) -> str:
        labels = [format_field_name(f) for f in fields]
        lines = ["Please confirm which of the following apply to you (answer yes/no for each):\n"]
        for label in labels:
            lines.append(f"  • {label}")
        return "\n".join(lines)

    def _registered_address_filled(self, live_fill: dict) -> bool:
        """Return True if at least city or line1 of registered address is filled."""
        for key in ("address_registered.address_registered_city_id",
                    "address_registered.address_registered_line1_id"):
            if live_fill.get(key):
                return True
        return False

    def _build_continue_prompt(self, missing: list, merged_count: int) -> str:
        if merged_count > 0:
            header = "Got it, thank you! I still need a few more details.\n\n"
        else:
            header = "I still need some information from you.\n\n"

        display = missing[:MAX_MISSING_DISPLAY]
        lines = [header + "Still needed:"]
        for key in display:
            label = self.form_config.get_label(key) or format_field_name(key)
            question = self.form_config.get_question(key)
            if question:
                lines.append(f"  • {question}")
            else:
                lines.append(f"  • {label}")

        if len(missing) > MAX_MISSING_DISPLAY:
            lines.append(f"  • ... and {len(missing) - MAX_MISSING_DISPLAY} more")

        lines.append("\nFeel free to share multiple fields at once.")
        return "\n".join(lines)

    def _build_sequential_prompt(self, field_key: str) -> str:
        question = self.form_config.get_question(field_key)
        if question:
            return question
        label = self.form_config.get_label(field_key) or format_field_name(field_key)
        return f"Please provide your {label.lower()}."