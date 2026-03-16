"""
Tests for config loading and path building.
"""

import os
from pathlib import Path
import pytest

from src.configs.file_config import get_file_config


def test_config_loading():
    """Config loads without error and source_type is readable."""
    config = get_file_config()
    source_type = config.get_source_type()
    assert source_type in ("local", "aws", "azure", "gcp"), f"Unexpected source_type: {source_type}"


def test_path_building():
    """Processing paths can be built from config."""
    config = get_file_config()

    user_id = 553
    session_id = "086d6670-81e5-47f4-aecb-e4f7c3ba2a83"
    pdf_doc_id = 990

    source_pdf = config.get_source_input_path("pdf", user_id, session_id, pdf_doc_id)
    assert source_pdf, "Expected a non-empty PDF path"

    source_json = config.get_source_input_path("json", user_id, session_id, pdf_doc_id)
    assert source_json, "Expected a non-empty JSON path"

    processing_paths = config.get_all_processing_paths(user_id, session_id, pdf_doc_id)
    assert len(processing_paths) > 0, "Expected at least one processing path"

    output_pdf = config.get_source_output_path("filled_pdf", user_id, session_id, pdf_doc_id)
    assert output_pdf, "Expected a non-empty output PDF path"


def test_directory_creation(tmp_path):
    """Directories can be created under tmp_path."""
    dirs = [
        tmp_path / "data" / "input",
        tmp_path / "data" / "output",
        tmp_path / "processing",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        assert d.exists(), f"Failed to create directory: {d}"
