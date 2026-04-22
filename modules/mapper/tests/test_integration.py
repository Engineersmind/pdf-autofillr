"""Integration-style tests covering cross-module interactions and hash cache utilities."""

import json
import pytest
from pathlib import Path


class TestHashCacheRoundTrip:
    async def test_cache_miss_on_empty_registry(self, tmp_path):
        from pdf_autofillr_mapper.utils.hash_cache import check_hash_cache

        result = await check_hash_cache("abc123", str(tmp_path / "registry.json"))
        assert result is None

    async def test_save_and_retrieve_cache_entry(self, tmp_path):
        from pdf_autofillr_mapper.utils.hash_cache import check_hash_cache, save_hash_cache

        registry = str(tmp_path / "registry.json")
        embedded = str(tmp_path / "embedded.pdf")
        mapping = str(tmp_path / "mapping.json")
        radio = str(tmp_path / "radio.json")

        Path(embedded).write_bytes(b"%PDF-1.4")
        Path(mapping).write_text("{}")
        Path(radio).write_text("{}")

        await save_hash_cache(
            pdf_hash="deadbeef" * 8,
            cache_registry_path=registry,
            embedded_pdf=embedded,
            mapping_json=mapping,
            radio_groups=radio,
            user_id=1,
            pdf_doc_id=99,
        )

        entry = await check_hash_cache("deadbeef" * 8, registry)
        assert entry is not None
        assert entry["reference_files"]["embedded_pdf"] == embedded

    async def test_cache_miss_for_unknown_hash(self, tmp_path):
        from pdf_autofillr_mapper.utils.hash_cache import check_hash_cache, save_hash_cache

        registry = str(tmp_path / "registry.json")
        embedded = str(tmp_path / "embedded.pdf")
        mapping = str(tmp_path / "mapping.json")
        radio = str(tmp_path / "radio.json")

        Path(embedded).write_bytes(b"%PDF-1.4")
        Path(mapping).write_text("{}")
        Path(radio).write_text("{}")

        await save_hash_cache(
            pdf_hash="aaaa" * 16,
            cache_registry_path=registry,
            embedded_pdf=embedded,
            mapping_json=mapping,
            radio_groups=radio,
            user_id=1,
            pdf_doc_id=1,
        )

        result = await check_hash_cache("bbbb" * 16, registry)
        assert result is None

    async def test_get_cache_stats_on_populated_registry(self, tmp_path):
        from pdf_autofillr_mapper.utils.hash_cache import save_hash_cache, get_cache_stats

        registry = str(tmp_path / "registry.json")
        embedded = str(tmp_path / "e.pdf")
        mapping = str(tmp_path / "m.json")
        radio = str(tmp_path / "r.json")

        Path(embedded).write_bytes(b"%PDF-1.4")
        Path(mapping).write_text("{}")
        Path(radio).write_text("{}")

        await save_hash_cache(
            pdf_hash="cccc" * 16,
            cache_registry_path=registry,
            embedded_pdf=embedded,
            mapping_json=mapping,
            radio_groups=radio,
            user_id=1,
            pdf_doc_id=1,
        )

        stats = await get_cache_stats(registry)
        assert stats["total_entries"] >= 1

    async def test_get_cache_stats_on_missing_registry(self, tmp_path):
        from pdf_autofillr_mapper.utils.hash_cache import get_cache_stats

        stats = await get_cache_stats(str(tmp_path / "ghost.json"))
        assert stats["total_entries"] == 0


class TestStorageSaveJson:
    def test_saves_dict_to_local_path(self, tmp_path):
        from pdf_autofillr_mapper.utils.storage import save_json

        out = str(tmp_path / "out.json")
        result = save_json({"key": "value"}, {"type": "local", "path": out})
        assert result is True
        data = json.loads(Path(out).read_text())
        assert data["key"] == "value"

    def test_raises_on_invalid_config(self):
        from pdf_autofillr_mapper.utils.storage import save_json

        with pytest.raises(ValueError):
            save_json({"k": "v"}, {})

    def test_raises_on_unsupported_type(self, tmp_path):
        from pdf_autofillr_mapper.utils.storage import save_json

        with pytest.raises(ValueError, match="Only 'local'"):
            save_json({"k": "v"}, {"type": "s3", "path": str(tmp_path / "x.json")})

    def test_creates_parent_directories(self, tmp_path):
        from pdf_autofillr_mapper.utils.storage import save_json

        out = str(tmp_path / "deep" / "nested" / "file.json")
        save_json({"x": 1}, {"type": "local", "path": out})
        assert Path(out).exists()


class TestPDFPipelineSmoke:
    def test_pipeline_instantiates(self):
        from pdf_autofillr_mapper.orchestrator import PDFPipeline

        p = PDFPipeline()
        assert p.config == {}

    def test_pipeline_accepts_config(self):
        from pdf_autofillr_mapper.orchestrator import PDFPipeline

        p = PDFPipeline(config={"llm_model": "test-model", "confidence_threshold": 0.8})
        assert p.config["confidence_threshold"] == 0.8
