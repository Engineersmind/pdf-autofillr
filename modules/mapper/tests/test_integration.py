"""
Integration-level smoke tests: wire multiple mocked operations together
to verify they hand off data correctly through the pipeline.

All LLM calls, Java processes, and external storage are mocked.
Real file I/O uses tmp_path.
"""

import json
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def _minimal_extracted(tmp_path):
    data = {
        "pages": [{
            "page_number": 1,
            "page_height": 792, "page_width": 612,
            "text_elements": [
                {"gid": 1, "text": "First Name: [TEXT_FIELD:1]",
                 "bbox": {"top": 100, "left": 0, "right": 200, "bottom": 115},
                 "font_name": "Arial", "font_size": 10, "font_weight": "normal",
                 "heading_type": "normal", "is_header": False, "is_footer": False}
            ],
            "form_fields": [{
                "fid": 1, "field_name": "firstNameField", "field_type": "TEXT_FIELD",
                "gid": 1, "bbox": {"top": 100, "left": 100, "right": 200, "bottom": 115},
                "tid": None, "row": None, "col": None
            }]
        }]
    }
    p = str(tmp_path / "doc_extracted.json")
    _write_json(p, data)
    return p


def _minimal_input_keys(tmp_path):
    data = {"firstName": "John", "lastName": "Doe"}
    p = str(tmp_path / "input_keys.json")
    _write_json(p, data)
    return p


# ---------------------------------------------------------------------------
# Extract → Map pipeline (mocked LLM)
# ---------------------------------------------------------------------------

class TestExtractMapPipeline:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.DetailedFitzExtractor")
    @patch("src.handlers.operations.SemanticMapper")
    def test_extract_then_map_produces_output_file(self, MockMapper, MockExt, mock_fh, tmp_path):
        # --- EXTRACT ---
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        extracted = _minimal_extracted(tmp_path)

        extract_cfg = MagicMock()
        extract_cfg.source_type = "local"
        extract_cfg.local_extracted_json = extracted

        extract_in = MagicMock()
        extract_in.get_input.side_effect = lambda k: pdf if k == "input_pdf" else None
        extract_out = MagicMock()
        extract_out.save_output.return_value = extracted

        mock_fh.return_value = (extract_in, extract_out)
        MockExt.return_value.extract.return_value = {"pdf_hash": "abc", "pages": [], "fields": []}

        from src.handlers.operations import handle_extract_operation
        extract_result = self._run(handle_extract_operation(extract_cfg))
        assert extract_result["status"] == "success"

        # --- MAP ---
        mapped_path = str(tmp_path / "doc_mapped_fields.json")
        radio_path = str(tmp_path / "radio.json")
        input_keys = _minimal_input_keys(tmp_path)
        # Pre-create the mapped file (process_and_save is mocked, so the handler's
        # shutil.copy2 + json.load need a real file to read from)
        _write_json(mapped_path, {"1": {"predicted_field_name": "firstName", "confidence": 0.9}})

        map_cfg = MagicMock()
        map_cfg.source_type = "local"
        map_cfg.local_mapped_json = mapped_path
        map_cfg.local_radio_json = radio_path

        map_in = MagicMock()
        map_in.get_input.side_effect = lambda k: {
            "extracted_json": extracted, "input_json": input_keys
        }.get(k)
        map_out = MagicMock()
        map_out.save_output.return_value = mapped_path
        mock_fh.return_value = (map_in, map_out)

        mapper_inst = MockMapper.return_value
        mapper_inst.process_and_save = AsyncMock(return_value={
            "mapping_path": mapped_path,
            "radio_groups_path": radio_path,
            "total_fields_mapped": 1
        })

        from src.handlers.operations import handle_map_operation
        map_result = self._run(handle_map_operation(
            map_cfg,
            mapping_config={"llm_model": "gpt-4o", "confidence_threshold": 0.7}
        ))
        assert map_result["status"] == "success"


# ---------------------------------------------------------------------------
# Embed → Fill pipeline (mocked Java)
# ---------------------------------------------------------------------------

