# Module Documentation: pdf_upload_lambda

## Overview
The `pdf_upload_lambda` module is a serverless Lambda function that handles PDF document extraction and filling workflows. It serves as the entry point for processing uploaded PDFs through extraction, embedding, and filling operations.

## Purpose
- Accept PDF upload requests via Lambda Function URL
- Extract structured data from PDF documents using LLM
- Create embedded PDF templates via main pipeline API
- Fill PDFs with extracted and profile data
- Provide comprehensive execution logging

## Architecture

### Entry Point
- **File**: `lambda_function.py`
- **Handler**: `lambda_handler(event, context)`
- **Type**: AWS Lambda Function URL handler

### Module Structure
```
pdf_upload_lambda/
├── lambda_function.py      # Entry point, API validation
├── main.py                 # Parallel processing orchestration
├── api_handler.py          # API client for main pipeline
├── extractor_logic.py      # LLM-based document extraction
├── s3_handler.py           # S3 operations
├── logger_utils.py         # Execution logging
└── requirements.txt        # Dependencies
```

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     PDF Upload Lambda                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  API Validation  │
                    │  - X-API-Key     │
                    │  - Required      │
                    │    Fields        │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Load Schema &   │
                    │  Download PDF    │
                    └──────────────────┘
                              │
                              ▼
          ┌───────────────────────────────────────┐
          │      PARALLEL PROCESSING (2 Threads)   │
          └───────────────────────────────────────┘
                    │                 │
         ┌──────────┴────────┐        │
         │                   │        │
         ▼                   ▼        ▼
  ┌────────────┐      ┌─────────────────┐
  │  Thread A  │      │    Thread B     │
  │            │      │                 │
  │ Extract    │      │ make_embed_file │
  │ (OpenAI)   │      │    (API Call)   │
  │     ↓      │      │        ↓        │
  │ Upload to  │      │ check_embed_file│
  │ 2 S3 Locs  │      │   (Polling)     │
  └────────────┘      └─────────────────┘
         │                   │
         └──────────┬────────┘
                    │
                    ▼
           ┌────────────────┐
           │   fill_pdf     │
           │   (API Call)   │
           └────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │  Save Logs     │
           │  to S3         │
           └────────────────┘
```

## API Contract

### Input (Lambda Function URL)
```json
{
  "headers": {
    "X-API-Key": "required_api_key"
  },
  "body": {
    "user_id": "12345",
    "session_id": "session_abc",
    "filled_doc_pdf_id": "doc_456",
    "pdf_doc_id": "789",
    "pdf_location": "s3://bucket/path/to/file.pdf",
    "investor_type": "Individual"
  }
}
```

### Output (Success)
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "status": "success",
    "response": "Your PDF has been extracted and filled",
    "user_id": "12345",
    "session_id": "session_abc",
    "filled_doc_pdf_id": "doc_456",
    "pdf_doc_id": "789",
    "output_location": "s3://bucket/outputs/12345/sessions/session_abc/doc_456/final_upload_form_keys_filled.json"
  }
}
```

## Key Operations

### 1. Document Extraction (`extractor_logic.py`)
- **Purpose**: Extract structured data from documents using OpenAI LLM
- **Supported Formats**: PDF, DOCX, PPTX, XLSX, JSON, TXT
- **Process**:
  1. Extract text from document based on format
  2. Build extraction prompt with schema
  3. Call OpenAI API (gpt-4.1-mini)
  4. Enforce schema structure
  5. Normalize addresses

### 2. Parallel Processing (`main.py`)
- **Thread A**: Document extraction + S3 upload (2 locations)
  - Original format: Nested JSON structure
  - API format: Flattened JSON structure
- **Thread B**: Embedded PDF creation + polling
  - `make_embed_file`: Initiates pipeline processing
  - `check_embed_file`: Polls for completion (max 48 attempts, 10s intervals)

### 3. PDF Filling (`api_handler.py`)
- Calls main pipeline's `fill_pdf` operation
- Combines extracted data with user profile information
- Generates final filled PDF

### 4. Execution Logging (`logger_utils.py`)
- Tracks all operations with timestamps
- Logs API requests/responses
- Saves comprehensive logs to S3

