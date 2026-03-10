"""Unit tests for extraction (mocked LLM)."""
import pytest
from unittest.mock import MagicMock, patch
from uploaddocument.extraction.extractor import Extractor
from uploaddocument.extraction.fallback_extractor import FallbackExtractor


SCHEMA = {
    "investor_name_id": "",
    "investor_email_id": "",
    "accredited_check": False,
}

LLM_RESPONSE = {
    "filled_form_keys": {
        "investor_name_id": "John Smith",
        "investor_email_id": "john@example.com",
        "accredited_check": True,
    }
}


def test_llm_extraction_mocked():
    extractor = Extractor(openai_api_key="sk-test")
    with patch.object(extractor.llm, "extract", return_value=LLM_RESPONSE):
        cleaned, method = extractor.extract("Some document text", SCHEMA)
    assert method == "llm"
    assert cleaned["investor_name_id"] == "John Smith"
    assert cleaned["accredited_check"] is True


def test_fallback_on_llm_error():
    extractor = Extractor(openai_api_key="sk-test")
    with patch.object(extractor.llm, "extract", side_effect=Exception("LLM down")):
        cleaned, method = extractor.extract("investor@example.com", SCHEMA)
    assert method == "fallback"
    assert "investor_name_id" in cleaned


def test_fallback_extractor_email():
    fb = FallbackExtractor()
    result = fb.extract("Contact: john@example.com for details", {})
    assert result["investor_email_id"] == "john@example.com"


def test_schema_enforcement_on_llm_output():
    extractor = Extractor(openai_api_key="sk-test")
    bad_response = {"filled_form_keys": {"investor_name_id": "Jane", "accredited_check": "yes"}}
    with patch.object(extractor.llm, "extract", return_value=bad_response):
        cleaned, method = extractor.extract("text", SCHEMA)
    assert cleaned["accredited_check"] is True   # "yes" coerced to True
