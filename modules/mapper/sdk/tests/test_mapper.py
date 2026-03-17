"""
Tests for pdf_autofiller_mapper.mapper — PDFMapper (embedded SDK).

All mapper internals (handlers, configs, IniConfigLoader) are mocked —
no real PDF, no real LLM, no Java required.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from pdf_autofiller_mapper.mapper import PDFMapper
from pdf_autofiller_mapper.result import SDKResult
from pdf_autofiller_mapper.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """Ensure env vars don't bleed between tests."""
    monkeypatch.delenv("PDF_AUTOFILLER_CONFIG", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def pdf_and_jsons(tmp_path):
    """Return (pdf_path, global_json_path, input_json_path)."""
    pdf = tmp_path / "form.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    global_json = tmp_path / "schema.json"
    global_json.write_text(json.dumps({"firstName": "", "lastName": ""}))

    input_json = tmp_path / "data.json"
    input_json.write_text(json.dumps({"firstName": "Jane", "lastName": "Doe"}))

    return str(pdf), str(global_json), str(input_json)


def _success_raw(stage_name, **extra):
    return {"status": "success", "output_file": f"/tmp/{stage_name}_out",
            "execution_time": 1.0, **extra}


def _mock_internals(tmp_path):
    """
    Return a 6-tuple matching _import_mapper_internals():
    (handle_extract, handle_map, handle_embed, handle_fill,
     SDKStorageConfig, IniConfigLoader)
    """
    filled = str(tmp_path / "filled.pdf")
    embedded = str(tmp_path / "form_embedded.pdf")
    open(filled, "wb").write(b"%PDF fake filled")
    open(embedded, "wb").write(b"%PDF fake embedded")

    cfg = MagicMock()
    cfg.base_dir = str(tmp_path)
    cfg.local_filled_pdf = filled
    cfg.local_embedded_pdf = embedded

    SDKStorageConfig = MagicMock(return_value=cfg)

    # IniConfigLoader mock — returns a minimal mapping config
    loader_instance = MagicMock()
    loader_instance.get_mapping_config.return_value = {
        "llm_model": "gpt-4o",
        "confidence_threshold": 0.7,
        "chunking_strategy": "page",
        "use_second_mapper": False,
    }
    loader_instance.get_section.return_value = {
        "headers_llm_model": "gpt-4.1",
    }
    IniConfigLoader = MagicMock(return_value=loader_instance)

    handle_extract = AsyncMock(return_value=_success_raw("extract"))
    handle_map = AsyncMock(return_value={
        **_success_raw("map"),
        "mapping": {"1": "firstName", "2": "lastName"},
        "confidence": 0.88,
        "total_fields_mapped": 2,
    })
    handle_embed = AsyncMock(return_value=_success_raw("embed"))
    handle_fill = AsyncMock(return_value={**_success_raw("fill"), "output_file": filled})

    return handle_extract, handle_map, handle_embed, handle_fill, SDKStorageConfig, IniConfigLoader


# ---------------------------------------------------------------------------
# Construction & validation
# ---------------------------------------------------------------------------

class TestPDFMapperInit:
    def test_requires_config_or_model_or_env(self):
        with pytest.raises(ConfigurationError, match="config_path"):
            PDFMapper()

    def test_accepts_llm_model_directly(self):
        mapper = PDFMapper(llm_model="gpt-4o")
        assert mapper._overrides["llm_model"] == "gpt-4o"

    def test_accepts_config_path(self):
        mapper = PDFMapper(config_path="config.ini")
        assert mapper._config_path == "config.ini"

    def test_accepts_env_var_fallback(self, monkeypatch):
        monkeypatch.setenv("PDF_AUTOFILLER_CONFIG", "config.ini")
        mapper = PDFMapper()
        assert mapper._config_path is None  # env var handled by IniConfigLoader

    def test_invalid_cleanup_raises(self):
        with pytest.raises(ConfigurationError, match="cleanup"):
            PDFMapper(llm_model="gpt-4o", cleanup="whenever")

    def test_valid_cleanup_values(self):
        for val in (False, True, "on_success", "on_error"):
            PDFMapper(llm_model="gpt-4o", cleanup=val)

    def test_overrides_stored(self):
        mapper = PDFMapper(
            config_path="config.ini",
            llm_model="ollama/llama3.1:8b",
            headers_llm_model="gpt-4.1",
            confidence_threshold=0.85,
            use_second_mapper=True,
        )
        assert mapper._overrides["llm_model"] == "ollama/llama3.1:8b"
        assert mapper._overrides["headers_llm_model"] == "gpt-4.1"
        assert mapper._overrides["confidence_threshold"] == 0.85
        assert mapper._overrides["use_second_mapper"] is True

    def test_none_overrides_not_stored(self):
        mapper = PDFMapper(llm_model="gpt-4o")
        assert "confidence_threshold" not in mapper._overrides
        assert "headers_llm_model" not in mapper._overrides

    def test_repr(self):
        mapper = PDFMapper(llm_model="gpt-4o", cleanup="on_success")
        r = repr(mapper)
        assert "gpt-4o" in r
        assert "on_success" in r


# ---------------------------------------------------------------------------
# _build_mapping_config
# ---------------------------------------------------------------------------

class TestBuildMappingConfig:
    def test_overrides_win_over_ini(self, tmp_path):
        _, _, _, _, _, IniConfigLoader = _mock_internals(tmp_path)
        # IniConfigLoader returns gpt-4o, we override with bedrock
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals",
                   return_value=(*_mock_internals(tmp_path),)):
            mapper = PDFMapper(
                config_path="config.ini",
                llm_model="bedrock/anthropic.claude-3-5-sonnet",
            )
            cfg = mapper._build_mapping_config()
        assert cfg["llm_model"] == "bedrock/anthropic.claude-3-5-sonnet"

    def test_headers_config_merged_in(self, tmp_path):
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            mapper = PDFMapper(config_path="config.ini")
            cfg = mapper._build_mapping_config()
        assert "headers_llm_model" in cfg

    def test_raises_when_no_llm_model(self, tmp_path):
        internals = list(_mock_internals(tmp_path))
        # Make IniConfigLoader return empty mapping config
        loader = MagicMock()
        loader.get_mapping_config.return_value = {}
        loader.get_section.return_value = {}
        internals[5] = MagicMock(return_value=loader)

        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=tuple(internals)):
            mapper = PDFMapper(config_path="config.ini")
            with pytest.raises(ConfigurationError, match="llm_model"):
                mapper._build_mapping_config()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_missing_pdf_raises(self, tmp_path):
        schema = tmp_path / "schema.json"
        schema.write_text("{}")
        mapper = PDFMapper(llm_model="gpt-4o")
        with pytest.raises(ConfigurationError, match="PDF not found"):
            mapper.make_embed_file("/nonexistent.pdf", str(schema))

    def test_missing_global_json_raises(self, tmp_path):
        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF")
        mapper = PDFMapper(llm_model="gpt-4o")
        with pytest.raises(ConfigurationError, match="not found"):
            mapper.make_embed_file(str(pdf), "/nonexistent_schema.json")

    def test_missing_input_json_raises(self, tmp_path):
        pdf = tmp_path / "form.pdf"
        pdf.write_bytes(b"%PDF")
        mapper = PDFMapper(llm_model="gpt-4o")
        with pytest.raises(ConfigurationError, match="not found"):
            mapper.fill(str(pdf), "/nonexistent_data.json")

    def test_process_missing_pdf_raises(self, tmp_path):
        schema = tmp_path / "schema.json"
        schema.write_text("{}")
        data = tmp_path / "data.json"
        data.write_text("{}")
        mapper = PDFMapper(llm_model="gpt-4o")
        with pytest.raises(ConfigurationError, match="PDF not found"):
            mapper.process("/nonexistent.pdf", str(schema), str(data))


