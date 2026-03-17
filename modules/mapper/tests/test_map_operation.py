"""
Tests for handle_map_operation.

Verifies that the map handler reads 'global_json' (keys-only schema)
via input_handler.get_input('global_json') — NOT 'input_json'.
LLM (SemanticMapper) and file handlers are mocked throughout.
"""

import json
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import src.handlers.operations  # ensure submodule is in sys.modules for @patch


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def map_config(tmp_path):
    cfg = MagicMock()
    cfg.source_type = "local"
    cfg.local_mapped_json = str(tmp_path / "doc_mapped_fields.json")
    cfg.local_radio_json  = str(tmp_path / "radio.json")
    return cfg


def _map_handlers(extracted, global_json):
    """
    Build a mock (input_handler, output_handler) pair for handle_map_operation.
    The handler reads 'extracted_json' and 'global_json' — NOT 'input_json'.
    """
    in_h = MagicMock()
    in_h.get_input.side_effect = lambda key: {
        "extracted_json": extracted,
        "global_json":    global_json,   # map reads global schema, not user data
    }.get(key)
    out_h = MagicMock()
    out_h.save_output.return_value = "/saved/mapped.json"
    return in_h, out_h


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# handle_map_operation
# ---------------------------------------------------------------------------

class TestHandleMapOperation:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.SemanticMapper")
    def test_success_response_shape(self, MockMapper, mock_fh, map_config, tmp_path):
        extracted = str(tmp_path / "extracted.json")
        global_json = str(tmp_path / "schema.json")
        _write_json(extracted, {"pages": [], "fields": []})
        _write_json(global_json, {"firstName": "", "lastName": ""})

        # Pre-create mapped file so shutil.copy2 + json.load in the handler work
        _write_json(map_config.local_mapped_json,
                    {"1": {"predicted_field_name": "firstName", "confidence": 0.9}})

        mock_fh.return_value = _map_handlers(extracted, global_json)
        MockMapper.return_value.process_and_save = AsyncMock(return_value={
            "mapping_path":     map_config.local_mapped_json,
            "radio_groups_path": map_config.local_radio_json,
            "total_fields_mapped": 1,
        })

        from src.handlers.operations import handle_map_operation
        result = self._run(handle_map_operation(
            map_config,
            mapping_config={"llm_model": "gpt-4o", "confidence_threshold": 0.7}
        ))

        assert result["status"] == "success"
        assert result["operation"] == "map"

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.SemanticMapper")
    def test_reads_global_json_not_input_json(self, MockMapper, mock_fh, map_config, tmp_path):
        """
        Critical: the map handler must call get_input('global_json').
        If it called get_input('input_json') it would get None and raise FileNotFoundError.
        """
        extracted = str(tmp_path / "extracted.json")
        global_json = str(tmp_path / "schema.json")
        _write_json(extracted, {"pages": [], "fields": []})
        _write_json(global_json, {"firstName": "", "lastName": ""})
        _write_json(map_config.local_mapped_json,
                    {"1": {"predicted_field_name": "firstName", "confidence": 0.9}})

        # Provide 'global_json' but NOT 'input_json' — handler must succeed
        in_h = MagicMock()
        in_h.get_input.side_effect = lambda key: {
            "extracted_json": extracted,
            "global_json":    global_json,
            # 'input_json' intentionally absent — map must NOT read it
        }.get(key)
        mock_fh.return_value = (in_h, MagicMock(save_output=MagicMock(return_value=None)))
        MockMapper.return_value.process_and_save = AsyncMock(return_value={
            "mapping_path": map_config.local_mapped_json,
            "radio_groups_path": map_config.local_radio_json,
            "total_fields_mapped": 1,
        })

        from src.handlers.operations import handle_map_operation
        result = self._run(handle_map_operation(
            map_config, mapping_config={"llm_model": "gpt-4o"}
        ))
        assert result["status"] == "success"

    @patch("src.handlers.operations.create_file_handlers")
    def test_missing_global_json_raises(self, mock_fh, map_config):
        """Missing global_json → FileNotFoundError (not input_json missing)."""
        in_h = MagicMock()
        in_h.get_input.side_effect = lambda key: {
            "extracted_json": "/some/extracted.json",
            "global_json":    None,   # not available
        }.get(key)
        mock_fh.return_value = (in_h, MagicMock())

        from src.handlers.operations import handle_map_operation
        with pytest.raises(FileNotFoundError):
            self._run(handle_map_operation(
                map_config, mapping_config={"llm_model": "gpt-4o"}
            ))

    @patch("src.handlers.operations.create_file_handlers")
    def test_providing_input_json_instead_of_global_json_raises(self, mock_fh, map_config):
        """
        Providing 'input_json' but not 'global_json' must fail — confirms
        the handler is asking for the right key.
        """
        in_h = MagicMock()
        in_h.get_input.side_effect = lambda key: {
            "extracted_json": "/some/extracted.json",
            "input_json":     "/some/user_data.json",  # wrong key for map phase
            # 'global_json' absent
        }.get(key)
        mock_fh.return_value = (in_h, MagicMock())

        from src.handlers.operations import handle_map_operation
        with pytest.raises(FileNotFoundError):
            self._run(handle_map_operation(
                map_config, mapping_config={"llm_model": "gpt-4o"}
            ))

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.SemanticMapper")
    def test_global_json_passed_to_semantic_mapper(self, MockMapper, mock_fh, map_config, tmp_path):
        """The global_json path must be forwarded to SemanticMapper.process_and_save."""
        extracted = str(tmp_path / "extracted.json")
        global_json = str(tmp_path / "schema.json")
        _write_json(extracted, {"pages": [], "fields": []})
        _write_json(global_json, {"firstName": "", "lastName": ""})
        _write_json(map_config.local_mapped_json,
                    {"1": {"predicted_field_name": "firstName", "confidence": 0.9}})

        mock_fh.return_value = _map_handlers(extracted, global_json)
        process_and_save = AsyncMock(return_value={
            "mapping_path": map_config.local_mapped_json,
            "radio_groups_path": map_config.local_radio_json,
            "total_fields_mapped": 1,
        })
        MockMapper.return_value.process_and_save = process_and_save

        from src.handlers.operations import handle_map_operation
        self._run(handle_map_operation(
            map_config, mapping_config={"llm_model": "gpt-4o"}
        ))

        # Confirm the schema path was passed as input_json_path to the mapper
        call_kwargs = process_and_save.call_args[1]
        assert call_kwargs["input_json_path"] == global_json


