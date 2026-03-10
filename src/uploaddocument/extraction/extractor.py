"""Unified extractor — LLM with fallback, always schema-enforced."""
from __future__ import annotations
from uploaddocument.extraction.llm_extractor import LLMExtractor
from uploaddocument.extraction.fallback_extractor import FallbackExtractor
from uploaddocument.transform.schema_enforcer import enforce_schema
from uploaddocument.transform.address_normalizer import apply_address_normalization


class Extractor:
    """LLMExtractor -> FallbackExtractor on error. Always schema-enforces output."""

    def __init__(self, openai_api_key: str, prompt_builder=None):
        self.llm = LLMExtractor(openai_api_key=openai_api_key, prompt_builder=prompt_builder)
        self.fallback = FallbackExtractor()

    def extract(self, document_text: str, schema: dict, logger=None) -> tuple:
        """
        Returns (cleaned_dict, method) where method is 'llm' or 'fallback'.
        """
        try:
            raw = self.llm.extract(document_text, schema, logger=logger)
            filled = raw.get("filled_form_keys", raw)
            cleaned = enforce_schema(filled, schema)
            cleaned = apply_address_normalization(cleaned)
            return cleaned, "llm"
        except Exception as e:
            if logger:
                logger.log_error(f"LLM extraction failed, using fallback: {e}")
            raw = self.fallback.extract(document_text, schema)
            cleaned = enforce_schema(raw, schema)
            cleaned = apply_address_normalization(cleaned)
            return cleaned, "fallback"
