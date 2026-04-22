"""Tests for mappers/semantic_mapper.py and utils/pdf_hash.py."""

from unittest.mock import patch


class TestNormalizeText:
    def test_strips_whitespace(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_text
        assert normalize_text("  Hello World  ") == "hello world"

    def test_lowercases(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_text
        assert normalize_text("FIRST NAME") == "first name"

    def test_collapses_extra_spaces(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_text
        assert normalize_text("hello   world") == "hello world"

    def test_empty_string(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_text
        assert normalize_text("") == ""

    def test_none_returns_empty(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_text
        assert normalize_text(None) == ""

    def test_removes_special_chars(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_text
        assert normalize_text("first-name:") == "firstname"


class TestNormalizeBbox:
    def test_basic_normalization(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_bbox
        bbox = {"left": 100, "top": 200, "width": 50, "height": 20}
        result = normalize_bbox(bbox, page_width=1000, page_height=1000)
        assert result["left"] == 0.1
        assert result["top"] == 0.2
        assert result["width"] == 0.05
        assert result["height"] == 0.02

    def test_rounds_to_three_decimals(self):
        from pdf_autofillr_mapper.utils.pdf_hash import normalize_bbox
        bbox = {"left": 1, "top": 1, "width": 1, "height": 1}
        result = normalize_bbox(bbox, page_width=3, page_height=3)
        assert result["left"] == round(1 / 3, 3)


class TestCreateBboxHash:
    def test_empty_fields_returns_empty(self):
        from pdf_autofillr_mapper.utils.pdf_hash import create_bbox_hash
        assert create_bbox_hash([], 1000, 1000) == ""

    def test_returns_sha256_hex(self):
        from pdf_autofillr_mapper.utils.pdf_hash import create_bbox_hash
        fields = [{"bbox": {"left": 100, "top": 200, "width": 50, "height": 20}}]
        result = create_bbox_hash(fields, 1000, 1000)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_fields_same_hash(self):
        from pdf_autofillr_mapper.utils.pdf_hash import create_bbox_hash
        fields = [{"bbox": {"left": 100, "top": 200, "width": 50, "height": 20}}]
        h1 = create_bbox_hash(fields, 1000, 1000)
        h2 = create_bbox_hash(fields, 1000, 1000)
        assert h1 == h2

    def test_different_fields_different_hash(self):
        from pdf_autofillr_mapper.utils.pdf_hash import create_bbox_hash
        fields_a = [{"bbox": {"left": 100, "top": 200, "width": 50, "height": 20}}]
        fields_b = [{"bbox": {"left": 300, "top": 400, "width": 50, "height": 20}}]
        assert create_bbox_hash(fields_a, 1000, 1000) != create_bbox_hash(fields_b, 1000, 1000)


class TestSemanticMapperInit:
    def test_init_with_defaults(self):
        from pdf_autofillr_mapper.mappers.semantic_mapper import SemanticMapper
        with patch("pdf_autofillr_mapper.mappers.semantic_mapper.settings"):
            with patch("pdf_autofillr_mapper.mappers.semantic_mapper.get_semantic_mapper_config", return_value={}):
                with patch("pdf_autofillr_mapper.mappers.semantic_mapper.get_chunking_config", return_value={}):
                    mapper = SemanticMapper()
                    assert mapper is not None

    def test_init_with_legacy_method_config(self):
        from pdf_autofillr_mapper.mappers.semantic_mapper import SemanticMapper
        with patch("pdf_autofillr_mapper.mappers.semantic_mapper.settings"):
            with patch("pdf_autofillr_mapper.mappers.semantic_mapper.get_semantic_mapper_config", return_value={}):
                with patch("pdf_autofillr_mapper.mappers.semantic_mapper.get_chunking_config", return_value={}):
                    mapper = SemanticMapper(method_config={"confidence_threshold": 0.8})
                    assert mapper is not None