## Environment Variables

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `STATIC_BUCKET` | S3 bucket for config and outputs | `my-static-bucket` |
| `OUTPUT_BUCKET` | S3 bucket for API outputs | `my-output-bucket` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `FILL_PDF_LAMBDA_URL` | Main pipeline Lambda URL | `https://...` |
| `PDF_API_KEY` | API key for main pipeline | `secret-key` |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_INVESTOR_TYPE` | Fallback investor type | `Individual` |

## Hardcoded Dependencies (Requiring Refactoring)

### 🔴 LLM Provider (CRITICAL)
**Location**: `extractor_logic.py` lines 172-214

```python
def call_llm(prompt, logger=None):
    url = "https://api.openai.com/v1/chat/completions"  # ❌ HARDCODED
    
    payload = {
        "model": "gpt-4.1-mini",                        # ❌ HARDCODED
        "temperature": 0,                                # ❌ HARDCODED
        "max_tokens": 2000,                              # ❌ HARDCODED
        ...
    }
```

**Issues**:
- OpenAI URL is hardcoded (line 173)
- Model name `gpt-4.1-mini` is hardcoded (line 183)
- Temperature and max_tokens are hardcoded
- No support for other LLM providers (Anthropic, Azure OpenAI, etc.)
- API key from environment variable `OPENAI_API_KEY` is OpenAI-specific

**Refactoring Required**:
1. Create LLM provider abstraction layer
2. Support multiple providers (OpenAI, Anthropic, Azure, AWS Bedrock)
3. Make model, temperature, max_tokens configurable
4. Use provider-agnostic configuration
5. Example:
   ```python
   LLM_PROVIDER = "openai"  # or "anthropic", "azure", "bedrock"
   LLM_MODEL = "gpt-4.1-mini"
   LLM_TEMPERATURE = 0
   LLM_MAX_TOKENS = 2000
   LLM_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
   ```

### 🔴 Storage Provider (CRITICAL)
**Locations**: 
- `lambda_function.py` lines 66-67, 106-116
- `main.py` lines 115-117
- `s3_handler.py` (entire file)

```python
# lambda_function.py
bucket_base = os.environ.get("STATIC_BUCKET")              # ❌ S3-SPECIFIC
schema_s3_uri = f"s3://{bucket_base}/config/form_keys.json"  # ❌ S3 URI FORMAT
output_s3_uri = f"s3://{bucket_base}/outputs/..."          # ❌ S3 URI FORMAT

# main.py
schema = load_json_from_s3(schema_s3_uri)                  # ❌ S3-SPECIFIC
local_pdf = download_pdf_to_tmp(pdf_s3_uri)                # ❌ S3-SPECIFIC
upload_json_to_s3(result, output_s3_uri)                   # ❌ S3-SPECIFIC
```

**Issues**:
- All storage operations assume AWS S3
- S3 URI format `s3://bucket/key` is hardcoded
- No support for Azure Blob Storage, Google Cloud Storage, local files
- Functions like `load_json_from_s3`, `download_pdf_to_tmp`, `upload_json_to_s3` are S3-specific

**Refactoring Required**:
1. Create storage provider abstraction layer
2. Support multiple storage providers (S3, Azure Blob, GCS, local)
3. Use provider-agnostic URIs (e.g., `storage://bucket/key`)
4. Example:
   ```python
   STORAGE_PROVIDER = "s3"  # or "azure_blob", "gcs", "local"
   STATIC_BUCKET = "my-bucket"
   
   # Abstract functions:
   storage.download(uri)
   storage.upload(data, uri)
   storage.load_json(uri)
   ```

### 🟡 Main Pipeline API Dependency (MEDIUM)
**Location**: `lambda_function.py` lines 68-69

```python
fill_pdf_lambda_url = os.environ.get("FILL_PDF_LAMBDA_URL")  # ❌ DIRECT COUPLING
pdf_api_key = os.environ.get("PDF_API_KEY")                  # ❌ DIRECT COUPLING
```

**Issues**:
- Tightly coupled to main pipeline Lambda URL
- API key authentication is hardcoded approach
- No abstraction for different deployment scenarios (local, different cloud)

**Refactoring Required**:
1. Create pipeline client abstraction
2. Support different authentication methods (API key, JWT, IAM)
3. Support local/development mode (direct function calls)

### 🟡 Document Format Support (MEDIUM)
**Location**: `extractor_logic.py` lines 109-124

```python
extractors = {
    '.pdf': extract_pdf_text,      # PyMuPDF (fitz)
    '.docx': extract_docx_text,    # python-docx
    '.pptx': extract_pptx_text,    # python-pptx
    '.xlsx': extract_xlsx_text,    # openpyxl
    ...
}
```

