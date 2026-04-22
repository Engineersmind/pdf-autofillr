"""Tests for headers/create_rag_files.py."""

import json
import pytest
from pathlib import Path


SAMPLE_FIELDS = [
    {
        "name": "first_name",
        "type": "text",
        "value": "",
        "section": "Personal Info",
        "context": "Enter your first name",
        "page": 1,
    },
    {
        "name": "dob",
        "type": "date",
        "value": "",
        "section": "Personal Info",
        "context": "Date of birth",
        "page": 1,
    },
    {
        "name": "agree_terms",
        "type": "checkbox",
        "value": False,
        "section": "Agreement",
        "context": "I agree to the terms",
        "page": 2,
    },
]


def make_fields_file(tmp_path: Path, fields=None, pdf_category="insurance") -> str:
    path = tmp_path / "final_form_fields.json"
    path.write_text(json.dumps({"fields": fields or SAMPLE_FIELDS, "pdf_category": pdf_category}))
    return str(path)


class TestCreateRagApiFiles:
    async def test_creates_both_output_files(self, tmp_path):
        from pdf_autofillr_mapper.headers.create_rag_files import create_rag_api_files

        fields_path = make_fields_file(tmp_path)
        header_out = str(tmp_path / "header_file.json")
        section_out = str(tmp_path / "section_file.json")

        result = await create_rag_api_files(
            fields_path, header_out, section_out,
            user_id=1, session_id="sess-1", pdf_doc_id=10, pdf_hash="abc123",
        )

        assert Path(header_out).exists()
        assert Path(section_out).exists()
        assert result["header_file"] == header_out
        assert result["section_file"] == section_out

    async def test_header_file_contains_fields(self, tmp_path):
        from pdf_autofillr_mapper.headers.create_rag_files import create_rag_api_files

        fields_path = make_fields_file(tmp_path)
        header_out = str(tmp_path / "header_file.json")
        section_out = str(tmp_path / "section_file.json")

        await create_rag_api_files(
            fields_path, header_out, section_out,
            user_id=1, session_id="sess-1", pdf_doc_id=10, pdf_hash="abc123",
        )

        data = json.loads(Path(header_out).read_text())
        assert isinstance(data, dict)

    async def test_section_file_is_valid_json(self, tmp_path):
        from pdf_autofillr_mapper.headers.create_rag_files import create_rag_api_files

        fields_path = make_fields_file(tmp_path)
        header_out = str(tmp_path / "header_file.json")
        section_out = str(tmp_path / "section_file.json")

        await create_rag_api_files(
            fields_path, header_out, section_out,
            user_id=2, session_id="sess-2", pdf_doc_id=20, pdf_hash="def456",
        )

        data = json.loads(Path(section_out).read_text())
        assert isinstance(data, (dict, list))

    async def test_raises_on_missing_fields_file(self, tmp_path):
        from pdf_autofillr_mapper.headers.create_rag_files import create_rag_api_files

        with pytest.raises((FileNotFoundError, OSError)):
            await create_rag_api_files(
                str(tmp_path / "ghost.json"),
                str(tmp_path / "h.json"),
                str(tmp_path / "s.json"),
                user_id=1, session_id="s", pdf_doc_id=1, pdf_hash="x",
            )

    async def test_empty_fields_list(self, tmp_path):
        from pdf_autofillr_mapper.headers.create_rag_files import create_rag_api_files

        fields_path = make_fields_file(tmp_path, fields=[])
        header_out = str(tmp_path / "header_file.json")
        section_out = str(tmp_path / "section_file.json")

        result = await create_rag_api_files(
            fields_path, header_out, section_out,
            user_id=1, session_id="s", pdf_doc_id=1, pdf_hash="x",
        )
        assert result["header_file"] == header_out
        assert result["section_file"] == section_out


class TestCreateHeaderFile:
    def test_returns_dict(self):
        from pdf_autofillr_mapper.headers.create_rag_files import create_header_file

        result = create_header_file(
            fields=SAMPLE_FIELDS,
            pdf_hash="abc",
            pdf_category="medical",
            user_id=1,
            session_id="s",
            pdf_doc_id=1,
        )
        assert isinstance(result, dict)

    def test_handles_empty_fields(self):
        from pdf_autofillr_mapper.headers.create_rag_files import create_header_file

        result = create_header_file(
            fields=[],
            pdf_hash="abc",
            pdf_category=None,
            user_id=1,
            session_id="s",
            pdf_doc_id=1,
        )
        assert isinstance(result, dict)


class TestCreateSectionFile:
    def test_returns_dict_or_list(self):
        from pdf_autofillr_mapper.headers.create_rag_files import create_section_file

        result = create_section_file(
            fields=SAMPLE_FIELDS,
            pdf_category="insurance",
            user_id=1,
            session_id="s",
            pdf_doc_id=1,
        )
        assert isinstance(result, (dict, list))

    def test_handles_empty_fields(self):
        from pdf_autofillr_mapper.headers.create_rag_files import create_section_file

        result = create_section_file(
            fields=[],
            pdf_category=None,
            user_id=1,
            session_id="s",
            pdf_doc_id=1,
        )
        assert isinstance(result, (dict, list))
