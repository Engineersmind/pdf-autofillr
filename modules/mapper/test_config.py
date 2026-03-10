#!/usr/bin/env python3
"""
Simple test to verify config and path building works.
"""

import os
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent))

from src.configs.file_config import get_file_config

def test_config_loading():
    """Test that config.ini loads correctly."""
    print("="*60)
    print("Testing Config Loading")
    print("="*60)
    
    try:
        config = get_file_config()
        print("✅ Config loaded successfully")
        
        # Test getting source type
        source_type = config.get_source_type()
        print(f"✅ Source type: {source_type}")
        
        # Test getting paths from config
        input_base = config.get('local', 'input_base_path')
        output_base = config.get('local', 'output_base_path')
        processing_dir = config.get('local', 'processing_dir')
        
        print(f"✅ Input base: {input_base}")
        print(f"✅ Output base: {output_base}")
        print(f"✅ Processing dir: {processing_dir}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_path_building():
    """Test that path building works."""
    print("\n" + "="*60)
    print("Testing Path Building")
    print("="*60)
    
    try:
        config = get_file_config()
        
        # Test parameters
        user_id = 553
        session_id = "086d6670-81e5-47f4-aecb-e4f7c3ba2a83"
        pdf_doc_id = 990
        
        # Build source input path
        source_pdf = config.get_source_input_path('pdf', user_id, session_id, pdf_doc_id)
        print(f"✅ Source PDF path: {source_pdf}")
        
        source_json = config.get_source_input_path('json', user_id, session_id, pdf_doc_id)
        print(f"✅ Source JSON path: {source_json}")
        
        # Build processing paths
        processing_paths = config.get_all_processing_paths(user_id, session_id, pdf_doc_id)
        print(f"✅ Processing paths built: {len(processing_paths)} paths")
        for key, path in list(processing_paths.items())[:5]:
            print(f"   - {key}: {path}")
        
        # Build output path
        output_pdf = config.get_source_output_path('filled_pdf', user_id, session_id, pdf_doc_id)
        print(f"✅ Output PDF path: {output_pdf}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_directory_creation():
    """Test that directories can be created."""
    print("\n" + "="*60)
    print("Testing Directory Creation")
    print("="*60)
    
    try:
        # Create test directories
        dirs = [
            "data/input",
            "data/output",
            "/tmp/processing"
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            if os.path.exists(dir_path):
                print(f"✅ Created/verified: {dir_path}")
            else:
                print(f"❌ Failed to create: {dir_path}")
                return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    print("\n🧪 Running Config Tests\n")
    
    success = True
    success = test_config_loading() and success
    success = test_path_building() and success
    success = test_directory_creation() and success
    
    print("\n" + "="*60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("="*60)
    
    sys.exit(0 if success else 1)
