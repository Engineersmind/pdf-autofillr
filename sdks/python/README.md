# PDF Autofiller Python SDK

Python client library for the PDF Mapper API.

## Installation

```bash
pip install pdf-autofiller-sdk

# Or from source
cd sdks/python
pip install -e .
```

## Quick Start

```python
from pdf_autofiller import PDFMapperClient

# Initialize client
client = PDFMapperClient(
    api_key="your-api-key",
    base_url="https://api.example.com/v1"
)

# Extract fields from PDF
result = client.mapper.extract(
    pdf_path="s3://my-bucket/form.pdf"
)
print(result["data"]["fields"])

# Map fields using ensemble mapper
result = client.mapper.map(
    pdf_path="s3://my-bucket/form.pdf",
    mapper_type="ensemble"
)

# Create embed file (extract + map + embed)
result = client.mapper.make_embed_file(
    pdf_path="s3://my-bucket/form.pdf"
)

# Fill PDF with data
result = client.mapper.fill(
    pdf_path="s3://my-bucket/form.pdf",
    data={
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com"
    }
)
```

## Context Manager

```python
with PDFMapperClient(api_key="your-key") as client:
    result = client.mapper.extract("path/to/pdf")
# Client is automatically closed
```

## Available Operations

### Extract
Extract form fields from a PDF:
```python
result = client.mapper.extract(pdf_path="...")
```

### Map
Map fields to target schema:
```python
result = client.mapper.map(
    pdf_path="...",
    mapper_type="ensemble"  # semantic, rag, headers, ensemble
)
```

### Embed
Embed metadata into PDF:
```python
result = client.mapper.embed(pdf_path="...")
```

### Fill
Fill PDF form with data:
```python
result = client.mapper.fill(
    pdf_path="...",
    data={"field": "value"}
)
```

### Make Embed File
Complete pipeline (Extract + Map + Embed):
```python
result = client.mapper.make_embed_file(pdf_path="...")
```

### Check Embed File
Verify if PDF has embedded metadata:
```python
result = client.mapper.check_embed_file(pdf_path="...")
if result["data"]["has_metadata"]:
    print("Has metadata!")
```

### Run All
Complete pipeline (Extract + Map + Embed + Fill):
```python
result = client.mapper.run_all(pdf_path="...")
```

## Error Handling

```python
import httpx

try:
    result = client.mapper.extract(pdf_path="invalid")
except httpx.HTTPError as e:
    print(f"HTTP error: {e}")
```

## Configuration

```python
client = PDFMapperClient(
    api_key="your-api-key",
    base_url="https://api.example.com/v1",
    timeout=300.0  # Request timeout in seconds
)
```

## Examples

See the `examples/` directory for more usage examples.

## License

MIT License
