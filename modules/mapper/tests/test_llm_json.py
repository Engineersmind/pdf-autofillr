"""
Unit tests for src/utils/llm_json.py

These tests require no LLM calls and no mocking — pure logic.
"""

import json
import pytest
from src.utils.llm_json import parse_llm_json, FieldMatch, MappingOutput


# ---------------------------------------------------------------------------
# parse_llm_json
# ---------------------------------------------------------------------------

class TestParseLlmJson:
    def test_plain_json(self):
        assert parse_llm_json('{"a": 1}') == {"a": 1}

    def test_fenced_with_json_label(self):
        raw = '```json\n{"key": "value", "con": 0.9}\n```'
        result = parse_llm_json(raw)
        assert result == {"key": "value", "con": 0.9}

    def test_fenced_without_json_label(self):
        raw = '```\n{"x": 42}\n```'
        assert parse_llm_json(raw) == {"x": 42}

    def test_json_with_preamble_text(self):
        raw = 'Here is the result:\n\n{"11": {"key": "name", "con": 0.95}}'
        result = parse_llm_json(raw)
        assert result == {"11": {"key": "name", "con": 0.95}}

    def test_json_with_trailing_explanation(self):
        raw = '{"11": {"key": "name", "con": 0.95}}\nNote: confidence is high.'
        result = parse_llm_json(raw)
        assert result == {"11": {"key": "name", "con": 0.95}}

    def test_nested_json(self):
        raw = '{"sections": [{"fid": 1, "text": "Name"}]}'
        result = parse_llm_json(raw)
        assert result["sections"][0]["fid"] == 1

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("")

    def test_no_json_object_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("Sorry, I could not process this request.")

    def test_malformed_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json('{"key": "value"')  # unclosed brace

    def test_preserves_null_values(self):
        raw = '{"11": {"key": null, "con": 0}}'
        result = parse_llm_json(raw)
        assert result["11"]["key"] is None

    def test_multiline_fenced_json(self):
        raw = """```json
{
  "11": {"key": "firstName", "con": 0.95},
  "12": {"key": null, "con": 0}
}
```"""
        result = parse_llm_json(raw)
        assert len(result) == 2
        assert result["11"]["key"] == "firstName"
        assert result["12"]["key"] is None


# ---------------------------------------------------------------------------
# FieldMatch
# ---------------------------------------------------------------------------

class TestFieldMatch:
    def test_normal_values(self):
        m = FieldMatch(key="investor_name", con=0.92)
        assert m.key == "investor_name"
        assert m.con == 0.92

    def test_defaults(self):
        m = FieldMatch()
        assert m.key is None
        assert m.con == 0.0

    def test_con_coerced_from_string(self):
        m = FieldMatch(key="x", con="0.85")
        assert m.con == 0.85

    def test_con_clamped_above_one(self):
        m = FieldMatch(key="x", con=1.5)
        assert m.con == 1.0

    def test_con_clamped_below_zero(self):
        m = FieldMatch(key="x", con=-0.3)
        assert m.con == 0.0

    def test_con_invalid_string_defaults_to_zero(self):
        m = FieldMatch(key="x", con="high")
        assert m.con == 0.0

    def test_empty_key_becomes_none(self):
        m = FieldMatch(key="", con=0.9)
        assert m.key is None

    def test_literal_null_string_becomes_none(self):
        m = FieldMatch(key="null", con=0.5)
        assert m.key is None

    def test_literal_null_with_whitespace_becomes_none(self):
        m = FieldMatch(key="  NULL  ", con=0.5)
        assert m.key is None

    def test_none_key(self):
        m = FieldMatch(key=None, con=0.0)
        assert m.key is None

    def test_valid_key_preserved(self):
        m = FieldMatch(key="investor_full_name", con=0.95)
        assert m.key == "investor_full_name"


# ---------------------------------------------------------------------------
# MappingOutput
# ---------------------------------------------------------------------------

class TestMappingOutput:
    def test_parse_valid_dict(self):
        data = {
            "11": {"key": "firstName", "con": 0.95},
            "12": {"key": None, "con": 0.0},
        }
        out = MappingOutput.model_validate(data)
        assert len(out) == 2

    def test_iteration_via_items(self):
        data = {"11": {"key": "firstName", "con": 0.9}}
        out = MappingOutput.model_validate(data)
        items = list(out.items())
        assert items[0][0] == "11"
        assert items[0][1].key == "firstName"

    def test_coercion_applied_to_each_field(self):
        data = {
            "11": {"key": "", "con": "0.95"},     # empty key → None, string con
            "12": {"key": "null", "con": 1.9},    # literal null → None, clamped con
        }
        out = MappingOutput.model_validate(data)
        assert out.root["11"].key is None
        assert out.root["11"].con == 0.95
        assert out.root["12"].key is None
        assert out.root["12"].con == 1.0

    def test_empty_root(self):
        out = MappingOutput.model_validate({})
        assert len(out) == 0

    def test_roundtrip_from_parse_llm_json(self):
        raw = '{"11": {"key": "ssn", "con": 0.88}, "12": {"key": null, "con": 0}}'
        parsed = parse_llm_json(raw)
        out = MappingOutput.model_validate(parsed)
        assert out.root["11"].key == "ssn"
        assert out.root["11"].con == 0.88
        assert out.root["12"].key is None
