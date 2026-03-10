#!/usr/bin/env python3
"""
Test the local entrypoint design.

This script tests the complete flow:
1. Create test files in /app/data/input/
2. Call local entrypoint
3. Verify results in /app/data/output/
4. Verify cleanup of /tmp/processing/
"""

import os
import json
import sys
import asyncio
from pathlib import Path
import logging

# Add module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from entrypoints.local import handle_local_event
from src.configs.file_config import get_file_config

logger = logging.getLogger(__name__)


def test_local_entrypoint():
    """Test the local entrypoint."""
    print("\n" + "="*60)
    print("Testing Local Entrypoint Design")
    print("="*60 + "\n")
    
    # Load config to get paths
    file_config = get_file_config()
    input_base = file_config.get('local', 'input_base_path', fallback='../../data/input')
    registry_path = file_config.get('local', 'local_global_json', fallback='../../data/pdf_registry.json')
    
    # Make paths absolute from module directory
    module_dir = Path(__file__).parent
    input_base_abs = (module_dir / input_base).resolve()
    registry_path_abs = (module_dir / registry_path).resolve()
    
    print(f"Configuration from config.ini:")
    print(f"  Input base: {input_base} → {input_base_abs}")
    print(f"  Registry: {registry_path} → {registry_path_abs}")
    print()
    
    # Test IDs - user must provide these files
    user_id = 553
    session_id = "086d6670-81e5-47f4-aecb-e4f7c3ba2a83"
    pdf_doc_id = 990
    
    print(f"Test Configuration:")
    print(f"  User ID: {user_id}")
    print(f"  Session ID: {session_id}")
    print(f"  PDF Doc ID: {pdf_doc_id}")
    print()
    
    # Expected file locations (based on config.ini)
    expected_pdf = input_base_abs / f"{user_id}_{session_id}_{pdf_doc_id}.pdf"
    expected_json = input_base_abs / f"{user_id}_{session_id}_{pdf_doc_id}.json"
    expected_registry = registry_path_abs
    
    print(f"Expected input files (from config):")
    print(f"  PDF:  {expected_pdf}")
    print(f"  JSON: {expected_json}")
    print(f"  Registry: {expected_registry}")
    print()
    
    # Check if files exist
    missing = []
    if not expected_pdf.exists():
        missing.append(f"PDF: {expected_pdf}")
    if not expected_json.exists():
        missing.append(f"JSON: {expected_json}")
    if not expected_registry.exists():
        missing.append(f"Registry: {expected_registry}")
    
    if missing:
        print("❌ Missing required files:")
        for m in missing:
            print(f"  - {m}")
        print()
        print("Please create these files before running the test.")
        print()
        print("Example JSON content for input file:")
        print('  {')
        print('    "firstName": "John",')
        print('    "lastName": "Doe",')
        print('    "email": "john@example.com"')
        print('  }')
        print()
        print("Example registry content:")
        print('  {')
        print('    "form_fields": ["firstName", "lastName", "email"]')
        print('  }')
        return
    
    # Create test event
    event = {
        "operation": "make_embed_file",
        "user_id": user_id,
        "session_id": session_id,
        "pdf_doc_id": pdf_doc_id,
        "investor_type": "individual",
        "use_second_mapper": False
    }
    
    print(f"\nTest Event:")
    print(json.dumps(event, indent=2))
    
    # Call entrypoint (async)
    print(f"\nCalling local entrypoint...")
    result = asyncio.run(handle_local_event(event))
    
    # Print result
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
    
    # Verify
    print(f"\n" + "="*60)
    print("Verification")
    print("="*60)
    
    if result['status'] == 'success':
        print("✅ Status: SUCCESS")
        
        # Check output files
        for key, path in result.get('output_paths', {}).items():
            if os.path.exists(path):
                print(f"✅ Output file exists: {path}")
            else:
                print(f"❌ Output file missing: {path}")
        
        # Check cleanup
        processing_dir = Path("/tmp/processing")
        if processing_dir.exists():
            files = list(processing_dir.glob("*"))
            if files:
                print(f"⚠️  Temp files NOT cleaned up: {len(files)} files remain")
                for f in files:
                    print(f"   - {f}")
            else:
                print("✅ Temp files cleaned up")
        else:
            print("✅ Processing directory cleaned up")
            
    else:
        print(f"❌ Status: ERROR")
        print(f"   Error: {result.get('error')}")
    
    print(f"\n" + "="*60)


if __name__ == "__main__":
    test_local_entrypoint()
