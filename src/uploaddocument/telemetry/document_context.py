"""DocumentContext — document taxonomy metadata attached to every telemetry event."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class DocumentContext:
    """
    Attach document category metadata to every telemetry event.

    Example::

        DocumentContext(
            category="Private Markets",
            sub_category="Private Equity",
            document_type="LP Subscription Agreement",
            extra={"fund_name": "Acme Capital Fund III"},
        )
    """
    category: str = ""
    sub_category: str = ""
    document_type: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "sub_category": self.sub_category,
            "document_type": self.document_type,
            **{f"extra_{k}": v for k, v in self.extra.items()},
        }