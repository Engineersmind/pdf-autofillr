# tests/unit/test_telemetry.py
from chatbot.telemetry.collector import TelemetryCollector, _hash_id
from chatbot.telemetry.config import TelemetryConfig
from chatbot.telemetry.document_context import DocumentContext


class TestAnonymizer:
    def test_hash_is_deterministic(self):
        assert _hash_id("user_123") == _hash_id("user_123")

    def test_hash_is_not_reversible(self):
        h = _hash_id("user_123")
        assert "user_123" not in h

    def test_different_ids_different_hashes(self):
        assert _hash_id("user_123") != _hash_id("user_456")


class TestTelemetryCollector:
    def test_disabled_by_default(self):
        collector = TelemetryCollector()
        # Should not raise even though disabled
        collector.track_state_transition("init", "data_collection", 1, 0.5)

    def test_enabled_emits(self, capsys):
        import os; os.environ["chatbot_DEBUG_LOGGING"] = "true"
        collector = TelemetryCollector(
            config=TelemetryConfig(enabled=True, mode="self_hosted"),
            document_context=DocumentContext(category="Private Markets"),
        )
        collector.track_extraction(
            user_id="u1", session_id="s1",
            fields_extracted=5, fields_attempted=7,
            latency=1.2, method="llm",
        )
        captured = capsys.readouterr()
        assert "extraction_result" in captured.out


class TestDocumentContext:
    def test_to_dict(self):
        ctx = DocumentContext(
            category="Hedge Funds",
            sub_category="Credit",
            document_type="ISDA Master Agreement",
            extra={"fund_name": "Test Fund"},
        )
        d = ctx.to_dict()
        assert d["category"] == "Hedge Funds"
        assert d["extra_fund_name"] == "Test Fund"
