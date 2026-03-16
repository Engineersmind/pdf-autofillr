"""
Unit tests for src/groupers/group_by_llm.py

Tests context-line extraction, LLM-based grouping, and error handling.
"""

import pytest
from unittest.mock import MagicMock

from src.groupers.group_by_llm import GroupByLLM
from src.clients.unified_llm_client import LLMResponse, LLMUsage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_llm_response(content: str) -> LLMResponse:
    usage = LLMUsage(
        prompt_tokens=80, completion_tokens=40, total_tokens=120,
        cost_usd=0.0005, model="gpt-4o"
    )
    return LLMResponse(content=content, usage=usage, raw_response=MagicMock())


def _make_extracted_data(radio_gids: list[int], text_elements: list[dict]) -> dict:
    """Build minimal extracted_data with RADIOBUTTON fields at given GIDs."""
    fields = [
        {
            "fid": gid,
            "gid": gid,
            "field_type": "RADIOBUTTON",
            "field_name": f"radio_{gid}",
        }
        for gid in radio_gids
    ]
    return {
        "pages": [
            {
                "page_number": 1,
                "form_fields": fields,
                "text_elements": text_elements,
            }
        ]
    }


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.model = "gpt-4o"
    return llm


# ---------------------------------------------------------------------------
# get_context_lines
# ---------------------------------------------------------------------------

class TestGetContextLines:
    def test_collects_text_around_radio_fields(self, mock_llm):
        text_elements = [
            {"gid": 8, "text": "before"},
            {"gid": 9, "text": "label"},
            {"gid": 10, "text": "Option A"},   # radio at gid=10
            {"gid": 11, "text": "Option B"},
            {"gid": 12, "text": "after2"},
            {"gid": 20, "text": "far away"},   # outside window
        ]
        extracted = _make_extracted_data(radio_gids=[10], text_elements=text_elements)
        grouper = GroupByLLM(extracted, llm=mock_llm, field_type="RADIOBUTTON", threshold=2)

        lines = grouper.get_context_lines()
        texts = [l for l in lines]
        assert "Option A" in texts
        assert "Option B" in texts
        assert "label" in texts
        assert "before" in texts
        assert "far away" not in texts

    def test_no_radio_fields_returns_empty(self, mock_llm):
        text_elements = [{"gid": 1, "text": "some text"}]
        extracted = _make_extracted_data(radio_gids=[], text_elements=text_elements)
        grouper = GroupByLLM(extracted, llm=mock_llm, field_type="RADIOBUTTON", threshold=2)
        assert grouper.get_context_lines() == []

    def test_lines_sorted_by_gid(self, mock_llm):
        text_elements = [
            {"gid": 12, "text": "C"},
            {"gid": 10, "text": "A"},
            {"gid": 11, "text": "B"},
        ]
        extracted = _make_extracted_data(radio_gids=[11], text_elements=text_elements)
        grouper = GroupByLLM(extracted, llm=mock_llm, field_type="RADIOBUTTON", threshold=2)
        lines = grouper.get_context_lines()
        assert lines == ["A", "B", "C"]

    def test_threshold_controls_window_size(self, mock_llm):
        text_elements = [
            {"gid": 5, "text": "far_before"},
            {"gid": 9, "text": "near_before"},
            {"gid": 10, "text": "radio"},     # radio at gid 10
            {"gid": 11, "text": "near_after"},
            {"gid": 15, "text": "far_after"},
        ]
        extracted = _make_extracted_data(radio_gids=[10], text_elements=text_elements)

        # threshold=1 → window [9, 10, 11]
        grouper = GroupByLLM(extracted, llm=mock_llm, field_type="RADIOBUTTON", threshold=1)
        lines = grouper.get_context_lines()
        assert "far_before" not in lines
        assert "far_after" not in lines
        assert "near_before" in lines
        assert "near_after" in lines


# ---------------------------------------------------------------------------
# group_fields_from_text
# ---------------------------------------------------------------------------

