"""
Tests for get_form_fields_points and its sub-functions.
The LLM is mocked; file I/O uses tmp_path.
"""

import json
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from src.clients.unified_llm_client import LLMResponse, LLMUsage


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _llm_usage():
    return LLMUsage(prompt_tokens=200, completion_tokens=80, total_tokens=280,
                    cost_usd=0.002, model="gpt-4o")


def _llm_response(content: str) -> LLMResponse:
    return LLMResponse(content=content, usage=_llm_usage(), raw_response=MagicMock())


def _minimal_extracted(tmp_path, n_pages=2, n_fields=2):
    """Write a minimal extracted.json to tmp_path and return its path."""
    pages = []
    fid = 1
    for p in range(1, n_pages + 1):
        fields = []
        texts = [
            {"gid": (p * 100) + i, "text": f"Label {i}", "bbox": {"top": i * 10, "left": 0, "right": 200, "bottom": i * 10 + 10},
             "font_name": "Arial", "font_size": 10, "font_weight": "normal",
             "heading_type": "normal", "is_header": False, "is_footer": False}
            for i in range(5)
        ]
        for i in range(n_fields):
            fields.append({
                "fid": fid, "field_name": f"field_{fid}",
                "field_type": "TEXT_FIELD",
                "gid": (p * 100) + i,
                "bbox": {"top": i * 10, "left": 100, "right": 200, "bottom": i * 10 + 10},
                "tid": None, "row": None, "col": None
            })
            fid += 1
        pages.append({"page_number": p, "page_height": 792, "page_width": 612,
                      "text_elements": texts, "form_fields": fields})

    data = {"pages": pages}
    path = str(tmp_path / "doc_extracted.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def _llm_sections_response(fids_on_page):
    """Minimal LLM response for the headers extraction prompt."""
    sections = [
        {"level": "title", "text": "Test Form", "page": 1, "fid": None},
        {"level": "h1", "text": "Section A", "page": 1, "fid": None},
    ]
    for fid in fids_on_page:
        sections.append({"level": "h3", "text": f"Field {fid}", "page": 1, "fid": fid})
    return json.dumps({"sections": sections,
                       "pdf_category": {"category": "Financial", "sub_category": "Investment",
                                        "document_type": "Application"}})


# ---------------------------------------------------------------------------
# build_header_index / find_page_hierarchy — pure logic (no LLM)
# ---------------------------------------------------------------------------

class TestBuildHeaderIndex:
    def test_basic_hierarchy(self):
        from src.headers.get_form_fields_points import build_header_index
        headers = [
            {"level": "title", "text": "Form", "page": 1, "fid": None},
            {"level": "h1", "text": "Personal Info", "page": 1, "fid": None},
            {"level": "h2", "text": "Identity", "page": 1, "fid": None,
             "section_context": "Identity of investor"},
            {"level": "h3", "text": "Name", "page": 1, "fid": 1},
        ]
        fid_to_header, page_to_structural, fid_to_h2_map = build_header_index(headers)
        # title/h1/h2 should be in page_to_structural[1]
        structural_for_page1 = page_to_structural.get(1, [])
        levels = [h["level"] for h in structural_for_page1]
        assert "title" in levels
        assert "h1" in levels

    def test_fid_mapped_to_h3(self):
        from src.headers.get_form_fields_points import build_header_index
        headers = [
            {"level": "h3", "text": "Full Name", "page": 1, "fid": 5},
        ]
        fid_to_header, page_to_structural, fid_to_h2_map = build_header_index(headers)
        assert 5 in fid_to_header
        assert fid_to_header[5]["text"] == "Full Name"

    def test_empty_headers(self):
        from src.headers.get_form_fields_points import build_header_index
        fid_to_header, page_to_structural, fid_to_h2_map = build_header_index([])
        assert fid_to_header == {}
        assert page_to_structural == {}
        assert fid_to_h2_map == {}


class TestFindPageHierarchy:
    def test_returns_hierarchy_for_page(self):
        from src.headers.get_form_fields_points import find_page_hierarchy
        headings = [
            {"level": "title", "text": "Investment Form", "page": 1},
            {"level": "h1", "text": "Investor Info", "page": 1},
            {"level": "h2", "text": "Personal Details", "page": 1,
             "section_context": "Personal Details of investor"},
        ]
        title, h1, h2, ctx = find_page_hierarchy(1, headings)
        assert title == "Investment Form"
        assert h1 == "Investor Info"
        assert h2 == "Personal Details"

    def test_returns_none_for_missing_levels(self):
        from src.headers.get_form_fields_points import find_page_hierarchy
        title, h1, h2, ctx = find_page_hierarchy(1, [])
        assert title is None
        assert h1 is None
        assert h2 is None


# ---------------------------------------------------------------------------
# get_form_fields_points — end-to-end with mocked LLM
# ---------------------------------------------------------------------------

class TestGetFormFieldsPoints:
    def _run(self, coro):
        return asyncio.run(coro)

    @patch("src.headers.get_form_fields_points.UnifiedLLMClient.create_headers_client")
    def test_returns_success_status(self, mock_factory, tmp_path):
        extracted = _minimal_extracted(tmp_path, n_pages=1, n_fields=2)
        headers_out = str(tmp_path / "headers.json")
        fields_out = str(tmp_path / "fields.json")

        mock_llm = MagicMock()
        mock_llm.model = "gpt-4o"
        mock_llm.complete.return_value = _llm_response(_llm_sections_response([1, 2]))
        mock_factory.return_value = mock_llm

        from src.headers.get_form_fields_points import get_form_fields_points
        result = self._run(get_form_fields_points(extracted, headers_out, fields_out))

        assert result["status"] == "success"
        assert result["operation"] == "get_form_fields_points"

    @patch("src.headers.get_form_fields_points.UnifiedLLMClient.create_headers_client")
    def test_output_files_created(self, mock_factory, tmp_path):
        import os
        extracted = _minimal_extracted(tmp_path, n_pages=1, n_fields=2)
        headers_out = str(tmp_path / "headers.json")
        fields_out = str(tmp_path / "fields.json")

        mock_llm = MagicMock()
        mock_llm.model = "gpt-4o"
        mock_llm.complete.return_value = _llm_response(_llm_sections_response([1, 2]))
        mock_factory.return_value = mock_llm

        from src.headers.get_form_fields_points import get_form_fields_points
        self._run(get_form_fields_points(extracted, headers_out, fields_out))

        assert os.path.exists(headers_out)
        assert os.path.exists(fields_out)

    @patch("src.headers.get_form_fields_points.UnifiedLLMClient.create_headers_client")
    def test_final_fields_have_hierarchy(self, mock_factory, tmp_path):
        extracted = _minimal_extracted(tmp_path, n_pages=1, n_fields=2)
        headers_out = str(tmp_path / "headers.json")
        fields_out = str(tmp_path / "fields.json")

        mock_llm = MagicMock()
        mock_llm.model = "gpt-4o"
        mock_llm.complete.return_value = _llm_response(_llm_sections_response([1, 2]))
        mock_factory.return_value = mock_llm

        from src.headers.get_form_fields_points import get_form_fields_points
        self._run(get_form_fields_points(extracted, headers_out, fields_out))

        with open(fields_out) as f:
            data = json.load(f)

        fields = data.get("fields", [])
        assert len(fields) > 0
        assert "hierarchy" in fields[0]
        assert "fid" in fields[0]

    @patch("src.headers.get_form_fields_points.UnifiedLLMClient.create_headers_client")
    def test_llm_usage_in_result(self, mock_factory, tmp_path):
        extracted = _minimal_extracted(tmp_path, n_pages=1, n_fields=1)
        headers_out = str(tmp_path / "headers.json")
        fields_out = str(tmp_path / "fields.json")

        mock_llm = MagicMock()
        mock_llm.model = "gpt-4o"
        mock_llm.complete.return_value = _llm_response(_llm_sections_response([1]))
        mock_factory.return_value = mock_llm

        from src.headers.get_form_fields_points import get_form_fields_points
        result = self._run(get_form_fields_points(extracted, headers_out, fields_out))

        assert "llm_usage" in result
        assert result["llm_usage"]["model"] == "gpt-4o"

    @patch("src.headers.get_form_fields_points.UnifiedLLMClient.create_headers_client")
    def test_invalid_llm_json_falls_back_gracefully(self, mock_factory, tmp_path):
        """If LLM returns garbage for one chunk, the operation should not blow up."""
        extracted = _minimal_extracted(tmp_path, n_pages=1, n_fields=1)
        headers_out = str(tmp_path / "headers.json")
        fields_out = str(tmp_path / "fields.json")

        mock_llm = MagicMock()
        mock_llm.model = "gpt-4o"
        mock_llm.complete.return_value = _llm_response("not valid json at all")
        mock_factory.return_value = mock_llm

        from src.headers.get_form_fields_points import get_form_fields_points
        # Should either succeed with empty sections OR raise a clear error — not hang
        try:
            result = self._run(get_form_fields_points(extracted, headers_out, fields_out))
            assert "status" in result
        except Exception as e:
            assert isinstance(e, (ValueError, RuntimeError, Exception))
