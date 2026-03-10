# tests/unit/test_storage_local.py
import pytest
import tempfile
import os
from chatbot.storage.local_storage import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(data_path=str(tmp_path / "data"), config_path=str(tmp_path / "configs"))


class TestLocalStorage:

    def test_session_state_roundtrip(self, storage):
        state = {"state": "init", "user_id": "u1", "live_fill_flat": {}}
        storage.save_session_state("u1", "s1", state)
        loaded = storage.get_session_state("u1", "s1")
        assert loaded == state

    def test_get_nonexistent_session_returns_none(self, storage):
        assert storage.get_session_state("nobody", "no_session") is None

    def test_final_output_flat_roundtrip(self, storage):
        data = {"investor_full_legal_name_id": "Alice Smith"}
        storage.save_final_output_flat("u1", "s1", data)
        loaded = storage.get_final_output_flat("u1", "s1")
        assert loaded == data

    def test_user_integrated_info_roundtrip(self, storage):
        info = {"investor_email_id": "alice@test.com"}
        storage.save_user_integrated_info("u1", info)
        loaded = storage.get_user_integrated_info("u1")
        assert loaded == info

    def test_list_sessions(self, storage):
        storage.save_session_state("u1", "s1", {})
        storage.save_session_state("u1", "s2", {})
        sessions = storage.list_user_sessions("u1")
        assert set(sessions) == {"s1", "s2"}

    def test_delete_session(self, storage):
        storage.save_session_state("u1", "s1", {"state": "init"})
        storage.delete_session("u1", "s1")
        assert storage.get_session_state("u1", "s1") is None

    def test_debug_conversation_roundtrip(self, storage):
        debug_data = {"entries": [{"message": "test"}]}
        storage.save_debug_conversation("u1", "s1", debug_data)
        loaded = storage.get_debug_conversation("u1", "s1")
        assert loaded == debug_data