# ---------------------------------------------------------------------------
# make_embed_file
# ---------------------------------------------------------------------------

class TestMakeEmbedFile:
    def test_success_sets_embedded_pdf(self, pdf_and_jsons, tmp_path):
        pdf, global_json, _ = pdf_and_jsons
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals",
                   return_value=_mock_internals(tmp_path)):
            result = PDFMapper(llm_model="gpt-4o").make_embed_file(pdf, global_json)
        assert result.ok
        assert result.embedded_pdf is not None
        assert result.filled_pdf is None   # fill not run

    def test_extract_failure_short_circuits(self, pdf_and_jsons, tmp_path):
        pdf, global_json, _ = pdf_and_jsons
        internals = list(_mock_internals(tmp_path))
        internals[0] = AsyncMock(return_value={"status": "error", "error": "bad PDF"})
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=tuple(internals)):
            result = PDFMapper(llm_model="gpt-4o").make_embed_file(pdf, global_json)
        assert not result.ok
        assert "bad PDF" in result.error
        internals[1].assert_not_called()   # map not called

    def test_map_failure_short_circuits(self, pdf_and_jsons, tmp_path):
        pdf, global_json, _ = pdf_and_jsons
        internals = list(_mock_internals(tmp_path))
        internals[1] = AsyncMock(return_value={"status": "error", "error": "LLM quota"})
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=tuple(internals)):
            result = PDFMapper(llm_model="gpt-4o").make_embed_file(pdf, global_json)
        assert not result.ok
        internals[2].assert_not_called()   # embed not called

    def test_mapping_config_uses_overrides(self, pdf_and_jsons, tmp_path):
        pdf, global_json, _ = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(
                llm_model="ollama/qwen2.5:14b",
                confidence_threshold=0.9,
            ).make_embed_file(pdf, global_json)
        call_mapping_cfg = internals[1].call_args[0][1]
        assert call_mapping_cfg["llm_model"] == "ollama/qwen2.5:14b"
        assert call_mapping_cfg["confidence_threshold"] == 0.9

    def test_embed_config_uses_global_json(self, pdf_and_jsons, tmp_path):
        """SDKStorageConfig must be called with global_json_path (not input_json_path)."""
        pdf, global_json, _ = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(llm_model="gpt-4o").make_embed_file(pdf, global_json)
        call_kwargs = internals[4].call_args[1]
        assert call_kwargs["global_json_path"] == global_json
        assert "input_json_path" not in call_kwargs or call_kwargs.get("input_json_path") is None


