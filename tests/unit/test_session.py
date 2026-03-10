# tests/unit/test_session.py
import pytest
from chatbot.core.session import SessionManager
from chatbot.storage.local_storage import LocalStorage


@pytest.fixture
def session_manager(tmp_path):
    storage = LocalStorage(str(tmp_path / "data"), str(tmp_path / "configs"))
    return SessionManager(storage=storage)


class TestSessionManager:

    def test_create_new_session(self, session_manager):
        session = session_manager.create_session("u1", "s1")
        assert session["user_id"] == "u1"
        assert session["session_id"] == "s1"
        assert session["state"] == "init"

    def test_load_or_create_returns_existing(self, session_manager):
        session_manager.create_session("u1", "s1")
        session_manager.storage.save_session_state("u1", "s1", {"state": "data_collection", "user_id": "u1", "session_id": "s1"})
        loaded = session_manager.load_or_create("u1", "s1")
        assert loaded["state"] == "data_collection"

    def test_load_or_create_creates_if_missing(self, session_manager):
        session = session_manager.load_or_create("u_new", "s_new")
        assert session["state"] == "init"

    def test_save_updates_timestamp(self, session_manager):
        session = session_manager.create_session("u1", "s1")
        old_ts = session.get("updated_at")
        import time; time.sleep(0.01)
        session_manager.save("u1", "s1", session)
        loaded = session_manager.get("u1", "s1")
        assert loaded["updated_at"] >= old_ts

    def test_delete_session(self, session_manager):
        session_manager.create_session("u1", "s1")
        session_manager.delete("u1", "s1")
        assert session_manager.get("u1", "s1") is None
