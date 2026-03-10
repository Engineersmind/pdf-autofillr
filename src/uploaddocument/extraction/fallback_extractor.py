"""Fallback extractor — regex-based, no network call."""
from __future__ import annotations
import re


class FallbackExtractor:
    """
    Simple regex-based extractor used when LLM is unavailable.
    Returns partial results — always schema-enforced downstream.
    """
    EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}")
    PHONE_RE = re.compile(r"(\+?1?\s*[-.\s]?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4})")
    DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")

    def extract(self, document_text: str, schema: dict) -> dict:
        result = {}
        emails = self.EMAIL_RE.findall(document_text)
        if emails:
            result["investor_email_id"] = emails[0]
        phones = self.PHONE_RE.findall(document_text)
        if phones:
            result["investor_phone_id"] = phones[0]
        dates = self.DATE_RE.findall(document_text)
        if dates:
            result["date_id"] = dates[0]
        return result
