"""
Test script for HTTP Server API.

Run this after starting the HTTP server to test the endpoints.
"""

import requests
import json
from typing import Dict, Any


# Server URL
BASE_URL = "http://localhost:8000"


def test_health():
    """Test health check endpoint."""
    print("\n" + "=" * 80)
    print("Testing Health Check")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed")


def test_make_embed_file():
    """Test make_embed_file endpoint."""
    print("\n" + "=" * 80)
    print("Testing Make Embed File")
    print("=" * 80)
    
    payload = {
        "user_id": 553,
        "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
        "pdf_doc_id": 990,
        "investor_type": "individual",
        "use_second_mapper": True
    }
    
    print(f"Request Payload:")
    print(json.dumps(payload, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/make-embed-file",
        json=payload,
        timeout=300  # 5 minutes timeout for long operations
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        assert result["status"] == "success"
        assert result["operation"] == "make_embed_file"
        assert "output_paths" in result
        print("✅ Make embed file passed")
    else:
        print(f"❌ Make embed file failed: {response.json().get('detail')}")


def test_extract():
    """Test extract endpoint."""
    print("\n" + "=" * 80)
    print("Testing Extract")
    print("=" * 80)
    
    payload = {
        "user_id": 553,
        "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
        "pdf_doc_id": 990,
        "investor_type": "individual"
    }
    
    response = requests.post(
        f"{BASE_URL}/extract",
        json=payload,
        timeout=60
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Extract completed: {result.get('output_paths', {}).get('extracted_json')}")
    else:
        print(f"❌ Extract failed: {response.json().get('detail')}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PDF AUTOFILLER HTTP API TEST SUITE")
    print("=" * 80)
    print(f"Testing server at: {BASE_URL}")
    print("Make sure the HTTP server is running!")
    print("  python -m entrypoints.http_server")
    print("=" * 80)
    
    try:
        # Test health check
        test_health()
        
        # Test main pipeline
        test_make_embed_file()
        
        # Test individual operations
        # test_extract()  # Uncomment to test
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to server")
        print("Make sure the HTTP server is running:")
        print("  cd modules/mapper")
        print("  python -m entrypoints.http_server")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
