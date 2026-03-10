"""
schema_enforcer — enforces LLM output matches expected schema types.
Ported from enforce_schema() in the original Lambda extractor_logic.py.
"""
from __future__ import annotations


def enforce_schema(llm_data, schema):
    """
    Recursively enforce that llm_data matches schema structure and types.

    - dict schema  -> recurse into keys
    - bool schema  -> coerce to bool
    - str schema   -> coerce to str
    - Missing keys -> "" or False
    """
    if isinstance(schema, dict):
        fixed = {}
        for k, sub in schema.items():
            fixed[k] = enforce_schema(llm_data.get(k) if isinstance(llm_data, dict) else None, sub)
        return fixed
    if isinstance(schema, bool):
        if isinstance(llm_data, bool):
            return llm_data
        if isinstance(llm_data, str):
            return llm_data.lower() in ("true", "yes", "1")
        return False
    if isinstance(schema, str):
        return str(llm_data) if llm_data not in (None, "", {}, []) else ""
    return ""
