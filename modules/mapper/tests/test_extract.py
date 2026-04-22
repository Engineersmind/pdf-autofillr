"""Tests for extractors/detailed_fitz.py — DocumentAnalyzer and related helpers."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestDocumentAnalyzer:
    def test_init_defaults(self):
        from pdf_autofillr_mapper.extractors.detailed_fitz import DocumentAnalyzer

        da = DocumentAnalyzer()
        assert da.heading_sequences == []
        assert len(da.pages_with_h1) == 0
        assert len(da.pages_with_h2) == 0
        assert len(da.pages_with_h3) == 0

    def test_font_patterns_default(self):
        from pdf_autofillr_mapper.extractors.detailed_fitz import DocumentAnalyzer

        da = DocumentAnalyzer()
        # Access a missing key — should not raise (defaultdict)
        _ = da.font_patterns[("Arial", 12)]
        assert ("Arial", 12) in da.font_patterns

    def test_style_signatures_default(self):
        from pdf_autofillr_mapper.extractors.detailed_fitz import DocumentAnalyzer

        da = DocumentAnalyzer()
        da.style_signatures[("Arial", 12, True)] += 1
        assert da.style_signatures[("Arial", 12, True)] == 1

    def test_text_occurrences_default(self):
        from pdf_autofillr_mapper.extractors.detailed_fitz import DocumentAnalyzer

        da = DocumentAnalyzer()
        da.text_occurrences["header"].append((1, 0.0))
        assert len(da.text_occurrences["header"]) == 1


class TestDetailedFitzExtractor:
    def test_init_with_no_args(self):
        from pdf_autofillr_mapper.extractors.detailed_fitz import DetailedFitzExtractor

        extractor = DetailedFitzExtractor()
        assert extractor is not None

    def test_extract_raises_on_missing_pdf(self, tmp_path):
        from pdf_autofillr_mapper.extractors.detailed_fitz import DetailedFitzExtractor

        extractor = DetailedFitzExtractor()
        missing = str(tmp_path / "ghost.pdf")
        with pytest.raises((FileNotFoundError, Exception)):
            extractor.extract(missing)

    def test_extract_returns_dict_on_valid_pdf(self, tmp_path):
        from pdf_autofillr_mapper.extractors.detailed_fitz import DetailedFitzExtractor
        import fitz

        # Create a minimal valid PDF with fitz
        pdf_path = str(tmp_path / "test.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Name: ")
        doc.save(pdf_path)
        doc.close()

        extractor = DetailedFitzExtractor()
        result = extractor.extract(pdf_path)
        assert isinstance(result, dict)
