"""
Example using context manager for automatic cleanup.
"""

from pdf_autofiller import PDFMapperClient


def main():
    # Use context manager - client is automatically closed
    with PDFMapperClient(
        api_key="your-api-key",
        base_url="http://localhost:8000"
    ) as client:
        
        pdf_path = "s3://my-bucket/form.pdf"
        
        # Complete pipeline in one call
        result = client.mapper.make_embed_file(pdf_path=pdf_path)
        
        if result['success']:
            print("✓ Successfully created embed file")
            print(f"  Data: {result.get('data', {})}")
        else:
            print("✗ Failed to create embed file")
            print(f"  Error: {result.get('error')}")


if __name__ == "__main__":
    main()
