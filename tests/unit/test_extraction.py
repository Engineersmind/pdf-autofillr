# tests/unit/test_extraction.py
import json
import pytest
from unittest.mock import patch, MagicMock
from chatbot.extraction.llm_extractor import LLMExtractor
from chatbot.extraction.fallback_extractor import FallbackExtractor
from chatbot.extraction.prompt_builder import PromptBuilder


# ── LLMExtractor ─────────────────────────────────────────────────────

class TestLLMExtractor:

    def test_filters_unknown_fields(self):
        """LLM response with unknown fields should be filtered out."""
        extractor = LLMExtractor(openai_api_key="sk-test")

        with patch.object(extractor, "llm") as mock_llm:
            mock_llm.invoke.return_value = MagicMock(
                content=json.dumps({
                    "investor_full_legal_name_id": "John Doe",
                    "unknown_field_xyz": "should be filtered",
                })
            )

            result = extractor.extract(
                user_input="My name is John Doe",
                conversation_history="",
                live_fill_flat={"investor_full_legal_name_id": ""},
                meta_form_keys={},
            )

        assert "investor_full_legal_name_id" in result
        assert result["investor_full_legal_name_id"] == "John Doe"
        assert "unknown_field_xyz" not in result

    def test_handles_json_parse_error(self):
        """Malformed LLM response should return empty dict."""
        extractor = LLMExtractor(openai_api_key="sk-test")

        with patch.object(extractor, "llm") as mock_llm:
            mock_llm.invoke.return_value = MagicMock(content="not json at all")
            result = extractor.extract(
                user_input="hello",
                conversation_history="",
                live_fill_flat={"investor_email_id": ""},
                meta_form_keys={},
            )

        assert result == {}

    def test_strips_markdown_fences(self):
        extractor = LLMExtractor(openai_api_key="sk-test")
        raw = '```json\n{"investor_email_id": "test@test.com"}\n```'

        with patch.object(extractor, "llm") as mock_llm:
            mock_llm.invoke.return_value = MagicMock(content=raw)
            result = extractor.extract(
                user_input="email is test@test.com",
                conversation_history="",
                live_fill_flat={"investor_email_id": ""},
                meta_form_keys={},
            )

        assert result.get("investor_email_id") == "test@test.com"


# ── FallbackExtractor ─────────────────────────────────────────────────

class TestFallbackExtractor:

    def test_extracts_email(self):
        extractor = FallbackExtractor()
        result = extractor.extract(
            user_input="my email is john@example.com",
            live_fill_flat={"investor_email_id": ""},
        )
        assert result.get("investor_email_id") == "john@example.com"

    def test_extracts_phone(self):
        extractor = FallbackExtractor()
        result = extractor.extract(
            user_input="phone: +1 212 555 1234",
            live_fill_flat={"investor_telephone_id": ""},
        )
        assert "investor_telephone_id" in result

    def test_extracts_zip(self):
        extractor = FallbackExtractor()
        result = extractor.extract(
            user_input="zip code 10001",
            live_fill_flat={"address_registered_zip_id": ""},
        )
        assert result.get("address_registered_zip_id") == "10001"

    def test_no_false_positives(self):
        extractor = FallbackExtractor()
        result = extractor.extract(
            user_input="hello how are you",
            live_fill_flat={"investor_full_legal_name_id": ""},
        )
        assert result == {}


# ── PromptBuilder ─────────────────────────────────────────────────────

class TestPromptBuilder:

    def test_build_includes_user_input(self):
        builder = PromptBuilder()
        prompt = builder.build(
            form_keys={"investor_full_legal_name_id": ""},
            meta_form_keys={},
            mandatory_flat={},
            investor_type="Individual",
            conversation_history="",
            user_input="My name is Alice",
        )
        assert "Alice" in prompt

    def test_build_includes_field_keys(self):
        builder = PromptBuilder()
        prompt = builder.build(
            form_keys={"investor_email_id": ""},
            meta_form_keys={},
            mandatory_flat={},
            investor_type="Individual",
            conversation_history="",
            user_input="test",
        )
        assert "investor_email_id" in prompt

    def test_version_tracked(self):
        builder = PromptBuilder(version="v2.1.0")
        assert builder.version == "v2.1.0"
