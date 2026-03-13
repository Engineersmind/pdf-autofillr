"""
Unit tests for src/mappers/semantic_mapper.py

Focuses on pure-logic methods and LLM-dependent methods (with mocked LLM).
process_and_save() end-to-end is covered in test_integration.py.
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.mappers.semantic_mapper import SemanticMapper
from src.clients.unified_llm_client import LLMResponse, LLMUsage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_llm_usage():
    return LLMUsage(
        prompt_tokens=100, completion_tokens=50, total_tokens=150,
        cost_usd=0.001, model="gpt-4o"
    )


def _make_llm_response(content: str) -> LLMResponse:
    return LLMResponse(content=content, usage=_make_llm_usage(), raw_response=MagicMock())


def _make_mapper(**kwargs) -> SemanticMapper:
    """Create a SemanticMapper with a mocked LLM — no real API calls."""
    with patch("src.clients.unified_llm_client.UnifiedLLMClient.create_from_settings") as mock_factory:
        mock_llm = MagicMock()
        mock_llm.model = "gpt-4o"
        mock_factory.return_value = mock_llm
        mapper = SemanticMapper(**kwargs)
        mapper.llm = mock_llm
    return mapper


@pytest.fixture
def mapper():
    return _make_mapper()


@pytest.fixture
def extracted_data_simple():
    """Minimal extracted data with two TEXT fields."""
    return {
        "pages": [
            {
                "page_number": 1,
                "page_height": 792.0,
                "page_width": 612.0,
                "text_elements": [
                    {"gid": 1, "text": "First Name: [TEXT_FIELD:1]"},
                    {"gid": 2, "text": "Last Name: [TEXT_FIELD:2]"},
                ],
                "form_fields": [
                    {
                        "fid": 1, "field_name": "firstNameField",
                        "field_type": "TEXT_FIELD", "gid": 1,
                        "bbox": {"top": 100, "left": 50, "right": 200, "bottom": 115},
                        "tid": None, "row": None, "col": None
                    },
                    {
                        "fid": 2, "field_name": "lastNameField",
                        "field_type": "TEXT_FIELD", "gid": 2,
                        "bbox": {"top": 130, "left": 50, "right": 200, "bottom": 145},
                        "tid": None, "row": None, "col": None
                    },
                ],
            }
        ]
    }


@pytest.fixture
def extracted_data_with_table():
    """Extracted data containing a table with rows and columns."""
    return {
        "pages": [
            {
                "page_number": 1,
                "page_height": 792.0,
                "page_width": 612.0,
                "text_elements": [],
                "form_fields": [
                    # Table 1, Column 0: rows 0, 1, 2 — all mapped to same key
                    {
                        "fid": 10, "field_name": "nameRow0",
                        "field_type": "TABLE_CELL_FIELD", "gid": 10,
                        "bbox": {"top": 100, "left": 50, "right": 200, "bottom": 115},
                        "tid": 1, "row": 0, "col": 0
                    },
                    {
                        "fid": 11, "field_name": "nameRow1",
                        "field_type": "TABLE_CELL_FIELD", "gid": 11,
                        "bbox": {"top": 120, "left": 50, "right": 200, "bottom": 135},
                        "tid": 1, "row": 1, "col": 0
                    },
                    {
                        "fid": 12, "field_name": "nameRow2",
                        "field_type": "TABLE_CELL_FIELD", "gid": 12,
                        "bbox": {"top": 140, "left": 50, "right": 200, "bottom": 155},
                        "tid": 1, "row": 2, "col": 0
                    },
                    # Table 1, Column 1: rows 0, 1 — DIFFERENT keys (no duplicate)
                    {
                        "fid": 13, "field_name": "amountRow0",
                        "field_type": "TABLE_CELL_FIELD", "gid": 13,
                        "bbox": {"top": 100, "left": 220, "right": 350, "bottom": 115},
                        "tid": 1, "row": 0, "col": 1
                    },
                    {
                        "fid": 14, "field_name": "amountRow1",
                        "field_type": "TABLE_CELL_FIELD", "gid": 14,
                        "bbox": {"top": 120, "left": 220, "right": 350, "bottom": 135},
                        "tid": 1, "row": 1, "col": 1
                    },
                ],
            }
        ]
    }


# ---------------------------------------------------------------------------
# prepare_updated_input_data / with_description
# ---------------------------------------------------------------------------

class TestPrepareInputData:
    def test_returns_keys_only(self, mapper):
        input_data = {"firstName": "John", "lastName": "Doe", "ssn": "123"}
        keys = mapper.prepare_updated_input_data(input_data)
        assert set(keys) == {"firstName", "lastName", "ssn"}
        assert isinstance(keys, list)

    def test_empty_input(self, mapper):
        assert mapper.prepare_updated_input_data({}) == []

    def test_with_description_extracts_descriptions(self, mapper):
        enriched = {
            "firstName": {"value": "John", "description": "First name of investor"},
            "lastName": {"value": "Doe", "description": "Last name of investor"},
        }
        result = mapper.prepare_updated_input_data_with_description(enriched)
        assert result == {
            "firstName": ["First name of investor"],
            "lastName": ["Last name of investor"],
        }

    def test_with_description_skips_missing_description(self, mapper):
        enriched = {
            "firstName": {"value": "John", "description": "First name"},
            "noDesc": {"value": "x"},  # no "description" key
        }
        result = mapper.prepare_updated_input_data_with_description(enriched)
        assert "noDesc" not in result
        assert "firstName" in result

    def test_flatten_enriched_data(self, mapper):
        enriched = {
            "firstName": {"value": "John", "description": "desc"},
            "lastName": {"value": "Doe"},
        }
        flat = mapper.flatten_enriched_data(enriched)
        assert flat == {"firstName": "John", "lastName": "Doe"}


# ---------------------------------------------------------------------------
# chunk_keys
# ---------------------------------------------------------------------------

class TestChunkKeys:
    def test_splits_into_n_chunks(self, mapper):
        keys = list(range(10))
        chunks = list(mapper.chunk_keys(keys, 2))
        # Should produce 2 chunks (each ~5 items)
        assert sum(len(c) for c in chunks) == 10

    def test_single_chunk(self, mapper):
        keys = ["a", "b", "c"]
        chunks = list(mapper.chunk_keys(keys, 1))
        assert len(chunks) == 1
        assert chunks[0] == ["a", "b", "c"]

    def test_more_chunks_than_keys(self, mapper):
        keys = ["a", "b"]
        chunks = list(mapper.chunk_keys(keys, 5))
        # chunk_size = max(1, 2//5) = 1 → each key in its own chunk
        assert sum(len(c) for c in chunks) == 2

    def test_empty_keys(self, mapper):
        chunks = list(mapper.chunk_keys([], 3))
        assert chunks == []


# ---------------------------------------------------------------------------
# remove_duplicate_keys_in_table_columns
# ---------------------------------------------------------------------------

class TestRemoveDuplicateKeysInTableColumns:
    def test_no_duplicates_unchanged(self, mapper, extracted_data_with_table):
        # fids 10, 11, 12 all in same column but mapped to DIFFERENT keys
        mapping = {
            "10": ("beneficiaryName_1", None, 0.9),
            "11": ("beneficiaryName_2", None, 0.85),
            "12": ("beneficiaryName_3", None, 0.8),
        }
        result = mapper.remove_duplicate_keys_in_table_columns(mapping, extracted_data_with_table)
        # No duplicates → all keys preserved
        assert result["10"][0] == "beneficiaryName_1"
        assert result["11"][0] == "beneficiaryName_2"
        assert result["12"][0] == "beneficiaryName_3"

    def test_duplicate_in_same_column_nulled_except_first(self, mapper, extracted_data_with_table):
        # fids 10, 11, 12 in col 0 of table 1 — all mapped to "beneficiaryName"
        mapping = {
            "10": ("beneficiaryName", None, 0.9),   # row 0 — kept
            "11": ("beneficiaryName", None, 0.85),  # row 1 — nulled
            "12": ("beneficiaryName", None, 0.8),   # row 2 — nulled
        }
        result = mapper.remove_duplicate_keys_in_table_columns(mapping, extracted_data_with_table)
        assert result["10"][0] == "beneficiaryName"   # first row kept
        assert result["11"][0] is None
        assert result["12"][0] is None

    def test_duplicate_in_different_columns_kept(self, mapper, extracted_data_with_table):
        # fid 10 (col 0) and fid 13 (col 1) same key — different columns → both kept
        mapping = {
            "10": ("amount", None, 0.9),   # col 0
            "13": ("amount", None, 0.88),  # col 1 — same key but different column
        }
        result = mapper.remove_duplicate_keys_in_table_columns(mapping, extracted_data_with_table)
        assert result["10"][0] == "amount"
        assert result["13"][0] == "amount"

    def test_non_table_fields_unaffected(self, mapper, extracted_data_simple):
        mapping = {
            "1": ("firstName", "John", 0.95),
            "2": ("firstName", "John", 0.85),  # same key but NOT table cells
        }
        result = mapper.remove_duplicate_keys_in_table_columns(mapping, extracted_data_simple)
        # Non-table fields should not be modified
        assert result["1"][0] == "firstName"
        assert result["2"][0] == "firstName"

    def test_null_keys_ignored(self, mapper, extracted_data_with_table):
        mapping = {
            "10": (None, None, 0.0),
            "11": (None, None, 0.0),
        }
        result = mapper.remove_duplicate_keys_in_table_columns(mapping, extracted_data_with_table)
        # Null keys should not trigger duplicate detection
        assert result["10"][0] is None
        assert result["11"][0] is None


# ---------------------------------------------------------------------------
# generate_key_descriptions_bulk
# ---------------------------------------------------------------------------

class TestGenerateKeyDescriptionsBulk:
    def test_calls_llm_and_parses_result(self, mapper):
        llm_json = '{"firstName": "First name of the investor", "lastName": "Last name"}'
        mapper.llm.complete.return_value = _make_llm_response(llm_json)

        result = mapper.generate_key_descriptions_bulk(["firstName", "lastName"], mapper.llm)
        assert result == {"firstName": "First name of the investor", "lastName": "Last name"}

    def test_handles_fenced_llm_response(self, mapper):
        llm_json = '```json\n{"ssn": "Social Security Number"}\n```'
        mapper.llm.complete.return_value = _make_llm_response(llm_json)

        result = mapper.generate_key_descriptions_bulk(["ssn"], mapper.llm)
        assert result["ssn"] == "Social Security Number"

    def test_raises_on_invalid_json(self, mapper):
        mapper.llm.complete.return_value = _make_llm_response("not json at all")
        import json
        with pytest.raises(json.JSONDecodeError):
            mapper.generate_key_descriptions_bulk(["key1"], mapper.llm)


# ---------------------------------------------------------------------------
# _process_chunk_async
# ---------------------------------------------------------------------------

class TestProcessChunkAsync:
    @pytest.fixture
    def chunk_info(self):
        # Keys must match what _process_chunk_async reads: "context", "start_fid", "end_fid"
        return {
            "context": "Name: [TEXT_FIELD:1]\nSSN: [TEXT_FIELD:2]",
            "start_fid": 1,
            "end_fid": 2,
        }

    @pytest.fixture
    def input_data(self):
        return {"firstName": "John", "ssn": "123-45-6789"}

    @pytest.fixture
    def keys_data(self):
        return ["firstName", "ssn"]

    async def _call_chunk(self, mapper, chunk_info, input_data, keys_data, llm_json):
        """Helper: creates Semaphore inside the event loop, runs one chunk."""
        mapper.llm.complete.return_value = _make_llm_response(llm_json)
        semaphore = asyncio.Semaphore(1)
        return await mapper._process_chunk_async(
            "chunk_1", chunk_info, input_data, keys_data,
            "individual", {}, {}, semaphore
        )

    def test_maps_fids_from_llm_response(self, mapper, chunk_info, input_data, keys_data):
        llm_json = '{"1": {"key": "firstName", "con": 0.95}, "2": {"key": "ssn", "con": 0.9}}'
        result = asyncio.run(self._call_chunk(mapper, chunk_info, input_data, keys_data, llm_json))
        assert result["1"] == ("firstName", "John", 0.95)
        assert result["2"] == ("ssn", "123-45-6789", 0.9)

    def test_null_key_maps_to_none_value(self, mapper, chunk_info, input_data, keys_data):
        llm_json = '{"1": {"key": null, "con": 0.0}, "2": {"key": "ssn", "con": 0.9}}'
        result = asyncio.run(self._call_chunk(mapper, chunk_info, input_data, keys_data, llm_json))
        assert result["1"] == (None, None, 0.0)

    def test_key_not_in_input_data_has_none_value(self, mapper, chunk_info, input_data, keys_data):
        llm_json = '{"1": {"key": "unknownKey", "con": 0.7}}'
        result = asyncio.run(self._call_chunk(mapper, chunk_info, input_data, keys_data, llm_json))
        assert result["1"][0] == "unknownKey"
        assert result["1"][1] is None

    def test_invalid_json_returns_empty_result(self, mapper, chunk_info, input_data, keys_data):
        llm_json = "this is not json"
        result = asyncio.run(self._call_chunk(mapper, chunk_info, input_data, keys_data, llm_json))
        assert result == {}

    def test_con_coercion_applied(self, mapper, chunk_info, input_data, keys_data):
        llm_json = '{"1": {"key": "firstName", "con": "0.93"}}'
        result = asyncio.run(self._call_chunk(mapper, chunk_info, input_data, keys_data, llm_json))
        assert result["1"][2] == 0.93