# ---------------------------------------------------------------------------
# fill
# ---------------------------------------------------------------------------

class TestFill:
    def test_success_sets_filled_pdf(self, pdf_and_jsons, tmp_path):
        pdf, _, input_json = pdf_and_jsons
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals",
                   return_value=_mock_internals(tmp_path)):
            result = PDFMapper(llm_model="gpt-4o").fill(pdf, input_json)
        assert result.ok
        assert result.filled_pdf is not None
        assert result.embedded_pdf is None

    def test_fill_failure_returns_error(self, pdf_and_jsons, tmp_path):
        pdf, _, input_json = pdf_and_jsons
        internals = list(_mock_internals(tmp_path))
        internals[3] = AsyncMock(return_value={"status": "error", "error": "Java OOM"})
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=tuple(internals)):
            result = PDFMapper(llm_model="gpt-4o").fill(pdf, input_json)
        assert not result.ok
        assert result.filled_pdf is None

    def test_fill_config_uses_input_json(self, pdf_and_jsons, tmp_path):
        """SDKStorageConfig must be called with input_json_path (not global_json_path)."""
        pdf, _, input_json = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(llm_model="gpt-4o").fill(pdf, input_json)
        call_kwargs = internals[4].call_args[1]
        assert call_kwargs["input_json_path"] == input_json
        assert "global_json_path" not in call_kwargs or call_kwargs.get("global_json_path") is None


# ---------------------------------------------------------------------------
# process
# ---------------------------------------------------------------------------

class TestProcess:
    def test_success_sets_both_pdfs(self, pdf_and_jsons, tmp_path):
        pdf, global_json, input_json = pdf_and_jsons
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals",
                   return_value=_mock_internals(tmp_path)):
            result = PDFMapper(llm_model="gpt-4o").process(pdf, global_json, input_json)
        assert result.ok
        assert result.embedded_pdf is not None
        assert result.filled_pdf is not None

    def test_mid_pipeline_failure(self, pdf_and_jsons, tmp_path):
        pdf, global_json, input_json = pdf_and_jsons
        internals = list(_mock_internals(tmp_path))
        internals[2] = AsyncMock(return_value={"status": "error", "error": "embed fail"})
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=tuple(internals)):
            result = PDFMapper(llm_model="gpt-4o").process(pdf, global_json, input_json)
        assert not result.ok
        internals[3].assert_not_called()   # fill not called

    def test_process_two_configs_created(self, pdf_and_jsons, tmp_path):
        """process() must create two SDKStorageConfig objects (embed + fill)."""
        pdf, global_json, input_json = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(llm_model="gpt-4o").process(pdf, global_json, input_json)
        # SDKStorageConfig should have been called twice
        assert internals[4].call_count == 2
        calls = internals[4].call_args_list
        # First call: embed config — global_json_path
        assert calls[0][1]["global_json_path"] == global_json
        # Second call: fill config — input_json_path
        assert calls[1][1]["input_json_path"] == input_json


