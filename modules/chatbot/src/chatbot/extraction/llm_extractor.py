# chatbot/extraction/llm_extractor.py
"""
LLMExtractor — uses GPT-4o-mini via LangChain to extract field values.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from langchain_openai import ChatOpenAI

from chatbot.extraction.prompt_builder import PromptBuilder


class LLMExtractor:
    """Extracts structured form field values using GPT-4o-mini."""

    MODEL = "gpt-4o-mini"

    def __init__(self, openai_api_key: str, prompt_builder=None):
        self.openai_api_key = openai_api_key
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm = ChatOpenAI(
            model=self.MODEL,
            temperature=0.0,
            openai_api_key=self.openai_api_key,
        )

    def extract(
        self,
        user_input: str,
        conversation_history: str,
        live_fill_flat: dict,
        meta_form_keys: dict,
        mandatory_flat: Optional[dict] = None,
        investor_type: Optional[str] = None,
    ) -> tuple:
        """
        Call GPT-4o-mini with the full form schema and return extracted fields.

        Returns:
            (extracted_dict, latency_seconds, method) — 3-tuple.
            Callers must unpack all 3 values.
        """
        start = time.time()

        prompt = self.prompt_builder.build(
            form_keys=live_fill_flat,
            meta_form_keys=meta_form_keys,
            mandatory_flat=mandatory_flat or {},
            investor_type=investor_type or "Not yet specified",
            conversation_history=conversation_history,
            user_input=user_input,
        )

        result = self.llm.invoke(prompt)
        raw = result.content if hasattr(result, "content") else str(result)

        extracted = self._parse_json(raw)
        known_keys = set(live_fill_flat.keys())
        filtered = {k: v for k, v in extracted.items() if k in known_keys}
        latency = time.time() - start
        return filtered, latency, "llm"

    # ------------------------------------------------------------------

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        for fence in ("```json", "```"):
            if raw.startswith(fence):
                raw = raw[len(fence):]
        if raw.endswith("```"):
            raw = raw[:-3]
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return {}