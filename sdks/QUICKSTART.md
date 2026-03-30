# PDF Autofiller SDK - Quick Start Guide

Complete guide to using the PDF Autofiller Python SDK and CLI.

## 📋 Table of Contents

- [Installation](#installation)
- [Python SDK](#python-sdk)
- [CLI Tool](#cli-tool)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from Source

```bash
cd sdks/python
pip install -e .
```

This installs:
- ✅ `pdf_autofiller` Python package
- ✅ `pdf-autofiller` CLI command

### Verify Installation

```bash
# Check CLI is installed
pdf-autofiller --help

# Check Python package
python -c "from pdf_autofiller import PDFMapperClient; print('✅ SDK installed')"
```

---

## 🐍 Python SDK

### Basic Usage

```python
from pdf_autofiller import PDFMapperClient

# Initialize client
client = PDFMapperClient(
    api_key="your-api-key",
    base_url="http://localhost:8000"
)

# Extract fields
result = client.mapper.extract("input.pdf")
print(f"Found {len(result['data']['fields'])} fields")

# Create embedded PDF
result = client.mapper.make_embed_file(
    pdf_path="input.pdf",
    use_second_mapper=True  # Enable RAG predictions
)
print(f"Embedded PDF: {result['outputs']['embedded_pdf']}")

# Fill PDF
result = client.mapper.fill(
    embedded_pdf="embedded.pdf",
    data={
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com"
    }
)
print(f"Filled PDF: {result['outputs']['filled_pdf']}")
```

### Context Manager Pattern

```python
with PDFMapperClient(api_key="key") as client:
    result = client.mapper.extract("input.pdf")
    # Client automatically closed
```

### Error Handling

```python
from requests.exceptions import HTTPError

try:
    result = client.mapper.extract("input.pdf")
except HTTPError as e:
    print(f"API Error: {e.response.status_code}")
    print(e.response.json())
except Exception as e:
    print(f"Error: {e}")
```

### Async Support (Future)

```python
# Coming soon: Async client
from pdf_autofiller import AsyncPDFMapperClient

async with AsyncPDFMapperClient(api_key="key") as client:
    result = await client.mapper.extract("input.pdf")
```

---

## 💻 CLI Tool

### Basic Commands

#### Extract Fields

```bash
pdf-autofiller extract input.pdf --output extracted.json
```

**Output:**
```
✅ EXTRACT - SUCCESS
⏱️  Execution time: 2.45s
🔑 PDF Hash: aeff9d3d...

📤 Outputs:
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File Type      ┃ Path                           ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Extracted Json │ s3://bucket/extracted.json     │
└────────────────┴────────────────────────────────┘
```

#### Create Embedded PDF

```bash
# Basic embedding
pdf-autofiller make-embed input.pdf

# With RAG predictions (dual mapper)
pdf-autofiller make-embed input.pdf --use-rag
```

**Output:**
```
✅ MAKE-EMBED-FILE - SUCCESS
⏱️  Execution time: 12.45s
🔄 CACHE MISS
🔑 PDF Hash: aeff9d3d...

📊 Mapper: Semantic + RAG

📤 Outputs:
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File Type      ┃ Path                           ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Extracted Json │ s3://bucket/extracted.json     │
│ Mapping Json   │ s3://bucket/mapping.json       │
│ Embedded Pdf   │ s3://bucket/embedded.pdf       │
└────────────────┴────────────────────────────────┘
```

#### Fill PDF

```bash
pdf-autofiller fill embedded.pdf data.json --output filled.pdf
```

**data.json:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+1-555-0123"
}
```

#### Complete Pipeline

```bash
pdf-autofiller run-all input.pdf data.json --output filled.pdf
```

### Advanced Usage

#### Custom API Endpoint

```bash
pdf-autofiller --api-url https://api.example.com extract input.pdf
```

#### With Authentication

```bash
pdf-autofiller --api-key your-key extract input.pdf
```

#### Session Tracking

```bash
pdf-autofiller --session-id session-123 extract input.pdf
```

#### Map with Specific Mapper

```bash
pdf-autofiller map input.pdf data.json --mapper-type ensemble
```

**Mapper Types:**
- `semantic` - LLM-based semantic mapping
- `rag` - RAG-based predictions
- `headers` - Header structure analysis
- `ensemble` - Combines all mappers (recommended)

### Batch Processing

Process multiple PDFs:

```bash
#!/bin/bash
for pdf in pdfs/*.pdf; do
    echo "Processing $pdf..."
    pdf-autofiller make-embed "$pdf" --use-rag
done
```

---

## 📚 Examples

### Example 1: Basic Workflow

```bash
# 1. Extract fields
pdf-autofiller extract form.pdf --output extracted.json

# 2. Review extracted fields
cat extracted.json | jq '.data.fields | length'

# 3. Create embedded PDF
pdf-autofiller make-embed form.pdf

# 4. Fill with data
pdf-autofiller fill embedded.pdf data.json --output filled.pdf
```

### Example 2: With Cache

```bash
# First run (cache miss)
pdf-autofiller make-embed form.pdf --use-rag
# Output: 🔄 CACHE MISS, takes 12s

# Second run (cache hit)
pdf-autofiller make-embed form.pdf --use-rag
# Output: 🎯 CACHE HIT, takes 2s
```

### Example 3: Python Batch Processing

```python
from pdf_autofiller import PDFMapperClient
from pathlib import Path

client = PDFMapperClient(api_key="key")

pdfs = Path("pdfs").glob("*.pdf")

for pdf in pdfs:
    print(f"Processing {pdf.name}...")
    
    try:
        # Create embedded PDF
        result = client.mapper.make_embed_file(
            pdf_path=str(pdf),
            use_second_mapper=True
        )
        
        cache_status = "HIT" if result["cache_hit"] else "MISS"
        print(f"  ✅ {pdf.name} - Cache {cache_status}")
        
    except Exception as e:
        print(f"  ❌ {pdf.name} - Error: {e}")
```

### Example 4: Custom Configuration

```python
from pdf_autofiller import PDFMapperClient
import os

# Read from environment
client = PDFMapperClient(
    api_key=os.getenv("PDF_API_KEY"),
    base_url=os.getenv("PDF_API_URL", "http://localhost:8000"),
    timeout=600.0  # 10 minutes for large PDFs
)

result = client.mapper.make_embed_file("large_form.pdf")
```

---

## 🔧 Troubleshooting

### Issue: Command not found

```bash
pdf-autofiller: command not found
```

**Solution:**
```bash
# Reinstall with pip
cd sdks/python
pip install -e .

# Or add to PATH
export PATH="$PATH:$HOME/.local/bin"
```

### Issue: Import error

```python
ImportError: No module named 'pdf_autofiller'
```

**Solution:**
```bash
# Install package
pip install -e sdks/python

# Verify installation
pip list | grep pdf-autofiller
```

### Issue: API connection error

```
API Error: Connection refused
```

**Solution:**
```bash
# Check API is running
curl http://localhost:8000/health

# Use correct URL
pdf-autofiller --api-url http://localhost:8000 extract input.pdf
```

### Issue: RAG API not configured

```
⚠️  RAG API not configured (rag_api_url is empty)
📋 Using semantic mapper only (RAG integration disabled)
```

**Solution:**
This is expected if RAG module is not deployed yet. The system falls back to semantic mapper only.

To enable RAG:
1. Deploy RAG module
2. Configure `rag_api_url` in config.ini
3. Run with `--use-rag` flag

### Issue: Cache not working

```
🔄 CACHE MISS (expected cache hit)
```

**Solution:**
```bash
# Check cache registry exists
ls -la data/modules/mapper_sample/cache/hash_registry.json

# Verify pdf_cache_enabled in config.ini
grep pdf_cache_enabled config.ini
```

### Issue: Timeout errors

```
Request timed out after 300s
```

**Solution:**
```python
# Increase timeout for large PDFs
client = PDFMapperClient(
    api_key="key",
    timeout=600.0  # 10 minutes
)
```

---

## 📖 More Information

- **Full API Documentation**: See `sdks/python/README.md`
- **Code Examples**: See `sdks/python/examples/`
- **OpenAPI Spec**: See `sdks/openapi-mapper.yaml`
- **Module Documentation**: See `modules/mapper/README.md`

---

## 🤝 Support

- **GitHub Issues**: https://github.com/Engineersmind/pdf-autofillr/issues
- **Email**: team@engineersmind.com
- **Documentation**: See `docs/` directory

---

## ✅ What's Next?

1. **Try the examples** in `sdks/python/examples/`
2. **Read the API docs** in `sdks/python/README.md`
3. **Explore mapper module** in `modules/mapper/`
4. **Check integration tests** in `modules/mapper/tests/`

Happy PDF processing! 🚀
