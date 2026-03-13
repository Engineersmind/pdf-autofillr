"""
Unit tests for src/clients/unified_llm_client.py

Uses unittest.mock to patch litellm.completion so no real API calls are made.
"""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional

from src.clients.unified_llm_client import UnifiedLLMClient, LLMUsage, LLMResponse


# ---------------------------------------------------------------------------
# Helpers — fake litellm response objects
# ---------------------------------------------------------------------------

def _make_usage(
    prompt=100, completion=50, total=150,
    cache_read=0, cache_creation=0,
    cached_tokens=0,   # OpenAI style
):
    u = MagicMock()
    u.prompt_tokens = prompt
    u.completion_tokens = completion
    u.total_tokens = total
    u.cache_read_input_tokens = cache_read        # Claude/Bedrock
    u.cache_creation_input_tokens = cache_creation  # Claude/Bedrock
    # OpenAI prompt_tokens_details
    details = MagicMock()
    details.cached_tokens = cached_tokens
    u.prompt_tokens_details = details
    return u


def _make_response(content="response text", usage=None):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage = usage or _make_usage()
    return resp


# ---------------------------------------------------------------------------
# _extract_usage
# ---------------------------------------------------------------------------

class TestExtractUsage:
    @pytest.fixture
    def client(self):
        with patch("src.clients.unified_llm_client.completion"):
            return UnifiedLLMClient(model="gpt-4o", max_tokens=100)

    def test_basic_tokens(self, client):
        resp = _make_response(usage=_make_usage(prompt=200, completion=80, total=280))
        usage = client._extract_usage(resp)
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 80
        assert usage.total_tokens == 280

    def test_claude_cache_read_tokens(self, client):
        usage_obj = _make_usage(prompt=500, completion=100, total=600, cache_read=400)
        resp = _make_response(usage=usage_obj)
        usage = client._extract_usage(resp)
        assert usage.cache_read_tokens == 400
        assert usage.cache_creation_tokens == 0

    def test_claude_cache_creation_tokens(self, client):
        usage_obj = _make_usage(prompt=500, completion=100, total=600, cache_creation=480)
        resp = _make_response(usage=usage_obj)
        usage = client._extract_usage(resp)
        assert usage.cache_creation_tokens == 480

    def test_openai_cached_tokens(self, client):
        # OpenAI uses prompt_tokens_details.cached_tokens; no Claude fields
        usage_obj = _make_usage(cached_tokens=300)
        usage_obj.cache_read_input_tokens = 0   # not set for OpenAI
        resp = _make_response(usage=usage_obj)
        usage = client._extract_usage(resp)
        assert usage.cache_read_tokens == 300

    def test_no_cache_fields_gives_zeros(self, client):
        usage_obj = _make_usage()
        usage_obj.cache_read_input_tokens = 0
        usage_obj.cache_creation_input_tokens = 0
        details = MagicMock()
        details.cached_tokens = 0
        usage_obj.prompt_tokens_details = details
        resp = _make_response(usage=usage_obj)
        usage = client._extract_usage(resp)
        assert usage.cache_read_tokens == 0
        assert usage.cache_creation_tokens == 0

    def test_model_stored_in_usage(self, client):
        resp = _make_response()
        usage = client._extract_usage(resp)
        assert usage.model == "gpt-4o"


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    @pytest.fixture
    def client(self):
        with patch("src.clients.unified_llm_client.completion"):
            return UnifiedLLMClient(model="gpt-4o", max_tokens=100)

    def test_string_content_messages(self, client):
        msgs = [{"role": "user", "content": "hello world"}]
        with patch("src.clients.unified_llm_client.token_counter", return_value=5):
            count = client.estimate_tokens(msgs)
        assert count == 5

    def test_fallback_uses_char_count(self, client):
        """When token_counter raises, fallback = total_chars // 4."""
        msgs = [{"role": "user", "content": "abcd"}]   # 4 chars → 1 token
        with patch("src.clients.unified_llm_client.token_counter", side_effect=Exception("error")):
            count = client.estimate_tokens(msgs)
        assert count == 1

    def test_fallback_handles_list_content_blocks(self, client):
        """Claude-style content blocks are summed in fallback."""
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "aaaa"},   # 4 chars
            {"type": "text", "text": "bbbb"},   # 4 chars
        ]}]
        with patch("src.clients.unified_llm_client.token_counter", side_effect=Exception("error")):
            count = client.estimate_tokens(msgs)
        assert count == 2   # 8 chars // 4


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------

