# SDK Examples

This directory contains example scripts showing how to use the PDF Autofiller SDK.

## Files

- **`test_connection.py`** - Quick test to verify SDK can connect to API server
- **`example_with_config.py`** - Complete example using config.json
- **`sample_input.json`** - Sample form data for testing
- **`sample_form.pdf`** - Place your test PDF here

## Quick Start

### 1. Setup Configuration

**Option A: Environment Variables**
```bash
# Copy and edit .env file
cp ../.env.example .env

# Edit .env with your settings
export PDF_AUTOFILLER_API_URL=http://localhost:8000
export PDF_AUTOFILLER_USER_ID=1
export PDF_AUTOFILLER_PDF_DOC_ID=100
```

**Option B: Config File**
```bash
# Copy and edit config.json
cp ../config.json.example ../config.json

# Edit config.json with your settings
```

### 2. Test Connection

```bash
# Make sure API server is running first!
python test_connection.py
```

Expected output:
```
🔗 Using API URL: http://localhost:8000
🔍 Checking server health...
✅ Server is healthy!
   Status: healthy
   Version: 1.0.0
```

### 3. Run Complete Example

```bash
# Place a test PDF in this directory as sample_form.pdf
python example_with_config.py
```

## Using the SDK

### Python Script Example

```python
from pdf_autofiller.client import PDFMapperClient

# Initialize client
client = PDFMapperClient(api_url="http://localhost:8000")

# Extract fields from PDF
result = client.extract(
    pdf_path="/path/to/form.pdf",
    user_id=1,
    pdf_doc_id=100
)
print(f"Extracted fields: {result}")

# Map fields to schema
mapped = client.map_fields(user_id=1, pdf_doc_id=100)
print(f"Mapped {mapped['mapped_count']} fields")

# Embed metadata in PDF
embedded = client.embed(
    pdf_path="/path/to/form.pdf",
    user_id=1,
    pdf_doc_id=100
)
print(f"Embedded PDF: {embedded['embedded_pdf_path']}")
```

### CLI Example

```bash
# Extract fields
pdf-autofiller --api-url http://localhost:8000 extract input.pdf

# Map fields
pdf-autofiller --api-url http://localhost:8000 map --user-id 1 --pdf-doc-id 100

# Complete pipeline (extract + map + embed)
pdf-autofiller --api-url http://localhost:8000 make-embed input.pdf
```

## Testing with Sample Data

1. Place a test PDF as `sample_form.pdf` in this directory
2. Review/edit `sample_input.json` with appropriate field values
3. Run the examples to test extraction, mapping, and filling

## Troubleshooting

**Connection refused:**
```
❌ Health check failed: Connection refused
```
→ Make sure the API server is running: `cd modules/mapper && python api_server.py`

**File not found:**
```
⚠️  Sample PDF not found: sample_form.pdf
```
→ Place a test PDF file in the examples directory

**Import errors:**
```
ModuleNotFoundError: No module named 'pdf_autofiller'
```
→ Install the SDK: `cd sdks/python && pip install -e .`

## Next Steps

1. Review the example scripts
2. Test with your own PDF forms
3. Integrate into your application
4. Read the [SDK documentation](../QUICKSTART.md) for more details
