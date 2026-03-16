"""
Tests for SDKStorageConfig — verifies that global_json and input_json
are stored in separate attributes and never aliased to each other.
"""

import os
import json
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_files(tmp_path):
    """Return (pdf_path, global_json_path, input_json_path) as real files."""
    pdf = tmp_path / "form.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    global_json = tmp_path / "schema.json"
    global_json.write_text(json.dumps({"firstName": "", "lastName": ""}))

    input_json = tmp_path / "user_data.json"
    input_json.write_text(json.dumps({"firstName": "Jane", "lastName": "Doe"}))

    return str(pdf), str(global_json), str(input_json)


# ---------------------------------------------------------------------------
# SDKStorageConfig — construction
# ---------------------------------------------------------------------------

class TestSDKStorageConfigConstruction:
    def test_requires_at_least_one_json(self, tmp_path):
        pdf, _, _ = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        with pytest.raises(ValueError, match="global_json_path or input_json_path"):
            SDKStorageConfig(pdf_path=pdf, output_dir=str(tmp_path))

    def test_embed_config_sets_global_json_only(self, tmp_path):
        """Embed pipeline: local_global_json set, local_input_json = None."""
        pdf, global_json, _ = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            global_json_path=global_json,
            output_dir=str(tmp_path),
        )
        assert os.path.abspath(global_json) == cfg.local_global_json
        assert cfg.local_input_json is None

    def test_fill_config_sets_input_json_only(self, tmp_path):
        """Fill pipeline: local_input_json set, local_global_json = None."""
        pdf, _, input_json = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            input_json_path=input_json,
            output_dir=str(tmp_path),
        )
        assert os.path.abspath(input_json) == cfg.local_input_json
        assert cfg.local_global_json is None

    def test_both_set_independently(self, tmp_path):
        """Both can be provided — each stored in its own attribute."""
        pdf, global_json, input_json = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            global_json_path=global_json,
            input_json_path=input_json,
            output_dir=str(tmp_path),
        )
        assert cfg.local_global_json == os.path.abspath(global_json)
        assert cfg.local_input_json == os.path.abspath(input_json)
        # Confirm they are NOT the same path
        assert cfg.local_global_json != cfg.local_input_json

    def test_global_json_not_aliased_to_input_json(self, tmp_path):
        """The old bug: local_global_json = local_input_json (alias). Must not happen."""
        pdf, global_json, input_json = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            global_json_path=global_json,
            input_json_path=input_json,
            output_dir=str(tmp_path),
        )
        assert cfg.local_global_json != cfg.local_input_json


# ---------------------------------------------------------------------------
# SDKStorageConfig — derived paths
# ---------------------------------------------------------------------------

class TestSDKStorageConfigPaths:
    def test_output_paths_derived_from_pdf_stem(self, tmp_path):
        pdf, global_json, _ = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            global_json_path=global_json,
            output_dir=str(tmp_path),
        )
        stem = "form"
        assert cfg.local_extracted_json.endswith(f"{stem}_extracted.json")
        assert cfg.local_mapped_json.endswith(f"{stem}_mapped_fields.json")
        assert cfg.local_embedded_pdf.endswith(f"{stem}_embedded.pdf")
        assert cfg.local_filled_pdf.endswith(f"{stem}_filled.pdf")

    def test_cloud_paths_all_none(self, tmp_path):
        pdf, global_json, _ = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            global_json_path=global_json,
            output_dir=str(tmp_path),
        )
        assert cfg.s3_input_pdf is None
        assert cfg.s3_input_json is None
        assert cfg.s3_global_json is None

    def test_output_dir_created(self, tmp_path):
        pdf, global_json, _ = _make_files(tmp_path)
        new_dir = str(tmp_path / "new_output")
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            global_json_path=global_json,
            output_dir=new_dir,
        )
        assert os.path.isdir(new_dir)

    def test_default_output_dir_uses_stem(self, tmp_path):
        pdf, global_json, _ = _make_files(tmp_path)
        import tempfile
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(pdf_path=pdf, global_json_path=global_json)
        assert "pdf_mapper_form" in cfg.base_dir

    def test_repr(self, tmp_path):
        pdf, global_json, _ = _make_files(tmp_path)
        from src.configs.sdk import SDKStorageConfig
        cfg = SDKStorageConfig(
            pdf_path=pdf,
            global_json_path=global_json,
            output_dir=str(tmp_path),
        )
        assert "form.pdf" in repr(cfg)
