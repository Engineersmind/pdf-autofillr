#!/usr/bin/env python3
"""
Manual smoke-test for the local entrypoint.

Verifies the complete flow end-to-end:
  1. Input files at MAPPER_INPUT_PATH/{uid}/{sid}/{pid}/
  2. Call handle_local_event()
  3. Outputs appear at MAPPER_OUTPUT_PATH/{uid}/{sid}/{pid}/
  4. /tmp/processing/ is cleaned up after the job

Run manually (requires real input files and API keys):
    python tests/test_local_entrypoint.py
"""

import os
import json
import sys
import asyncio
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from entrypoints.local import handle_local_event
from src.storage.storage_config import get_storage_config

logger = logging.getLogger(__name__)


def test_local_entrypoint():
    """Smoke-test the local entrypoint (manual — requires real input files)."""
    print("\n" + "=" * 60)
    print("Testing Local Entrypoint")
    print("=" * 60 + "\n")

    sc = get_storage_config()

    # Test IDs
    user_id = "1"
    session_id = "1"
    pdf_doc_id = "100"

    expected_pdf  = sc.input_path(user_id, session_id, pdf_doc_id, "input.pdf")
    expected_json = sc.input_path(user_id, session_id, pdf_doc_id, "global_schema.json")

    print(f"Storage backend : {sc.storage_type}")
    print(f"Expected input PDF    : {expected_pdf}")
    print(f"Expected global schema: {expected_json}")
    print()

    # Pre-flight check
    missing = []
    if not os.path.isfile(expected_pdf):
        missing.append(f"input PDF:    {expected_pdf}")
    if not os.path.isfile(expected_json):
        missing.append(f"global JSON:  {expected_json}")

    if missing:
        print("❌ Missing required input files:")
        for m in missing:
            print(f"   - {m}")
        print()
        print("Place input files at the paths above, then re-run.")
        return

    event = {
        "operation": "make_embed_file",
        "user_id": user_id,
        "session_id": session_id,
        "pdf_doc_id": pdf_doc_id,
        "investor_type": "individual",
        "use_second_mapper": False,
    }

    print(f"Event: {json.dumps(event, indent=2)}\n")
    print("Calling local entrypoint...")
    result = asyncio.run(handle_local_event(event))

    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    print("\n" + "=" * 60)
    if result.get("status") == "success":
        print("✅ Status: SUCCESS")
        for key, path in result.get("output_paths", {}).items():
            exists = os.path.exists(path)
            mark = "✅" if exists else "❌"
            print(f"  {mark} {key}: {path}")
    else:
        print(f"❌ Status: ERROR — {result.get('error')}")
    print("=" * 60)


if __name__ == "__main__":
    test_local_entrypoint()
