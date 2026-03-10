"""Builds the extraction prompt sent to OpenAI."""
from __future__ import annotations
import json


class PromptBuilder:
    """Builds the LLM extraction prompt from document text and schema."""

    VERSION = "1.0"

    def build(self, document_text: str, schema: dict) -> str:
        return f"""You are an extraction engine.

STRICT RULES:
- Follow the schema exactly.
- Preserve all nested objects.
- Do NOT hallucinate — only extract what is present.
- Missing or unclear fields => "" (empty string) or false (boolean).

SCHEMA:
{json.dumps(schema, indent=2)}

DOCUMENT CONTENT:
\"\"\"
{document_text}
\"\"\"

Return ONLY valid JSON in this exact shape, nothing else:
{{
  "filled_form_keys": <your extracted dict matching the schema>
}}"""