# ---------------------------------------------------------------------------
# Key separation: map vs fill
# ---------------------------------------------------------------------------

class TestMapVsFillKeysSeparation:
    """
    Confirms that map and fill use completely different input_handler keys.
    If both used 'input_json', a misconfigured config could silently pass
    user data to the map phase or schema to the fill phase.
    """

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.SemanticMapper")
    @patch("src.handlers.operations.fill_with_java")
    def test_map_and_fill_use_different_keys(
        self, mock_fill_java, MockMapper, mock_fh, tmp_path
    ):
        extracted = str(tmp_path / "extracted.json")
        global_json = str(tmp_path / "schema.json")   # keys only
        user_data = str(tmp_path / "user_data.json")  # actual values
        mapped = str(tmp_path / "doc_mapped_fields.json")
        radio = str(tmp_path / "radio.json")
        embedded = str(tmp_path / "embedded.pdf")
        filled = str(tmp_path / "filled.pdf")

        _write_json(extracted, {"pages": [], "fields": []})
        _write_json(global_json, {"firstName": "", "lastName": ""})
        _write_json(user_data, {"firstName": "Jane", "lastName": "Doe"})
        _write_json(mapped, {"1": {"predicted_field_name": "firstName", "confidence": 0.9}})
        open(embedded, "wb").close()
        open(filled, "wb").close()

        map_cfg = MagicMock(source_type="local", local_mapped_json=mapped, local_radio_json=radio)
        fill_cfg = MagicMock(source_type="local", local_filled_pdf=filled)

        # Map handler: provide global_json (not user_data)
        map_in = MagicMock()
        map_in.get_input.side_effect = lambda k: {
            "extracted_json": extracted,
            "global_json": global_json,      # schema → map
        }.get(k)

        # Fill handler: provide user_data (not global_json)
        fill_in = MagicMock()
        fill_in.get_input.side_effect = lambda k: {
            "embedded_pdf": embedded,
            "input_json": user_data,         # actual data → fill
        }.get(k)

        MockMapper.return_value.process_and_save = AsyncMock(return_value={
            "mapping_path": mapped, "radio_groups_path": radio, "total_fields_mapped": 1
        })
        mock_fill_java.return_value = filled

        from src.handlers.operations import handle_map_operation, handle_fill_operation

        mock_fh.return_value = (map_in, MagicMock(save_output=MagicMock(return_value=None)))
        map_result = self._run(handle_map_operation(map_cfg, mapping_config={"llm_model": "gpt-4o"}))
        assert map_result["status"] == "success"

        mock_fh.return_value = (fill_in, MagicMock(save_output=MagicMock(return_value=filled)))
        fill_result = self._run(handle_fill_operation(fill_cfg))
        assert fill_result["status"] == "success"
