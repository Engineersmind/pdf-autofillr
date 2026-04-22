#!/usr/bin/env python3
"""
Example: Quick test script using environment variables
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import the SDK
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_autofiller.client import PDFMapperClient

def main():
    # Get API URL from environment variable
    api_url = os.getenv("PDF_AUTOFILLER_API_URL", "http://localhost:8000")
    api_key = os.getenv("PDF_AUTOFILLER_API_KEY")
    
    print(f"🔗 Using API URL: {api_url}")
    
    # Initialize client
    client = PDFMapperClient(api_url=api_url, api_key=api_key)
    
    # Health check
    print("\n🔍 Checking server health...")
    try:
        health = client.health_check()
        print(f"✅ Server is healthy!")
        print(f"   Status: {health.get('status')}")
        print(f"   Version: {health.get('version')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        print("   Make sure the API server is running!")
        return
    
    # Get defaults from environment
    user_id = int(os.getenv("PDF_AUTOFILLER_USER_ID", "1"))
    pdf_doc_id = int(os.getenv("PDF_AUTOFILLER_PDF_DOC_ID", "100"))
    
    print(f"\n📊 Default values:")
    print(f"   User ID: {user_id}")
    print(f"   PDF Doc ID: {pdf_doc_id}")
    
    # Check if sample PDF exists
    sample_pdf = Path(__file__).parent / "sample_form.pdf"
    if sample_pdf.exists():
        print(f"\n📄 Found sample PDF: {sample_pdf.name}")
        print("   You can now run operations on this PDF!")
        print("\n   Try:")
        print(f"   python -c 'from pdf_autofiller.client import PDFMapperClient; "
              f"c = PDFMapperClient(\"{api_url}\"); "
              f"print(c.extract(\"{sample_pdf}\", {user_id}, {pdf_doc_id}))'")
    else:
        print(f"\n⚠️  No sample PDF found at {sample_pdf}")
        print("   Place a PDF file there to test extraction")
    
    print("\n✅ SDK is ready to use!")

if __name__ == "__main__":
    main()
