"""
Basic example of using the PDF Autofiller SDK.
"""

from pdf_autofiller import PDFMapperClient


def main():
    # Initialize client
    client = PDFMapperClient(
        api_key="your-api-key-here",
        base_url="http://localhost:8000"  # Change to your API URL
    )
    
    pdf_path = "s3://my-bucket/test-form.pdf"
    
    print("1. Checking API health...")
    health = client.health_check()
    print(f"   Status: {health}")
    
    print("\n2. Extracting fields from PDF...")
    extract_result = client.mapper.extract(pdf_path=pdf_path)
    print(f"   Success: {extract_result['success']}")
    if extract_result['success']:
        fields = extract_result.get('data', {}).get('fields', [])
        print(f"   Found {len(fields)} fields")
    
    print("\n3. Mapping fields...")
    map_result = client.mapper.map(
        pdf_path=pdf_path,
        mapper_type="ensemble"
    )
    print(f"   Success: {map_result['success']}")
    
    print("\n4. Creating embed file (Extract + Map + Embed)...")
    embed_result = client.mapper.make_embed_file(pdf_path=pdf_path)
    print(f"   Success: {embed_result['success']}")
    
    print("\n5. Checking if PDF has embedded metadata...")
    check_result = client.mapper.check_embed_file(pdf_path=pdf_path)
    print(f"   Has metadata: {check_result.get('data', {}).get('has_metadata', False)}")
    
    print("\n6. Filling PDF with data...")
    fill_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+1-555-0100"
    }
    fill_result = client.mapper.fill(
        pdf_path=pdf_path,
        data=fill_data
    )
    print(f"   Success: {fill_result['success']}")
    
    # Close client
    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
