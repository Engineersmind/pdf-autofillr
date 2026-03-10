# tests/integration/test_full_conversation.py
"""
Integration test — full conversation flow end to end.
Requires: OPENAI_API_KEY environment variable.
Run with: pytest tests/integration/ -m integration
"""
import os
import pytest

from chatbot import chatbotClient, LocalStorage, FormConfig


@pytest.fixture
def client(tmp_path):
    config_path = "tests/fixtures/configs"
    if not os.path.exists(config_path):
        pytest.skip("Fixture configs not present")
    return chatbotClient(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        storage=LocalStorage(str(tmp_path / "data"), config_path),
        form_config=FormConfig.from_directory(config_path),
        pdf_filler=None,
    )


@pytest.mark.integration
def test_individual_investor_greeting(client):
    """First message should return a greeting."""
    response, complete, data = client.send_message("u1", "s1", "")
    assert response
    assert not complete
    assert data is None


@pytest.mark.integration
def test_investor_type_selection(client):
    """Selecting investor type should move to data collection."""
    client.send_message("u1", "s1", "")     # greeting
    client.send_message("u1", "s1", "no")   # no existing data
    response, complete, _ = client.send_message("u1", "s1", "1")  # Individual
    assert "Individual" in response or "name" in response.lower()
    assert not complete


@pytest.mark.integration
def test_full_individual_flow():
    """
    Simulate a complete Individual investor onboarding session.
    Only runs when OPENAI_API_KEY is set and fixture configs exist.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config_path = "tests/fixtures/configs"
    if not os.path.exists(config_path):
        pytest.skip("Fixture configs not present")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        client = chatbotClient(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            storage=LocalStorage(tmpdir, config_path),
            form_config=FormConfig.from_directory(config_path),
            pdf_filler=None,
        )

        turns = [
            "",        # greeting
            "no",      # no existing data
            "1",       # select Individual
            "My name is John Doe, email john@test.com, SSN 123-45-6789, "
            "registered at 100 Main St, New York, NY 10001, USA, phone +1 2125551234",
            "no",      # no more info upfront
        ]

        for msg in turns:
            response, complete, data = client.send_message("u1", "s_full", msg)
            assert response is not None
            if complete:
                break

        # If session completed, check data
        if complete:
            assert data is not None
            assert data.get("investor_full_legal_name_id") == "John Doe"
            assert data.get("investor_email_id") == "john@test.com"
