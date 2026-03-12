# chatbot/extraction/extractor.py
"""
Extractor — entry point: tries LLM extraction, falls back to regex.
"""
from __future__ import annotations

import time
from typing import Optional, Tuple

from chatbot.extraction.llm_extractor import LLMExtractor
from chatbot.extraction.fallback_extractor import FallbackExtractor


class Extractor:
    """
    Unified extraction interface.

    Tries LLM first. If LLM raises or returns empty, falls back to
    FallbackExtractor (regex-based, no network call).
    """

    def __init__(self, openai_api_key: str, prompt_builder=None):
        self.llm = LLMExtractor(
            openai_api_key=openai_api_key,
            prompt_builder=prompt_builder,
        )
        self.fallback = FallbackExtractor()

    def extract(
        self,
        user_input: str,
        conversation_history: str,
        live_fill_flat: dict,
        meta_form_keys: dict,
        mandatory_flat: Optional[dict] = None,
        investor_type: Optional[str] = None,
    ) -> Tuple[dict, float, str]:
        """
        Extract structured field values from user input.

        Returns:
            (extracted_dict, latency_seconds, method)
            method is either "llm" or "fallback"
        """
        start = time.time()

        try:
            # ✅ FIX: unpack LLM return values
            result, latency, method = self.llm.extract(
                user_input=user_input,
                conversation_history=conversation_history,
                live_fill_flat=live_fill_flat,
                meta_form_keys=meta_form_keys,
                mandatory_flat=mandatory_flat,
                investor_type=investor_type,
            )

            # If LLM returned something useful
            if result:
                return result, latency, method

        except Exception as e:
            print(f"⚠️ LLM extraction failed, using fallback: {e}")

        # Fallback
        result = self.fallback.extract(
            user_input=user_input,
            live_fill_flat=live_fill_flat
        )
        latency = time.time() - start
        return result, latency, "fallback"