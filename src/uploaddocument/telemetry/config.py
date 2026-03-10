"""TelemetryConfig — configuration dataclass for telemetry."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TelemetryConfig:
    """
    Configure telemetry for the Upload Document SDK.

    Modes:
        local        → events printed to console only, nothing sent over network
        self_hosted  → events POSTed to YOUR own endpoint (you run the server)

    Example::

        TelemetryConfig(
            enabled=True,
            mode="self_hosted",
            endpoint="https://telemetry.yourcompany.com/events",
            sdk_api_key="your_internal_key",
        )
    """
    enabled: bool = False
    mode: str = "local"              # local | self_hosted
    endpoint: str = ""               # required when mode=self_hosted
    sdk_api_key: str = ""            # sent as X-SDK-Key header
    include_field_keys: bool = True  # include field names (not values) in events
    include_latency: bool = True     # include LLM + fill latency
    batch_size: int = 10             # flush after this many events
    flush_interval_seconds: int = 30 # background flush interval