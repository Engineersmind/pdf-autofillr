# PDF Autofiller Core

**Core shared interfaces and utilities for all PDF Autofiller modules.**

## 🎯 Purpose

This package provides platform-agnostic abstractions that enable:
- **Multi-cloud storage** - Unified interface for S3, Azure Blob, GCS, and local storage
- **Consistent handlers** - Standard request/response patterns across all modules
- **Common utilities** - Shared functions to avoid code duplication
- **Zero dependencies** - Only abstract interfaces, no cloud SDKs!

## 📦 Installation

```bash
# Install core package
pip install pdf-autofiller-core

# From source
cd packages/core
pip install -e .

# With dev dependencies
pip install -e .[dev]
```

## 🚀 Usage

### Storage Interface

```python
from pdf_autofiller_core.interfaces import (
    StorageInterface,
    StorageConfig,
    StorageProvider,
    create_storage
)

# Create storage configuration
config = StorageConfig(
    provider=StorageProvider.AWS_S3,
    bucket_name="my-bucket",
    region="us-east-1",
    prefix="pdfs/"
)

# Get storage instance (actual implementation depends on provider)
# Note: Implementations are in respective modules (mapper, orchestrator, etc.)
storage = create_storage(config)

# Upload file
url = storage.upload_file("local/path.pdf", "key/in/storage.pdf")

# Download file
storage.download_file("key/in/storage.pdf", "local/output.pdf")

# Check existence
exists = storage.file_exists("key/in/storage.pdf")

# Get presigned URL
download_url = storage.get_download_url("key/in/storage.pdf", expiration=3600)
```

### Handler Interface

```python
from pdf_autofiller_core.interfaces import (
    HandlerInterface,
    HandlerRequest,
    HandlerResponse,
    BaseHandler,
    OperationStatus
)

# Create a custom handler
class MyHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.supported_operations = ["extract", "map"]
    
    def process(self, request: HandlerRequest) -> HandlerResponse:
        # Your business logic here
        result = {"extracted_fields": [...]}
        
        return HandlerResponse.success_response(
            data=result,
            operation=request.operation,
            session_id=request.session_id
        )

# Use the handler
handler = MyHandler()

request = HandlerRequest(
    operation="extract",
    pdf_path="document.pdf",
    session_id="abc-123"
)

response = handler.handle(request)

if response.success:
    print(f"Success! Data: {response.data}")
else:
    print(f"Error: {response.error}")
```

### Common Utilities

```python
from pdf_autofiller_core.utils import (
    generate_session_id,
    generate_file_hash,
    safe_json_dumps,
    sanitize_filename,
    format_bytes,
    Timer
)

# Generate session ID
session_id = generate_session_id()  # "550e8400-e29b-41d4-a716-446655440000"

# Hash a file
file_hash = generate_file_hash("document.pdf")

# Safe JSON serialization (handles datetime, etc.)
json_str = safe_json_dumps({"timestamp": datetime.now()})

# Sanitize filenames
safe_name = sanitize_filename("my/unsafe:file<name>.pdf")  # "my_unsafe_file_name_.pdf"

# Format bytes
size = format_bytes(1536000)  # "1.5 MB"

# Time operations
with Timer("PDF Processing") as timer:
    # Your code here
    process_pdf()
# Automatically logs: "PDF Processing took 1.23s"
```

## 📁 Package Structure

```
pdf_autofiller_core/
├── __init__.py              # Main exports
├── interfaces/              # Abstract interfaces
│   ├── __init__.py
│   ├── storage_interface.py # Storage abstraction
│   └── handler_interface.py # Handler pattern
└── utils/                   # Common utilities
    ├── __init__.py
    └── common_utils.py      # Utility functions
```

## 🎯 Design Principles

### 1. **Zero Dependencies**
- Only Python standard library
- No cloud SDKs (boto3, azure-storage-blob, etc.)
- Modules import this, not vice versa

### 2. **Interface-First**
- All interfaces are abstract (ABC)
- Implementations live in specific modules
- Enables testing with mocks

### 3. **Platform Agnostic**
- No assumptions about cloud provider
- Works with AWS, Azure, GCP, or local
- Clean separation of concerns

### 4. **Consistency**
- All modules use same patterns
- Standard request/response formats
- Predictable error handling

## 🔌 How Modules Use This Package

### Mapper Module
```python
from pdf_autofiller_core.interfaces import BaseHandler, HandlerRequest, HandlerResponse

class MapperHandler(BaseHandler):
    def process(self, request: HandlerRequest) -> HandlerResponse:
        # Mapping logic
        pass
```

### RAG Module
```python
from pdf_autofiller_core.interfaces import StorageInterface
from pdf_autofiller_core.utils import generate_session_id

class RAGService:
    def __init__(self, storage: StorageInterface):
        self.storage = storage
```

### Orchestrator Module
```python
from pdf_autofiller_core.utils import Timer, format_bytes

with Timer("Upload Processing"):
    file_size = format_bytes(pdf_size)
    # Process upload
```

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest tests/

# Type checking
mypy pdf_autofiller_core/

# Code formatting
black pdf_autofiller_core/
```

## 📝 Contributing

This is the foundation package - changes here affect ALL modules!

When adding new interfaces:
1. Keep them abstract (ABC)
2. No external dependencies
3. Document thoroughly
4. Add examples to README

## 🔗 Related Packages

- **pdf-mapper** - PDF extraction, mapping, embedding, filling
- **pdf-rag** - RAG service for predictions and feedback
- **pdf-orchestrator** - Upload handler and workflow orchestration
- **pdf-chatbot** - Conversational interface

## 📄 License

MIT License - See LICENSE file

## 🤝 Support

- GitHub Issues: https://github.com/Engineersmind/pdf-autofillr/issues
- Documentation: https://github.com/Engineersmind/pdf-autofillr/tree/main/docs