class TestGroupFieldsFromText:
    def test_parses_valid_llm_response(self, mock_llm):
        response_json = '{"radiobutton_fields": {"investorType": [15, 16, 17]}}'
        mock_llm.complete.return_value = _make_llm_response(response_json)

        extracted = _make_extracted_data(radio_gids=[], text_elements=[])
        grouper = GroupByLLM(extracted, llm=mock_llm, field_type="RADIOBUTTON", threshold=2)

        result = grouper.group_fields_from_text(["Option A [RADIOBUTTON_FIELD:15]"])
        assert result == {"radiobutton_fields": {"investorType": [15, 16, 17]}}

    def test_parses_fenced_response(self, mock_llm):
        fenced = '```json\n{"radiobutton_fields": {"type": [1, 2]}}\n```'
        mock_llm.complete.return_value = _make_llm_response(fenced)

        extracted = _make_extracted_data(radio_gids=[], text_elements=[])
        grouper = GroupByLLM(extracted, llm=mock_llm)
        result = grouper.group_fields_from_text(["any text"])
        assert result == {"radiobutton_fields": {"type": [1, 2]}}

    def test_raises_on_invalid_json(self, mock_llm):
        mock_llm.complete.return_value = _make_llm_response("not valid json response")
        extracted = _make_extracted_data(radio_gids=[], text_elements=[])
        grouper = GroupByLLM(extracted, llm=mock_llm)

        with pytest.raises(RuntimeError, match="not valid JSON"):
            grouper.group_fields_from_text(["text"])

    def test_raises_when_llm_not_initialized(self):
        extracted = _make_extracted_data(radio_gids=[], text_elements=[])
        grouper = GroupByLLM(extracted)   # no llm kwarg

        with pytest.raises(ValueError, match="LLM is not initialized"):
            grouper.group_fields_from_text(["text"])

    def test_raises_on_empty_response(self, mock_llm):
        mock_llm.complete.return_value = _make_llm_response("   ")
        extracted = _make_extracted_data(radio_gids=[], text_elements=[])
        grouper = GroupByLLM(extracted, llm=mock_llm)

        with pytest.raises(ValueError, match="empty"):
            grouper.group_fields_from_text(["text"])

    def test_tracks_llm_usage(self, mock_llm):
        mock_llm.complete.return_value = _make_llm_response('{"radiobutton_fields": {}}')
        extracted = _make_extracted_data(radio_gids=[], text_elements=[])
        grouper = GroupByLLM(extracted, llm=mock_llm)
        grouper.group_fields_from_text(["text"])

        assert grouper.total_llm_calls == 1
        assert grouper.total_prompt_tokens == 80
        assert grouper.total_completion_tokens == 40


# ---------------------------------------------------------------------------
# group() — full flow
# ---------------------------------------------------------------------------

class TestGroupFlow:
    def test_group_returns_groups_and_usage(self, mock_llm):
        # No radio fields → get_context_lines returns [] → no LLM call
        extracted = _make_extracted_data(radio_gids=[], text_elements=[])
        grouper = GroupByLLM(extracted, llm=mock_llm, field_type="RADIOBUTTON", threshold=2)
        result = grouper.group()

        assert "groups" in result
        assert "llm_usage" in result
        assert isinstance(result["groups"], dict)

    def test_group_with_radio_fields_calls_llm(self, mock_llm):
        text_elements = [{"gid": 10, "text": "Yes [RADIOBUTTON_FIELD:10]"}]
        extracted = _make_extracted_data(radio_gids=[10], text_elements=text_elements)

        mock_llm.complete.return_value = _make_llm_response(
            '{"radiobutton_fields": {"confirm": [10]}}'
        )
        grouper = GroupByLLM(extracted, llm=mock_llm, field_type="RADIOBUTTON", threshold=2)
        result = grouper.group()

        mock_llm.complete.assert_called_once()
        # group() stores the full parsed LLM dict as "groups"
        assert "radiobutton_fields" in result["groups"]
        assert "confirm" in result["groups"]["radiobutton_fields"]

    def test_usage_stats_in_result(self, mock_llm):
        text_elements = [{"gid": 10, "text": "Option [RADIOBUTTON_FIELD:10]"}]
        extracted = _make_extracted_data(radio_gids=[10], text_elements=text_elements)
        mock_llm.complete.return_value = _make_llm_response('{"radiobutton_fields": {}}')

        grouper = GroupByLLM(extracted, llm=mock_llm)
        result = grouper.group()

        usage = result["llm_usage"]
        assert usage["model"] == "gpt-4o"
        assert usage["total_calls"] == 1
        assert usage["total_tokens"] == 120
        assert "avg_cost_per_call" in usage