# ---------------------------------------------------------------------------
# Cleanup behaviour
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_true_deletes_output_dir(self, pdf_and_jsons, tmp_path):
        pdf, global_json, _ = pdf_and_jsons
        out = str(tmp_path / "sdk_output")
        os.makedirs(out)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals",
                   return_value=_mock_internals(tmp_path)):
            mapper = PDFMapper(llm_model="gpt-4o", output_dir=out, cleanup=True)
            # Simulate the cfg.base_dir being tracked
            mapper._session_dirs.add(out)
            mapper._post_op(success=True, cfg=MagicMock(base_dir=out))
        assert not os.path.exists(out)

    def test_cleanup_on_error_keeps_on_success(self, pdf_and_jsons, tmp_path):
        pdf, global_json, _ = pdf_and_jsons
        out = str(tmp_path / "sdk_output2")
        os.makedirs(out)
        cfg_mock = MagicMock(base_dir=out)
        mapper = PDFMapper(llm_model="gpt-4o", output_dir=out, cleanup="on_error")
        mapper._post_op(success=True, cfg=cfg_mock)
        assert os.path.exists(out)   # not deleted on success

    def test_context_manager_cleans_up_on_exit(self, pdf_and_jsons, tmp_path):
        out = str(tmp_path / "ctx_output")
        os.makedirs(out)
        with PDFMapper(llm_model="gpt-4o", cleanup=True) as mapper:
            mapper._session_dirs.add(out)
        assert not os.path.exists(out)

    def test_context_manager_on_success_only(self, pdf_and_jsons, tmp_path):
        out = str(tmp_path / "ctx_err_output")
        os.makedirs(out)
        try:
            with PDFMapper(llm_model="gpt-4o", cleanup="on_success") as mapper:
                mapper._session_dirs.add(out)
                raise ValueError("simulated error")
        except ValueError:
            pass
        assert os.path.exists(out)   # not deleted when exception occurred


# ---------------------------------------------------------------------------
# Individual stage methods (extract / map / embed) — all use global_json
# ---------------------------------------------------------------------------

class TestStageMethods:
    def test_extract_uses_embed_config(self, pdf_and_jsons, tmp_path):
        """extract() must create an embed config (global_json_path kwarg)."""
        pdf, global_json, _ = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(llm_model="gpt-4o").extract(pdf, global_json)
        call_kwargs = internals[4].call_args[1]
        assert call_kwargs.get("global_json_path") == global_json
        assert call_kwargs.get("input_json_path") is None

    def test_map_uses_embed_config(self, pdf_and_jsons, tmp_path):
        """map() must create an embed config (global_json_path kwarg)."""
        pdf, global_json, _ = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(llm_model="gpt-4o").map(pdf, global_json)
        call_kwargs = internals[4].call_args[1]
        assert call_kwargs.get("global_json_path") == global_json
        assert call_kwargs.get("input_json_path") is None

    def test_embed_uses_embed_config(self, pdf_and_jsons, tmp_path):
        """embed() must create an embed config (global_json_path kwarg)."""
        pdf, global_json, _ = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(llm_model="gpt-4o").embed(pdf, global_json)
        call_kwargs = internals[4].call_args[1]
        assert call_kwargs.get("global_json_path") == global_json
        assert call_kwargs.get("input_json_path") is None

    def test_fill_uses_fill_config(self, pdf_and_jsons, tmp_path):
        """fill() must create a fill config (input_json_path kwarg)."""
        pdf, _, input_json = pdf_and_jsons
        internals = _mock_internals(tmp_path)
        with patch("pdf_autofiller_mapper.mapper._import_mapper_internals", return_value=internals):
            PDFMapper(llm_model="gpt-4o").fill(pdf, input_json)
        call_kwargs = internals[4].call_args[1]
        assert call_kwargs.get("input_json_path") == input_json
        assert call_kwargs.get("global_json_path") is None


# ---------------------------------------------------------------------------
# _import_mapper_internals — ConfigurationError when not installed
# ---------------------------------------------------------------------------

class TestImportMapperInternals:
    def test_raises_configuration_error_when_not_installed(self):
        import sys
        with patch.dict(sys.modules, {
            "src": None, "src.handlers": None,
            "src.handlers.operations": None,
            "src.configs": None, "src.configs.sdk": None,
            "src.utils": None, "src.utils.ini_config": None,
        }):
            import pdf_autofiller_mapper.mapper as _mod
            with pytest.raises(ConfigurationError, match="mapper module"):
                _mod._import_mapper_internals()
