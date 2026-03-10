"""
address_normalizer — splits full address strings into line1 / line2.
Ported from normalize_address() in the original Lambda extractor_logic.py.
"""
from __future__ import annotations
from typing import Tuple

ADDRESS_GROUPS = ["address_registered", "address_mailing", "address_jurisdiction"]


def normalize_address(full: str) -> Tuple[str, str]:
    """Split a full address string into (line1, line2) on commas."""
    if not full or not isinstance(full, str):
        return "", ""
    parts = [p.strip() for p in full.split(",") if p.strip()]
    if len(parts) == 1:
        return parts[0], ""
    return ", ".join(parts[:2]), ", ".join(parts[2:])


def apply_address_normalization(cleaned: dict) -> dict:
    """Apply address splitting to all address groups in extracted dict."""
    for key in ADDRESS_GROUPS:
        if key in cleaned and isinstance(cleaned[key], dict):
            full = cleaned[key].get(f"{key}_line1_id", "")
            l1, l2 = normalize_address(full)
            cleaned[key][f"{key}_line1_id"] = l1
            cleaned[key][f"{key}_line2_id"] = l2
    if "wiring_details" in cleaned and isinstance(cleaned["wiring_details"], dict):
        addr = cleaned["wiring_details"].get("address", {})
        if isinstance(addr, dict):
            full = addr.get("wiring_details_address_line1_id", "")
            l1, l2 = normalize_address(full)
            addr["wiring_details_address_line1_id"] = l1
            addr["wiring_details_address_line2_id"] = l2
    return cleaned
