#!/usr/bin/env python3
"""
Example: Using the PDF Autofiller SDK with config file
"""
import os
import sys
import json
from pathlib import Path

# Add parent directory to path to import the SDK
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_autofiller.client import PDFMapperClient

def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        print("⚠️  config.json not found. Copy config.json.example to config.json")
        print("   and update with your settings.")
        return None
    
    with open(config_path) as f:
        return json.load(f)

def main():
    # Load config
    config = load_config()
    if not config:
        return
    
    # Initialize client with config
    client = PDFMapperClient(
        api_url=config.get("api_url"),
        api_key=config.get("api_key"),
        timeout=config.get("timeout", 300)
    )
    
    # Check server health
    print("🔍 Checking server health...")
    health = client.health_check()
    print(f"✅ Server is healthy: {health}")
    
    # Get default values from config
    user_id = config.get("default_user_id", 1)
    pdf_doc_id = config.get("default_pdf_doc_id", 100)
    
    # Example: Extract fields from a PDF
    pdf_path = Path(__file__).parent / "sample_form.pdf"
    
    if not pdf_path.exists():
        print(f"⚠️  Sample PDF not found: {pdf_path}")
        print("   Please place a PDF file at examples/sample_form.pdf")
        return
    
    print(f"\n📄 Extracting fields from {pdf_path.name}...")
    result = client.extract(
        pdf_path=str(pdf_path),
        user_id=user_id,
        pdf_doc_id=pdf_doc_id
    )
    
    print(f"✅ Extraction complete!")
    print(f"   Fields found: {result.get('message', 'Unknown')}")
    
    # Example: Map fields
    print(f"\n🗺️  Mapping fields...")
    map_result = client.map_fields(
        user_id=user_id,
        pdf_doc_id=pdf_doc_id
    )
    
    print(f"✅ Mapping complete!")
    print(f"   Mapped: {map_result.get('mapped_count', 0)} fields")
    
    # Example: Embed metadata
    print(f"\n📝 Embedding metadata...")
    embed_result = client.embed(
        pdf_path=str(pdf_path),
        user_id=user_id,
        pdf_doc_id=pdf_doc_id
    )
    
    print(f"✅ Embedding complete!")
    print(f"   Output: {embed_result.get('embedded_pdf_path', 'Unknown')}")

if __name__ == "__main__":
    main()