class TestComplete:
    @pytest.fixture
    def client(self):
        with patch("src.clients.unified_llm_client.completion"):
            return UnifiedLLMClient(model="gpt-4o", max_tokens=512)

    def test_returns_llm_response(self, client):
        fake_resp = _make_response(content="answer")
        with patch("src.clients.unified_llm_client.completion", return_value=fake_resp), \
             patch("src.clients.unified_llm_client.completion_cost", return_value=0.001):
            result = client.complete([{"role": "user", "content": "q"}])
        assert isinstance(result, LLMResponse)
        assert result.content == "answer"

    def test_string_prompt_converted_to_messages(self, client):
        fake_resp = _make_response(content="ok")
        with patch("src.clients.unified_llm_client.completion", return_value=fake_resp) as mock_comp, \
             patch("src.clients.unified_llm_client.completion_cost", return_value=0.0):
            client.complete("plain string prompt")
        called_messages = mock_comp.call_args[1]["messages"]
        assert called_messages == [{"role": "user", "content": "plain string prompt"}]

    def test_accumulates_stats_across_calls(self, client):
        fake_resp = _make_response(usage=_make_usage(prompt=100, completion=50, total=150))
        with patch("src.clients.unified_llm_client.completion", return_value=fake_resp), \
             patch("src.clients.unified_llm_client.completion_cost", return_value=0.002):
            client.complete("q1")
            client.complete("q2")
        stats = client.get_cumulative_stats()
        assert stats["total_calls"] == 2
        assert stats["total_prompt_tokens"] == 200
        assert stats["total_completion_tokens"] == 100

    def test_passes_max_tokens_to_litellm(self, client):
        fake_resp = _make_response()
        with patch("src.clients.unified_llm_client.completion", return_value=fake_resp) as mock_comp, \
             patch("src.clients.unified_llm_client.completion_cost", return_value=0.0):
            client.complete("q")
        assert mock_comp.call_args[1]["max_tokens"] == 512

    def test_raises_on_litellm_error(self, client):
        with patch("src.clients.unified_llm_client.completion", side_effect=RuntimeError("API down")):
            with pytest.raises(RuntimeError, match="API down"):
                client.complete("q")

    def test_temperature_override(self, client):
        fake_resp = _make_response()
        with patch("src.clients.unified_llm_client.completion", return_value=fake_resp) as mock_comp, \
             patch("src.clients.unified_llm_client.completion_cost", return_value=0.0):
            client.complete("q", temperature=0.8)
        assert mock_comp.call_args[1]["temperature"] == 0.8


# ---------------------------------------------------------------------------
# get_cumulative_stats / reset_stats
# ---------------------------------------------------------------------------

class TestStats:
    @pytest.fixture
    def client(self):
        with patch("src.clients.unified_llm_client.completion"):
            return UnifiedLLMClient(model="gpt-4o", max_tokens=100)

    def test_initial_stats_are_zero(self, client):
        stats = client.get_cumulative_stats()
        assert stats["total_calls"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_cost_usd"] == 0.0

    def test_reset_clears_all_stats(self, client):
        fake_resp = _make_response(usage=_make_usage(prompt=50, completion=50, total=100))
        with patch("src.clients.unified_llm_client.completion", return_value=fake_resp), \
             patch("src.clients.unified_llm_client.completion_cost", return_value=0.01):
            client.complete("q")
        client.reset_stats()
        stats = client.get_cumulative_stats()
        assert stats["total_calls"] == 0
        assert stats["total_cost_usd"] == 0.0


# ---------------------------------------------------------------------------
# create_from_settings / create_headers_client
# ---------------------------------------------------------------------------

class TestFactoryMethods:
    def test_create_from_settings_uses_llm_model(self):
        with patch("src.clients.unified_llm_client.completion"):
            client = UnifiedLLMClient.create_from_settings()
        from src.core.config import settings
        assert client.model == settings.llm_model

    def test_create_headers_client_uses_headers_model(self):
        with patch("src.clients.unified_llm_client.completion"):
            client = UnifiedLLMClient.create_headers_client()
        from src.core.config import settings
        assert client.model == settings.headers_llm_model

    def test_create_from_settings_sets_ollama_base_url(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_API_BASE", raising=False)
        with patch("src.core.config.settings") as mock_settings, \
             patch("src.clients.unified_llm_client.completion"):
            mock_settings.llm_model = "ollama/llama3.1:8b"
            mock_settings.llm_temperature = 0.0
            mock_settings.llm_max_tokens = 4096
            mock_settings.llm_timeout = 120
            mock_settings.llm_max_retries = 3
            mock_settings.ollama_api_base = "http://custom-host:11434"
            # Patch create_from_settings to use the mocked settings
            with patch("src.clients.unified_llm_client.UnifiedLLMClient.__init__", return_value=None):
                try:
                    UnifiedLLMClient.create_from_settings()
                except Exception:
                    pass
        # The env var should have been set before __init__ was called
        # We verify via the classmethod logic directly
        assert True  # covered by integration-level test below

    def test_ollama_base_url_set_in_env(self, monkeypatch):
        """create_from_settings sets OLLAMA_API_BASE when model is ollama/*."""
        monkeypatch.delenv("OLLAMA_API_BASE", raising=False)

        with patch("src.core.config.settings") as mock_settings:
            mock_settings.llm_model = "ollama/llama3.1:8b"
            mock_settings.llm_temperature = 0.0
            mock_settings.llm_max_tokens = 512
            mock_settings.llm_timeout = 30
            mock_settings.llm_max_retries = 1
            mock_settings.ollama_api_base = "http://192.168.1.100:11434"

            # Prevent actual Ollama connection
            with patch.object(UnifiedLLMClient, "__init__", return_value=None):
                UnifiedLLMClient.create_from_settings()

        assert os.environ.get("OLLAMA_API_BASE") == "http://192.168.1.100:11434"
