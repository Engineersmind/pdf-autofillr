# upload-document-sdk

> Document extraction and PDF filling pipeline — open source Python SDK

[![PyPI version](https://badge.fury.io/py/upload-document-sdk.svg)](https://badge.fury.io/py/upload-document-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Upload Document SDK extracts structured investor data from any document format (PDF, DOCX, PPTX, XLSX, JSON, TXT) using GPT, then optionally fills a target PDF with that data via a pluggable PDF filling interface.

## Features

- Reads PDF, DOCX, PPTX, XLSX, JSON, TXT via pluggable readers
- GPT-4.1-mini extracts structured data matching your form_keys.json schema
- Parallel pipeline: extraction and embed preparation run simultaneously
- Schema enforcement and address normalization built-in
- Local filesystem or S3 storage backends
- Pluggable PDF filling via `PDFFillerInterface`
- Full execution logging saved to S3

## Installation

```bash
# Core only
pip install upload-document-sdk

# With S3 support
pip install upload-document-sdk[s3]

# With local dev server
pip install upload-document-sdk[server]

# Everything
pip install upload-document-sdk[all]
```

## Quick Start

```python
import os
from uploaddocument import UploadDocumentClient, LocalStorage, SchemaConfig

client = UploadDocumentClient(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    storage=LocalStorage(data_path="./data", config_path="./configs"),
    schema_config=SchemaConfig.from_directory("./configs"),
    pdf_filler=None,  # data-only mode
)

result = client.process_document(
    document_path="./investor_pack.pdf",
    user_id="investor_123",
    session_id="session_abc",
)

print(result.extracted_flat)  # flat dict of all extracted fields
```

## License

MIT
