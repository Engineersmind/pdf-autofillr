"""LLM-based extractor — calls OpenAI via requests (same as Lambda extractor_logic.py)."""
from __future__ import annotations
import json
import time
import requests
from uploaddocument.extraction.prompt_builder import PromptBuilder


class LLMExtractor:
    """Calls gpt-4.1-mini to extract structured data from document text."""

    MODEL = "gpt-4.1-mini"
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, openai_api_key: str, prompt_builder=None):
        self.openai_api_key = openai_api_key
        self.prompt_builder = prompt_builder or PromptBuilder()

    def extract(self, document_text: str, schema: dict, logger=None) -> dict:
        """Call OpenAI and return the raw extracted dict."""
        prompt = self.prompt_builder.build(document_text, schema)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}",
        }
        payload = {
            "model": self.MODEL,
            "temperature": 0,
            "max_tokens": 4000,
            "messages": [
                {"role": "system", "content": "You are a JSON extraction engine. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        }
        if logger:
            logger.log_api_request(
                operation="openai_extraction", url=self.API_URL,
                headers={"Authorization": "Bearer ***REDACTED***"},
                payload={"model": self.MODEL, "prompt_length": len(prompt)},
            )
        start = time.time()
        resp = requests.post(self.API_URL, headers=headers, json=payload, timeout=120)
        duration = round(time.time() - start, 3)
        resp.raise_for_status()
        result_str = resp.json()["choices"][0]["message"]["content"]
        if logger:
            logger.log_api_response(
                operation="openai_extraction", status_code=resp.status_code,
                response_data={"response_length": len(result_str)}, duration_seconds=duration,
            )
        # Strip markdown fences if present
        if "```" in result_str:
            result_str = result_str.split("```")[1]
            if result_str.startswith("json"):
                result_str = result_str[4:]
        return json.loads(result_str.strip())
