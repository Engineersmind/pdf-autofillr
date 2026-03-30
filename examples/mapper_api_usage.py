"""
Example: Using Mapper Module via API Server
This shows how to call mapper functions through HTTP endpoints
"""

import requests
import json
from pathlib import Path


class MapperAPIClient:
    """Client for Mapper API Server"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def health_check(self):
        """Check if API server is running"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def map_pdf(self, pdf_path, user_data=None, user_id="test_user", pdf_doc_id=None):
        """
        Map and fill a PDF
        
        Args:
            pdf_path: Path to PDF file
            user_data: Dictionary of user data (optional)
            user_id: User identifier
            pdf_doc_id: PDF document identifier
        
        Returns:
            Result dictionary with paths to output files
        """
        files = {
            'pdf': open(pdf_path, 'rb')
        }
        
        data = {
            'user_id': user_id,
            'pdf_doc_id': pdf_doc_id or Path(pdf_path).stem,
        }
        
        if user_data:
            data['user_data'] = json.dumps(user_data)
        
        response = requests.post(
            f"{self.base_url}/map",
            files=files,
            data=data
        )
        
        return response.json()
    
    def extract_fields(self, pdf_path):
        """Extract fields from PDF without filling"""
        files = {'pdf': open(pdf_path, 'rb')}
        response = requests.post(f"{self.base_url}/extract", files=files)
        return response.json()


def example_api_usage():
    """Example: Using API server"""
    
    # Initialize client
    client = MapperAPIClient("http://localhost:8000")
    
    # 1. Health check
    print("🏥 Checking API health...")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Source: {health.get('source_type', 'unknown')}")
    
    # 2. Extract fields only
    print("\n📄 Extracting fields from PDF...")
    pdf_path = "data/modules/mapper_sample/input/small_4page.pdf"
    fields = client.extract_fields(pdf_path)
    print(f"   Found {len(fields.get('fields', []))} fields")
    print(f"   Sample fields: {list(fields.get('fields', {}).keys())[:5]}")
    
    # 3. Map and fill PDF
    print("\n✍️  Mapping and filling PDF...")
    user_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "date": "2026-03-10",
        "amount": "1000.00"
    }
    
    result = client.map_pdf(
        pdf_path=pdf_path,
        user_data=user_data,
        user_id="test_user",
        pdf_doc_id="sample_001"
    )
    
    print(f"   ✅ Success!")
    print(f"   Filled PDF: {result.get('filled_pdf_path')}")
    print(f"   Mapping data: {result.get('mapping_path')}")
    print(f"   Fields mapped: {result.get('fields_mapped', 0)}")
    
    return result


def example_api_with_curl():
    """Example: Using curl commands"""
    
    print("\n🔧 Equivalent curl commands:\n")
    
    # Health check
    print("# Health check:")
    print("curl http://localhost:8000/health\n")
    
    # Extract fields
    print("# Extract fields:")
    print("curl -X POST http://localhost:8000/extract \\")
    print("  -F 'pdf=@data/modules/mapper_sample/input/small_4page.pdf'\n")
    
    # Map and fill
    print("# Map and fill PDF:")
    print("curl -X POST http://localhost:8000/map \\")
    print("  -F 'pdf=@data/modules/mapper_sample/input/small_4page.pdf' \\")
    print("  -F 'user_data={\"name\":\"John Doe\",\"email\":\"john@example.com\"}' \\")
    print("  -F 'user_id=test_user' \\")
    print("  -F 'pdf_doc_id=sample_001'\n")
    
    # View API docs
    print("# View interactive API docs:")
    print("open http://localhost:8000/docs")


if __name__ == "__main__":
    print("🚀 Mapper Module - API Usage Examples\n")
    
    print("⚠️  Make sure API server is running:")
    print("   cd modules/mapper")
    print("   python -m uvicorn api_server:app --reload")
    print("\n" + "=" * 60 + "\n")
    
    try:
        # Test if server is running
        response = requests.get("http://localhost:8000/health", timeout=2)
        
        print("✅ API server is running!\n")
        
        # Run examples
        result = example_api_usage()
        
        print("\n" + "=" * 60)
        example_api_with_curl()
        
    except requests.exceptions.ConnectionError:
        print("❌ API server not running!")
        print("\nTo start the server:")
        print("   cd modules/mapper")
        print("   python -m uvicorn api_server:app --reload --port 8000")
        print("\nThen run this script again.")