class TestEmbedFillPipeline:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.run_embed_java_stage")
    @patch("src.handlers.operations.fill_with_java")
    def test_embed_then_fill(self, mock_fill_java, mock_embed_java, mock_fh, tmp_path):
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        extracted = str(tmp_path / "ext.json"); _write_json(extracted, {})
        mapped = str(tmp_path / "mapped.json"); _write_json(mapped, {})
        radio = str(tmp_path / "radio.json"); _write_json(radio, {})
        embedded = str(tmp_path / "embedded.pdf"); open(embedded, "wb").close()
        filled = str(tmp_path / "filled.pdf"); open(filled, "wb").close()
        input_json = str(tmp_path / "data.json"); _write_json(input_json, {})

        # EMBED
        embed_cfg = MagicMock()
        embed_cfg.source_type = "local"
        embed_cfg.local_mapped_json = mapped
        embed_cfg.local_radio_json = radio
        embed_cfg.local_embedded_pdf = embedded
        embed_cfg.dest_embedded_pdf = embedded

        embed_in = MagicMock()
        embed_in.get_input.side_effect = lambda k: {
            "input_pdf": pdf, "extracted_json": extracted
        }.get(k)
        embed_out = MagicMock()
        embed_out.save_output.return_value = embedded
        mock_fh.return_value = (embed_in, embed_out)
        mock_embed_java.return_value = embedded

        from src.handlers.operations import handle_embed_operation
        embed_result = self._run(handle_embed_operation(embed_cfg))
        assert embed_result["status"] == "success"

        # FILL
        fill_cfg = MagicMock()
        fill_cfg.source_type = "local"
        fill_cfg.local_filled_pdf = filled

        fill_in = MagicMock()
        fill_in.get_input.side_effect = lambda k: {
            "embedded_pdf": embedded, "input_json": input_json
        }.get(k)
        fill_out = MagicMock()
        fill_out.save_output.return_value = filled
        mock_fh.return_value = (fill_in, fill_out)
        mock_fill_java.return_value = filled

        from src.handlers.operations import handle_fill_operation
        fill_result = self._run(handle_fill_operation(fill_cfg))
        assert fill_result["status"] == "success"
        assert fill_result["operation"] == "fill"


# ---------------------------------------------------------------------------
# Full pipeline: Extract → Map → Embed → Fill (all mocked)
# ---------------------------------------------------------------------------

class TestFullPipelineSmoke:
    """End-to-end smoke test: all four stages chained, all I/O mocked."""

    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.handlers.operations.create_file_handlers")
    @patch("src.handlers.operations.DetailedFitzExtractor")
    @patch("src.handlers.operations.SemanticMapper")
    @patch("src.handlers.operations.run_embed_java_stage")
    @patch("src.handlers.operations.fill_with_java")
    def test_all_four_stages_return_success(
        self, mock_fill_java, mock_embed_java, MockMapper, MockExt, mock_fh, tmp_path
    ):
        # Shared file paths
        pdf = str(tmp_path / "form.pdf"); open(pdf, "wb").close()
        extracted = str(tmp_path / "ext.json"); _write_json(extracted, {"pages": [], "fields": []})
        # Must end with _mapped_fields.json so handle_map_operation can derive semantic_path
        mapped = str(tmp_path / "doc_mapped_fields.json")
        _write_json(mapped, {"1": {"predicted_field_name": "firstName", "confidence": 0.9}})
        radio = str(tmp_path / "radio.json"); _write_json(radio, {})
        embedded = str(tmp_path / "embedded.pdf"); open(embedded, "wb").close()
        filled = str(tmp_path / "filled.pdf"); open(filled, "wb").close()
        input_keys = _minimal_input_keys(tmp_path)

        def _cfg(source_type="local", **attrs):
            c = MagicMock(); c.source_type = source_type
            for k, v in attrs.items():
                setattr(c, k, v)
            return c

        def _in_h(**mapping):
            h = MagicMock()
            h.get_input.side_effect = lambda k: mapping.get(k)
            return h

        def _out_h(ret):
            h = MagicMock(); h.save_output.return_value = ret
            return h

        from src.handlers.operations import (
            handle_extract_operation, handle_map_operation,
            handle_embed_operation, handle_fill_operation,
        )

        # 1. EXTRACT
        mock_fh.return_value = (_in_h(input_pdf=pdf), _out_h(extracted))
        MockExt.return_value.extract.return_value = {"pdf_hash": "h1", "pages": [], "fields": []}
        r1 = self._run(handle_extract_operation(_cfg(local_extracted_json=extracted)))
        assert r1["status"] == "success"

        # 2. MAP
        mock_fh.return_value = (_in_h(extracted_json=extracted, input_json=input_keys), _out_h(mapped))
        MockMapper.return_value.process_and_save = AsyncMock(return_value={"mapping_path": mapped, "radio_groups_path": radio, "total_fields_mapped": 1})
        r2 = self._run(handle_map_operation(
            _cfg(local_mapped_json=mapped, local_radio_json=radio),
            mapping_config={"llm_model": "gpt-4o"}
        ))
        assert r2["status"] == "success"

        # 3. EMBED
        mock_fh.return_value = (_in_h(input_pdf=pdf, extracted_json=extracted), _out_h(embedded))
        mock_embed_java.return_value = embedded
        r3 = self._run(handle_embed_operation(
            _cfg(local_mapped_json=mapped, local_radio_json=radio,
                 local_embedded_pdf=embedded, dest_embedded_pdf=embedded)
        ))
        assert r3["status"] == "success"

        # 4. FILL
        mock_fh.return_value = (_in_h(embedded_pdf=embedded, input_json=input_keys), _out_h(filled))
        mock_fill_java.return_value = filled
        r4 = self._run(handle_fill_operation(_cfg(local_filled_pdf=filled)))
        assert r4["status"] == "success"
