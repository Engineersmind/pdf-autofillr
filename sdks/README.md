# PDF Autofiller SDKs

Client libraries for PDF Autofiller APIs.

## 📦 Available SDKs

### ✅ Python SDK (Ready for Mapper)
**Status**: Complete for Mapper module  
**Package**: `pdf-autofiller-sdk`  
**Location**: `python/`

```bash
cd python
pip install -e .
```

```python
from pdf_autofiller import PDFMapperClient

client = PDFMapperClient(api_key="your-key")
result = client.mapper.extract(pdf_path="s3://bucket/file.pdf")
```

**Features**:
- ✅ Complete mapper operations (extract, map, embed, fill)
- ✅ Type hints
- ✅ Context manager support
- ✅ Examples included

---

### 🔶 TypeScript/JavaScript SDK (Skeleton)
**Status**: Skeleton structure  
**Package**: `@engineersmind/pdf-autofiller-sdk`  
**Location**: `typescript/`

**TODO**: Generate from OpenAPI spec when ready

---

### 🔶 Go SDK (Skeleton)
**Status**: Placeholder  
**Location**: `go/`

**TODO**: Generate from OpenAPI spec

---

### 🔶 Java SDK (Skeleton)
**Status**: Placeholder  
**Location**: `java/`

**TODO**: Generate from OpenAPI spec

---

## 🔧 SDK Generation

### Prerequisites

1. **OpenAPI Specifications** (Available)
   - ✅ `openapi-mapper.yaml` - Complete for Mapper module
   - 🔶 `openapi-rag.yaml` - Skeleton (TODO when RAG module is ready)
   - 🔶 `openapi-orchestrator.yaml` - Skeleton (TODO)
   - 🔶 `openapi-chatbot.yaml` - Skeleton (TODO)

2. **SDK Generator Tools**
   - [Stainless](https://www.stainlessapi.com/) - Modern, recommended
   - [OpenAPI Generator](https://openapi-generator.tech/) - Mature, many languages
   - [Speakeasy](https://www.speakeasyapi.dev/) - Developer-friendly

### Quick Generation Commands

#### TypeScript
```bash
openapi-generator generate \
  -i openapi-mapper.yaml \
  -g typescript-axios \
  -o typescript/
```

#### Go
```bash
openapi-generator generate \
  -i openapi-mapper.yaml \
  -g go \
  -o go/
```

#### Java
```bash
openapi-generator generate \
  -i openapi-mapper.yaml \
  -g java \
  -o java/
```

---

## 🚀 Quick Start (Python SDK)

### Install
```bash
cd sdks/python
pip install -e .
```

### Use
```python
from pdf_autofiller import PDFMapperClient

client = PDFMapperClient(
    api_key="your-api-key",
    base_url="http://localhost:8000"
)

# Extract fields
result = client.mapper.extract(pdf_path="s3://bucket/form.pdf")

# Map fields
result = client.mapper.map(
    pdf_path="s3://bucket/form.pdf",
    mapper_type="ensemble"
)

# Fill PDF
result = client.mapper.fill(
    pdf_path="s3://bucket/form.pdf",
    data={"first_name": "John", "last_name": "Doe"}
)
```

See `python/examples/` for more examples.

---

## 📄 License

MIT License
