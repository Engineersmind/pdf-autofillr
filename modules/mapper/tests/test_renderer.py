"""
Unit tests for src/prompts/renderer.py

Tests the build_messages() cache-splitting logic for Claude vs OpenAI.
No LLM calls — pure message-construction logic.
"""

import pytest
from src.prompts.renderer import build_messages, _CACHE_SPLIT_MARKER


CLAUDE_MODEL = "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"
OPENAI_MODEL = "gpt-4o"
OLLAMA_MODEL = "ollama/llama3.1:8b"


# ---------------------------------------------------------------------------
# Claude — with ##CACHE_SPLIT##
# ---------------------------------------------------------------------------

class TestBuildMessagesClaudeSplit:
    def test_splits_into_two_content_blocks(self):
        prompt = f"static instructions{_CACHE_SPLIT_MARKER}dynamic data"
        msgs = build_messages(CLAUDE_MODEL, prompt)
        user = msgs[0]
        assert user["role"] == "user"
        assert isinstance(user["content"], list)
        assert len(user["content"]) == 2

    def test_static_block_has_cache_control(self):
        prompt = f"static{_CACHE_SPLIT_MARKER}dynamic"
        msgs = build_messages(CLAUDE_MODEL, prompt)
        static_block = msgs[0]["content"][0]
        assert static_block["type"] == "text"
        assert static_block["cache_control"] == {"type": "ephemeral"}

    def test_dynamic_block_has_no_cache_control(self):
        prompt = f"static{_CACHE_SPLIT_MARKER}dynamic"
        msgs = build_messages(CLAUDE_MODEL, prompt)
        dynamic_block = msgs[0]["content"][1]
        assert "cache_control" not in dynamic_block

    def test_static_content_is_rstripped(self):
        # build_messages does static.rstrip() — trailing spaces removed, leading preserved
        prompt = f"  static content  {_CACHE_SPLIT_MARKER}dynamic"
        msgs = build_messages(CLAUDE_MODEL, prompt)
        assert msgs[0]["content"][0]["text"] == "  static content"

    def test_dynamic_content_is_lstripped(self):
        prompt = f"static{_CACHE_SPLIT_MARKER}\ndynamic content"
        msgs = build_messages(CLAUDE_MODEL, prompt)
        assert msgs[0]["content"][1]["text"] == "dynamic content"

    def test_only_splits_on_first_marker(self):
        prompt = f"static{_CACHE_SPLIT_MARKER}mid{_CACHE_SPLIT_MARKER}end"
        msgs = build_messages(CLAUDE_MODEL, prompt)
        # Only one split → two blocks
        assert len(msgs[0]["content"]) == 2
        assert _CACHE_SPLIT_MARKER in msgs[0]["content"][1]["text"]


class TestBuildMessagesClaudeNoSplit:
    def test_no_marker_sends_plain_string(self):
        prompt = "just a regular prompt"
        msgs = build_messages(CLAUDE_MODEL, prompt)
        assert msgs[0]["content"] == "just a regular prompt"

    def test_no_marker_single_message(self):
        msgs = build_messages(CLAUDE_MODEL, "hello")
        assert len(msgs) == 1


class TestBuildMessagesClaudeSystem:
    def test_system_block_has_cache_control(self):
        msgs = build_messages(CLAUDE_MODEL, "prompt", system="system instructions")
        sys_msg = msgs[0]
        assert sys_msg["role"] == "system"
        assert isinstance(sys_msg["content"], list)
        assert sys_msg["content"][0]["cache_control"] == {"type": "ephemeral"}

    def test_system_plus_split_prompt(self):
        prompt = f"static{_CACHE_SPLIT_MARKER}dynamic"
        msgs = build_messages(CLAUDE_MODEL, prompt, system="sys")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert len(msgs[1]["content"]) == 2  # two content blocks


# ---------------------------------------------------------------------------
# OpenAI — marker stripped, plain strings
# ---------------------------------------------------------------------------

class TestBuildMessagesOpenAI:
    def test_marker_stripped_from_prompt(self):
        prompt = f"static{_CACHE_SPLIT_MARKER}dynamic"
        msgs = build_messages(OPENAI_MODEL, prompt)
        assert _CACHE_SPLIT_MARKER not in msgs[0]["content"]
        assert msgs[0]["content"] == "staticdynamic"

    def test_plain_prompt_unchanged(self):
        msgs = build_messages(OPENAI_MODEL, "hello world")
        assert msgs[0]["content"] == "hello world"

    def test_system_is_plain_string(self):
        msgs = build_messages(OPENAI_MODEL, "prompt", system="instructions")
        sys_msg = msgs[0]
        assert sys_msg["role"] == "system"
        assert isinstance(sys_msg["content"], str)
        assert "cache_control" not in sys_msg

    def test_no_content_blocks_for_openai(self):
        prompt = f"a{_CACHE_SPLIT_MARKER}b"
        msgs = build_messages(OPENAI_MODEL, prompt)
        assert isinstance(msgs[0]["content"], str)


class TestBuildMessagesOllama:
    """Ollama is not Claude — should behave like OpenAI (plain strings)."""

    def test_marker_stripped(self):
        prompt = f"static{_CACHE_SPLIT_MARKER}dynamic"
        msgs = build_messages(OLLAMA_MODEL, prompt)
        assert isinstance(msgs[0]["content"], str)
        assert _CACHE_SPLIT_MARKER not in msgs[0]["content"]

    def test_no_cache_control(self):
        msgs = build_messages(OLLAMA_MODEL, "prompt", system="sys")
        assert isinstance(msgs[0]["content"], str)


# ---------------------------------------------------------------------------
# Model detection edge cases
# ---------------------------------------------------------------------------

class TestClaudeModelDetection:
    @pytest.mark.parametrize("model", [
        "claude-3-5-sonnet-20241022",
        "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic/claude-3-opus",
        "CLAUDE-3-HAIKU",
    ])
    def test_detected_as_claude(self, model):
        prompt = f"s{_CACHE_SPLIT_MARKER}d"
        msgs = build_messages(model, prompt)
        assert isinstance(msgs[0]["content"], list)

    @pytest.mark.parametrize("model", [
        "gpt-4o",
        "gpt-4.1",
        "ollama/qwen2.5:14b",
        "azure/gpt-4",
        "vertex_ai/gemini-pro",
    ])
    def test_not_detected_as_claude(self, model):
        prompt = f"s{_CACHE_SPLIT_MARKER}d"
        msgs = build_messages(model, prompt)
        assert isinstance(msgs[0]["content"], str)