**Issues**:
- Supported formats are hardcoded
- No plugin system for adding new formats
- Extraction libraries are tightly coupled

**Refactoring Required**:
1. Create document extractor plugin system
2. Support dynamic format registration
3. Decouple extraction logic from format detection

## Performance Optimization

### Parallel Processing Benefits
- **Before**: Sequential processing (~120s total)
  - Extract PDF: 60s
  - make_embed_file: 5s
  - check_embed_file (polling): 45s
  - fill_pdf: 10s

- **After**: Parallel processing (~65s total)
  - Thread A (Extract + Upload): 60s
  - Thread B (make_embed + check_embed): 50s
  - **Both run in parallel** (max = 60s)
  - fill_pdf: 10s
  - **Total savings**: ~55s (46% faster)

## Error Handling

### Validation Errors (400)
- Missing required fields
- Invalid API key
- Invalid user_id or pdf_doc_id format

### Configuration Errors (500)
- Missing environment variables
- Invalid S3 URIs

### Processing Errors (500)
- Document extraction failures
- API call failures
- Timeout errors (embed file polling)

## Dependencies

### Python Packages (requirements.txt)
```
requests          # API calls
boto3             # S3 operations
PyMuPDF           # PDF extraction (fitz)
python-docx       # DOCX extraction
python-pptx       # PPTX extraction
openpyxl          # XLSX extraction
python-dotenv     # Environment variables
```

## Integration Points

### Upstream Dependencies
- S3: Input PDF location
- S3: Config schema (`form_keys.json`)
- OpenAI API: Document extraction

### Downstream Dependencies
- Main Pipeline Lambda: `make_embed_file`, `check_embed_file`, `fill_pdf` operations
- S3: Output storage (2 locations)
- S3: Log storage

## Logging Structure

### Log Entry Format
```json
{
  "timestamp": "2025-01-29T10:30:45.123Z",
  "level": "INFO",
  "message": "Starting PDF extraction",
  "details": {
    "user_id": "12345",
    "pdf_doc_id": "789",
    "operation": "extract"
  }
}
```

### Log Sections
1. **Process Logs**: Pipeline step tracking
2. **API Request Logs**: Outbound API calls
3. **API Response Logs**: API call results
4. **Error Logs**: Failures with stack traces
5. **Summary**: Execution time and status

## Deployment

### Lambda Configuration
- **Runtime**: Python 3.9+
- **Memory**: 1024 MB (recommended)
- **Timeout**: 900s (15 minutes for long documents)
- **Trigger**: Lambda Function URL with API Key authentication

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::static-bucket/*",
        "arn:aws:s3:::output-bucket/*"
      ]
    }
  ]
}
```

## Known Limitations

1. **OpenAI Dependency**: Cannot switch to other LLM providers without code changes
2. **S3 Dependency**: Cannot use Azure Blob or GCS without rewriting storage layer
3. **Single Document Processing**: No batch processing support
4. **Synchronous**: Long-running extractions can timeout (15-minute Lambda limit)
5. **No Retry Logic**: Failed extractions require complete restart
6. **No Partial Success**: If one thread fails, entire operation fails

## Refactoring Roadmap

### Phase 1: Configuration Externalization
- Move all hardcoded values to environment variables
- Create configuration schema
- Add validation layer

### Phase 2: LLM Provider Abstraction
- Create `LLMProvider` interface
- Implement OpenAI, Anthropic, Azure OpenAI providers
- Make provider configurable via environment variable

### Phase 3: Storage Provider Abstraction
- Create `StorageProvider` interface
- Implement S3, Azure Blob, GCS providers
- Unify URI format across providers

### Phase 4: Async Processing
- Convert to async/await pattern
- Implement proper retry logic
- Add circuit breaker for external dependencies

### Phase 5: Monitoring & Observability
- Add distributed tracing (X-Ray)
- Implement structured logging
- Add custom CloudWatch metrics

## Related Modules

### Main Pipeline (`src/`)
- Provides: `make_embed_file`, `check_embed_file`, `fill_pdf` operations
- Dependency: This module calls main pipeline APIs

### chatbot_lambda (To Be Documented)
- Purpose: TBD
- Integration: TBD

### rag_lambda (To Be Documented)
- Purpose: TBD
- Integration: TBD

---

**Last Updated**: 2025-01-29
**Version**: 1.0.0
**Maintainer**: Development Team
