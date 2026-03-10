"""
Integration test — requires OPENAI_API_KEY set in environment.
Run with: pytest tests/integration/ -v
"""
import os
import tempfile
import pytest

pytestmark = pytest.mark.integration

if not os.getenv("OPENAI_API_KEY"):
    pytest.skip("OPENAI_API_KEY not set", allow_module_level=True)


def test_full_extraction_from_txt(tmp_path):
    from uploaddocument import UploadDocumentClient, LocalStorage, SchemaConfig

    # Write a simple schema
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    import json
    (config_dir / "form_keys.json").write_text(json.dumps({
        "investor_name_id": "",
        "investor_email_id": "",
        "accredited_check": False,
    }))

    # Write a test document
    doc = tmp_path / "investor.txt"
    doc.write_text("Investor: John Smith. Email: john@example.com. Accredited: Yes.")

    client = UploadDocumentClient(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        storage=LocalStorage(data_path=str(tmp_path / "data"), config_path=str(config_dir)),
        schema_config=SchemaConfig.from_directory(str(config_dir)),
        pdf_filler=None,
    )

    result = client.process_document(
        document_path=str(doc),
        user_id="test_user",
        session_id="test_session",
    )

    assert result.success, f"Errors: {result.errors}"
    assert result.fields_extracted > 0
    assert result.method in ("llm", "fallback")
    assert "investor_name_id" in result.extracted_flat
