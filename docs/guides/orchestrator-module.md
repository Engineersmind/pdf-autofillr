# Module Documentation: PDF Autofiller Orchestrator (src/)

## Overview
The `src/` orchestrator is the **cloud-agnostic core pipeline** for automated PDF form filling. It provides a pure file-based processing layer with NO knowledge of cloud storage, databases, or platform-specific APIs. This modular architecture enables deployment across AWS Lambda, Azure Functions, Google Cloud Functions, or local environments by wrapping the orchestrator with platform-specific adapters.

## Purpose
- **Extract** form fields from PDF documents using PyMuPDF (Fitz)
- **Map** extracted fields to input schema using semantic LLM matching
- **Embed** mapped field metadata back into PDF using Java utility
- **Fill** PDF forms with actual data using Java iText library
- Provide pure orchestration with LOCAL file paths only
- Enable multi-cloud deployment through platform adapters

## Architecture

### Design Philosophy
```
┌─────────────────────────────────────────────────────────────┐
│          CLOUD-AGNOSTIC ORCHESTRATOR (src/)                 │
│                                                              │
│  ALL inputs/outputs are LOCAL file paths (/tmp/*.pdf)      │
│  NO cloud storage, database, or API dependencies           │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
    ┌─────▼─────┐     ┌────▼──────┐    ┌────▼──────┐
    │  Lambda   │     │  Azure    │    │   GCP     │
    │  Wrapper  │     │  Wrapper  │    │  Wrapper  │
    └───────────┘     └───────────┘    └───────────┘
         │                  │                 │
    ┌────▼──────────────────▼─────────────────▼─────┐
    │   Platform-specific: S3, Blob, GCS            │
    │   Download → /tmp → Orchestrator → Upload     │
    └────────────────────────────────────────────────┘
```

### Module Structure
```
src/
├── orchestrator.py              # Main pipeline orchestration (612 lines)
├── extractors/
│   ├── detailed_fitz.py         # PDF form field extraction (2235 lines)
│   └── fitz_extract_lines.py    # Line-by-line extraction utility
├── mappers/
│   └── semantic_mapper.py       # LLM-based field mapping (1332 lines)
├── embedders/
│   └── embed_keys.py            # Java PDF rebuilder wrapper (130 lines)
├── fillers/
│   └── fill_pdf.py              # Java iText filler wrapper (152 lines)
├── clients/
│   ├── llm_clients/
│   │   ├── factory.py           # LLM client factory
│   │   ├── claude_client.py     # AWS Bedrock Claude client
│   │   ├── openai_client.py     # OpenAI API client
│   │   └── response.py          # LLM response wrapper
│   ├── s3_client.py             # AWS S3 storage client
│   ├── api_client.py            # Backend API client
│   └── auth_client.py           # Authentication client
├── core/
│   ├── config.py                # Configuration management (624 lines)
│   └── logger.py                # Logging configuration
├── chunkers/                    # Text chunking strategies
├── groupers/                    # Field grouping logic
├── headers/                     # PDF header/footer detection
├── java_utils/                  # Java utility helpers
├── models/
│   └── bounding_box.py          # Bounding box model
├── utils/
│   ├── storage.py               # Storage abstraction
│   ├── timing.py                # Performance timing
│   └── helpers.py               # Utility functions
└── validators/                  # Data validation
```

## Core Pipeline: PDFPipeline Class

### Entry Point
**File**: `src/orchestrator.py`
**Class**: `PDFPipeline`

### Constructor
```python
pipeline = PDFPipeline(config={
    'llm_provider': 'claude',           # or 'openai'
    'mapper_method': 'semantic',
    'confidence_threshold': 0.7,
    'chunking_strategy': 'page'
})
```

### 4-Stage Pipeline

#### Stage 1: Extract
**Method**: `await pipeline.extract(pdf_path, output_path)`

**Purpose**: Extract form fields from PDF using PyMuPDF (Fitz)

**Input**:
- `pdf_path`: `/tmp/form.pdf` (local file)
- `output_path`: `/tmp/form_extracted.json` (optional)

**Process**:
1. Load PDF with PyMuPDF (Fitz)
2. Analyze document structure (pages, fonts, styles)
3. Extract form fields with metadata:
   - Field name (if available)
   - Field type (text, checkbox, radio, dropdown)
   - Bounding box (x, y, width, height)
   - Page number
   - Context (surrounding text, section headers)
4. Detect headers/footers and repeated elements
5. Classify heading hierarchy (h1, h2, h3)
6. Save extracted data to JSON

**Output**:
```json
{
  "output_file": "/tmp/form_extracted.json",
  "execution_time_seconds": 2.5,
  "status": "success",
  "extracted_data": {
    "pages": [...],
    "fields": [
      {
        "field_name": "investor_name",
        "field_type": "text",
        "page": 1,
        "bbox": {"x": 100, "y": 200, "width": 300, "height": 25},
        "context": {
          "preceding_text": "Full Legal Name:",
          "section_header": "Investor Information",
          "page_header": "Subscription Agreement"
        }
      }
    ]
  }
}
```

**Extractor Details** (`src/extractors/detailed_fitz.py`):
- **2235 lines** of sophisticated PDF analysis
- **Document-level analysis**: Cross-page context, font patterns, heading sequences
- **Header/Footer detection**: Repeated text across pages
- **Heading classification**: h1, h2, h3 with numbering pattern detection
- **Context enrichment**: Section headers, surrounding text, page context

#### Stage 2: Map
**Method**: `await pipeline.map(extracted_json, input_schema, output_path)`

**Purpose**: Map extracted PDF fields to input data schema using LLM

**Input**:
- `extracted_json`: `/tmp/form_extracted.json`
- `input_schema`: `/tmp/input_data.json` (schema with field descriptions)
- `output_path`: `/tmp/form_mapped.json` (optional)

**Input Schema Example**:
```json
{
  "investor_full_legal_name": {
    "description": "Legal name of investor as it appears on government ID",
    "value": "John Michael Doe"
  },
  "investor_ssn": {
    "description": "Social Security Number (format: XXX-XX-XXXX)",
    "value": "123-45-6789"
  },
  "investment_amount": {
    "description": "Total investment amount in USD",
    "value": "100000"
  }
}
```

**Process**:
1. **Chunking**: Split extracted fields into manageable chunks
   - **Page-based**: Group by page (default)
   - **Window-based**: Sliding window with overlap
2. **Semantic Matching**: For each chunk, use LLM to match fields
   - Prompt: "Match PDF field names to input schema keys"
   - Context: Field name, type, context, section header
   - Input keys: Schema keys with descriptions
   - LLM: Returns best match + confidence score
3. **Confidence Filtering**: Only keep matches above threshold (default: 0.7)
4. **Radio Group Detection**: Identify radio button groups
5. **Save Results**: Mapping JSON + radio groups JSON

**Output**:
```json
{
  "output_files": {
    "mapping": "/tmp/form_mapped.json",
    "radio_groups": "/tmp/form_radio.json"
  },
  "execution_time_seconds": 5.3,
  "status": "success",
  "mapped_data": {
    "mapping": {
      "investor_name": "investor_full_legal_name",
      "ssn_field": "investor_ssn",
      "amount": "investment_amount"
    },
    "radio_groups": {
      "entity_type": ["individual", "corporation", "partnership"]
    }
  }
}
```

**Mapper Details** (`src/mappers/semantic_mapper.py`):
- **1332 lines** of semantic matching logic
- **LLM Integration**: Supports Claude (Bedrock) and OpenAI
- **Chunking Strategies**: Page-based, window-based
- **Token Management**: tiktoken for token counting
- **Parallel Processing**: ThreadPoolExecutor for concurrent LLM calls
- **Confidence Scoring**: Configurable threshold (default: 0.7)
- **Key Variants**: Optional support for fuzzy matching
- **Description Support**: Uses field descriptions for better matching

#### Stage 3: Embed
**Method**: `await pipeline.embed(original_pdf, extracted_json, mapping_json, radio_json)`

**Purpose**: Embed mapped field metadata into PDF using Java utility

**Input**:
- `original_pdf`: `/tmp/form.pdf`
- `extracted_json`: `/tmp/form_extracted.json`
- `mapping_json`: `/tmp/form_mapped.json`
- `radio_json`: `/tmp/form_radio.json`

**Process**:
1. Locate Java rebuilder JAR (`rebuilder.jar`)
   - Check root directory
   - Check assets/rebuilder.jar
   - Check /opt/rebuilder.jar (Lambda layer)
2. Validate all input files exist
3. Execute Java subprocess:
   ```bash
   java -jar rebuilder.jar \
     /tmp/form.pdf \
     /tmp/form_extracted.json \
     /tmp/form_mapped.json \
     /tmp/form_radio.json \
     /tmp/form_embedded.pdf
   ```
4. Java utility rebuilds PDF with embedded metadata
5. Return path to embedded PDF

**Output**:
```json
{
  "output_file": "/tmp/form_embedded.pdf",
  "execution_time_seconds": 1.2,
  "status": "success"
}
```

**Java Utility** (`rebuilder.jar`):
- **Purpose**: Embed mapped field names into PDF form
- **Technology**: Java iText library
- **Process**: Reads PDF, updates form field metadata, saves new PDF
- **Output**: PDF with standardized field names matching input schema

#### Stage 4: Fill
**Method**: `await pipeline.fill(embedded_pdf, input_data, output_path)`

**Purpose**: Fill PDF form with actual data using Java iText

**Input**:
- `embedded_pdf`: `/tmp/form_embedded.pdf`
- `input_data`: `/tmp/input_data.json`

**Process**:
1. Locate Java filler JAR (`filler.jar`)
   - Check root directory
   - Check assets/filler.jar
   - Check /opt/filler.jar (Lambda layer)
2. Validate input files exist
3. Execute Java subprocess:
   ```bash
   java -jar filler.jar \
     /tmp/form_embedded.pdf \
     /tmp/input_data.json \
     /tmp/form_filled.pdf
   ```
4. Java utility fills form fields with data values
5. Return path to filled PDF

**Output**:
```json
{
  "output_file": "/tmp/form_filled.pdf",
  "execution_time_seconds": 0.8,
  "status": "success"
}
```

**Java Utility** (`filler.jar`):
- **Purpose**: Fill PDF form fields with data values
- **Technology**: Java iText library
- **Process**: Reads embedded PDF, maps data to fields, fills and flattens PDF
- **Output**: Completed filled PDF ready for user

### Complete Pipeline: run_all()

**Method**: `await pipeline.run_all(input_pdf, input_data, output_path)`

**Purpose**: Execute all 4 stages sequentially

**Input**:
- `input_pdf_path`: `/tmp/form.pdf`
- `input_data_path`: `/tmp/data.json`
- `output_path`: `/tmp/form_filled.pdf` (optional)
- `config`: Pipeline configuration (optional)
- `keep_intermediates`: Keep intermediate files (default: True)

**Complete Process**:
```
1. Extract   →  form.pdf  →  form_extracted.json  (2.3s)
2. Map       →  extracted + data  →  mapped.json + radio.json  (7.8s)
3. Embed     →  form.pdf + mapped  →  form_embedded.pdf  (1.5s)
4. Fill      →  embedded + data  →  form_filled.pdf  (0.9s)
────────────────────────────────────────────────────────────
Total Pipeline: 12.5 seconds
```

**Output**:
```json
{
  "status": "success",
  "final_output": "/tmp/form_filled.pdf",
  "all_outputs": {
    "extracted_json": "/tmp/form_extracted.json",
    "mapping_json": "/tmp/form_mapped.json",
    "radio_groups": "/tmp/form_radio.json",
    "embedded_pdf": "/tmp/form_embedded.pdf",
    "filled_pdf": "/tmp/form_filled.pdf"
  },
  "timing": {
    "total_pipeline_seconds": 12.5,
    "stage_breakdown": {
      "extract": 2.3,
      "map": 7.8,
      "embed": 1.5,
      "fill": 0.9
    },
    "stage_percentages": {
      "extract": 18.4,
      "map": 62.4,
      "embed": 12.0,
      "fill": 7.2
    }
  },
  "pipeline_stages": {
    "extract": { /* stage 1 details */ },
    "map": { /* stage 2 details */ },
    "embed": { /* stage 3 details */ },
    "fill": { /* stage 4 details */ }
  }
}
```

## LLM Client Architecture

### Factory Pattern
**File**: `src/clients/llm_clients/factory.py`

**Class**: `LLMClientFactory` (also aliased as `LLMSelector`)

**Purpose**: Abstract LLM provider selection

**Supported Providers**:
1. **Claude** (AWS Bedrock)
2. **OpenAI** (API)

**Usage**:
```python
from src.clients.llm_clients import LLMSelector

# Create LLM client
llm = LLMSelector(provider="claude")  # or "openai"

# Complete prompt
response = llm.llm.complete(prompt="Map these fields...")
print(response.text)
```

### Claude Client
**File**: `src/clients/llm_clients/claude_client.py`

**Class**: `ClaudeLLMClient`

**Provider**: AWS Bedrock (boto3)

**Configuration**:
```python
ClaudeLLMClient(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1",
    temperature=0.1,
    max_tokens=20000
)
```

**API Call**:
```python
# Prepare request
body = {
    "anthropic_version": "bedrock-2023-05-31",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 20000,
    "temperature": 0.1
}

# Call Bedrock
response = bedrock.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    contentType="application/json",
    body=json.dumps(body)
)

# Parse response
result = json.loads(response['body'].read())
content = result["content"][0]["text"]
```

**Session Support**: Maintains conversation history

### OpenAI Client
**File**: `src/clients/llm_clients/openai_client.py`

**Class**: `OpenAILLMClient`

**Provider**: OpenAI API

**Configuration**:
```python
OpenAILLMClient(
    model_id="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
    max_tokens=2048
)
```

**Special Handling**:
- **Reasoning Models** (o1, o3, o3-mini): No temperature parameter
- **Reasoning API Models** (gpt-5-mini): Special API format
- **Standard Models**: Normal chat completion API

**API Call**:
```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.1,
    max_completion_tokens=2048
)

content = response.choices[0].message.content
```

## Configuration System

### Configuration File
**File**: `src/core/config.py`

**Class**: `Settings` (Pydantic BaseSettings)

**Total Lines**: 624 lines

### Configuration Categories

#### 1. LLM Configuration
```python
llm_current_provider: str = "claude"      # Default provider
llm_max_threads: int = 10                 # Parallel LLM calls

# Claude/Bedrock
claude_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
claude_region: str = "us-east-1"
claude_temperature: float = 0.1
claude_max_tokens: int = 20000

# OpenAI
openai_model_id: str = "gpt-4"
openai_api_key: str = ""
openai_temperature: float = 0.1
openai_max_tokens: int = 2048
```

#### 2. Mapper Configuration
```python
mapper_current_method: str = "semantic"
mapper_method_llm: str = "claude"
mapper_method_confidence_threshold: float = 0.7
mapper_method_include_key_variants: int = 0
mapper_method_include_field_name_variants: int = 0
mapper_method_include_description: int = 1  # Use field descriptions
```

#### 3. Chunking Strategy
```python
mapper_chunking_current_strategy: str = "page"  # or "window"
mapper_chunking_page_chunk_size: int = 9
mapper_chunking_page_overlap: int = 1
mapper_chunking_window_prefix_threshold: int = 10
mapper_chunking_window_suffix_threshold: int = 10
mapper_chunking_window_lines_limit: int = 400
```

#### 4. Storage Configuration
```python
storage_type: str = "local"  # or "s3"
storage_s3_bucket: str = ""
storage_s3_prefix: str = ""
```

#### 5. File Paths
```python
data_input_dir: str = "data/input"
temp_data_dir: str = "data/temp"
data_output_dir: str = "data/output"
```

#### 6. Notifications
```python
notifications_enabled: bool = True
notifications_backend_url: str = ""
notifications_api_key: str = ""
notifications_timeout_seconds: int = 30
notifications_max_retries: int = 3
notifications_fail_silently: bool = True
```

#### 7. Authentication
```python
auth_api_base_url: str = "https://dev-autofiller-backend.engineersmind.dev"
auth_email: str = ""
auth_password: str = ""
```

### Environment Variables

All configuration can be overridden via environment variables:

```bash
# LLM Provider
LLM_CURRENT_PROVIDER=claude
LLM_MAX_THREADS=10

# Claude
CLAUDE_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
CLAUDE_REGION=us-east-1
CLAUDE_TEMPERATURE=0.1
CLAUDE_MAX_TOKENS=20000

# OpenAI
OPENAI_MODEL_ID=gpt-4
OPENAI_API_KEY=sk-...
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=2048

# Mapper
MAPPER_METHOD_LLM=claude
MAPPER_METHOD_CONFIDENCE_THRESHOLD=0.7
MAPPER_METHOD_INCLUDE_DESCRIPTION=1

# Chunking
MAPPER_CHUNKING_CURRENT_STRATEGY=page
MAPPER_CHUNKING_PAGE_CHUNK_SIZE=9

# Storage
STORAGE_TYPE=local
STORAGE_S3_BUCKET=my-bucket
```

## Hardcoded Dependencies (Requiring Refactoring)

### 🔴 LLM Provider (HIGH PRIORITY)

#### Location 1: Factory Pattern
**File**: `src/clients/llm_clients/factory.py` lines 3-4, 24-38

```python
from src.clients.llm_clients.claude_client import ClaudeLLMClient    # ❌ HARDCODED
from src.clients.llm_clients.openai_client import OpenAILLMClient   # ❌ HARDCODED

class LLMClientFactory:
    def __init__(self, provider=None):
        if self.provider == "claude":                # ❌ ONLY 2 PROVIDERS
            self.llm = ClaudeLLMClient(...)
        elif self.provider == "openai":
            self.llm = OpenAILLMClient(...)
        else:
            raise ValueError(f"Unsupported: {self.provider}")  # ❌ NO EXTENSIBILITY
```

**Issues**:
- Only 2 providers hardcoded: Claude (Bedrock), OpenAI
- No support for: Anthropic direct, Azure OpenAI, AWS Bedrock (non-Claude), Cohere, AI21
- Cannot add new providers without code changes
- Factory has if/elif chain (not extensible)

#### Location 2: Claude Client (AWS Bedrock)
**File**: `src/clients/llm_clients/claude_client.py` lines 2-3, 20-21

```python
import boto3                                         # ❌ AWS-SPECIFIC
from botocore.config import Config

class ClaudeLLMClient:
    def __init__(self, ...):
        config = Config(region_name=region, ...)
        self.bedrock = boto3.client("bedrock-runtime", config=config)  # ❌ BEDROCK ONLY
```

**Issues**:
- Claude only accessible via AWS Bedrock
- Cannot use Anthropic API directly
- Requires AWS credentials
- boto3 dependency is AWS-specific

#### Location 3: OpenAI Client
**File**: `src/clients/llm_clients/openai_client.py` lines 3, 22

```python
import openai                                        # ❌ OPENAI-SPECIFIC

class OpenAILLMClient:
    def __init__(self, ...):
        self.client = openai.OpenAI(api_key=api_key)  # ❌ OPENAI SDK ONLY
```

**Issues**:
- Only supports OpenAI API
- No support for Azure OpenAI (different endpoint/auth)
- Special handling for reasoning models (o1, o3, gpt-5-mini)
- openai SDK dependency

#### Location 4: Semantic Mapper
**File**: `src/mappers/semantic_mapper.py` lines 67, 31

```python
from src.clients.llm_clients import LLMSelector      # ❌ HARDCODED FACTORY

llm_provider: str = None  # "claude", "openai"      # ❌ ONLY 2 OPTIONS

LLM = LLMSelector(provider=llm_name)                # ❌ DIRECT COUPLING
self.llm = LLM.llm
```

**Issues**:
- Tightly coupled to LLMSelector factory
- Only accepts "claude" or "openai"
- No abstraction layer for LLM interface
- Cannot inject custom LLM clients

**Refactoring Required**:
1. **Create LLM Provider Interface**:
   ```python
   class LLMProvider(ABC):
       @abstractmethod
       def complete(self, prompt: str, session_messages: list = None) -> LLMResponse:
           pass
   ```

2. **Plugin-Based Architecture**:
   ```python
   LLM_PROVIDERS = {
       "claude_bedrock": ClaudeBedrockProvider,
       "claude_api": ClaudeAPIProvider,
       "openai": OpenAIProvider,
       "azure_openai": AzureOpenAIProvider,
       "anthropic": AnthropicProvider,
       "bedrock_titan": BedrockTitanProvider,
       "cohere": CohereProvider
   }
   
   def get_llm_provider(provider_name: str) -> LLMProvider:
       return LLM_PROVIDERS[provider_name]()
   ```

3. **Configuration Changes**:
   ```python
   LLM_PROVIDER = "claude_bedrock"  # or any registered provider
   LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
   LLM_TEMPERATURE = 0.1
   LLM_MAX_TOKENS = 20000
   ```

### 🔴 Java Utilities (HIGH PRIORITY)

#### Location 1: Embedder
**File**: `src/embedders/embed_keys.py` lines 89-97

```python
jar_path = None
possible_jar_paths = [
    "rebuilder.jar",                    # ❌ HARDCODED FILENAME
    "assets/rebuilder.jar",             # ❌ HARDCODED PATHS
    "/opt/rebuilder.jar",               # ❌ LAMBDA-SPECIFIC
    ...
]

cmd = ["java", "-jar", jar_path, ...]   # ❌ SUBPROCESS CALL
result = subprocess.run(cmd, ...)       # ❌ JAVA DEPENDENCY
```

**Issues**:
- Requires Java runtime installed
- Requires `rebuilder.jar` file available
- Subprocess overhead (500ms-2s per call)
- No error recovery if Java fails
- Lambda layer dependency

#### Location 2: Filler
**File**: `src/fillers/fill_pdf.py` lines 75-83

```python
possible_jar_paths = [
    "filler.jar",                       # ❌ HARDCODED FILENAME
    "assets/filler.jar",                # ❌ HARDCODED PATHS
    "/opt/filler.jar",                  # ❌ LAMBDA-SPECIFIC
    ...
]

cmd = ["java", "-jar", jar_path, ...]   # ❌ SUBPROCESS CALL
result = subprocess.run(cmd, ...)       # ❌ JAVA DEPENDENCY
```

**Issues**:
- Same issues as embedder
- Requires Java runtime and JAR file
- Subprocess overhead
- Lambda layer dependency

**Refactoring Required**:
1. **Replace Java with Python Libraries**:
   - **Option 1**: PyPDF2 or pypdf for PDF manipulation
   - **Option 2**: PDFtk Server wrapper (still subprocess, but more standard)
   - **Option 3**: Reportlab for PDF generation

2. **Create PDF Utility Abstraction**:
   ```python
   class PDFEmbedder(ABC):
       @abstractmethod
       def embed_fields(self, pdf_path, extracted, mapping, radio) -> str:
           pass
   
   class JavaEmbedder(PDFEmbedder):
       # Current Java implementation
   
   class PythonEmbedder(PDFEmbedder):
       # Pure Python implementation with PyPDF2/pypdf
   
   # Configuration
   PDF_EMBEDDER = "python"  # or "java"
   PDF_FILLER = "python"    # or "java"
   ```

3. **Benefits**:
   - No Java runtime dependency
   - Faster execution (no subprocess overhead)
   - Better error handling
   - Native Python stack

### 🔴 AWS Bedrock Dependency (HIGH PRIORITY)

#### Location: Claude Client
**File**: `src/clients/llm_clients/claude_client.py` lines 2, 20

```python
import boto3                                         # ❌ AWS SDK
from botocore.config import Config

self.bedrock = boto3.client("bedrock-runtime", config=config)  # ❌ BEDROCK
```

**Issues**:
- Claude only accessible via AWS Bedrock
- Cannot use Anthropic API directly
- Requires AWS account and credentials
- Region-specific (must be in supported Bedrock region)
- boto3 is AWS-specific dependency

**Refactoring Required**:
1. **Support Anthropic Direct API**:
   ```python
   import anthropic
   
   client = anthropic.Anthropic(api_key=api_key)
   message = client.messages.create(
       model="claude-3-sonnet-20240229",
       max_tokens=20000,
       messages=[{"role": "user", "content": prompt}]
   )
   ```

2. **Make Bedrock Optional**:
   ```python
   CLAUDE_PROVIDER = "anthropic"  # or "bedrock"
   CLAUDE_API_KEY = "sk-ant-..."
   # OR
   CLAUDE_PROVIDER = "bedrock"
   CLAUDE_REGION = "us-east-1"
   ```

### 🟡 Storage Provider (MEDIUM PRIORITY)

#### Location: S3 Client
**File**: `src/clients/s3_client.py` (entire file)

```python
import boto3                                         # ❌ AWS-SPECIFIC

s3_client = boto3.client('s3')                      # ❌ S3 ONLY
```

**Issues**:
- All storage operations assume AWS S3
- No support for Azure Blob Storage, Google Cloud Storage
- boto3 is AWS-specific
- S3-specific URIs (s3://bucket/key)

**Current Mitigation**:
- `src/utils/storage.py` provides storage abstraction
- Config: `STORAGE_TYPE = "local"` or `"s3"`
- Local storage works fine for orchestrator

**Refactoring Required**:
1. **Extend Storage Abstraction**:
   ```python
   STORAGE_PROVIDER = "local"  # or "s3", "azure_blob", "gcs"
   ```

2. **Already Good**: Orchestrator uses LOCAL paths only, storage is wrapper concern

### 🟡 Backend API Coupling (MEDIUM PRIORITY)

#### Location: API Client
**File**: `src/clients/api_client.py` (entire file)

**Issues**:
- Tightly coupled to specific backend API
- Hardcoded endpoints
- Specific authentication flow
- Not part of core orchestrator (only used by Lambda wrappers)

**Current Mitigation**:
- Orchestrator has NO backend API dependency
- Backend calls are in Lambda wrappers only
- Pure orchestrator is API-agnostic

**Refactoring Required**:
- Already good separation
- Backend API coupling is in Lambda layer (expected)

### 🟢 Good Architecture (Already Cloud-Agnostic)

#### ✅ Orchestrator Design
**File**: `src/orchestrator.py`

**Strengths**:
- ALL inputs/outputs are local file paths
- NO cloud storage dependencies
- NO database dependencies
- NO API dependencies
- Pure processing logic

**Example**:
```python
# ✅ GOOD: Local file paths only
result = await pipeline.run_all(
    input_pdf_path="/tmp/form.pdf",
    input_data_path="/tmp/data.json"
)
# Output: /tmp/form_filled.pdf
```

#### ✅ Storage Abstraction
**File**: `src/utils/storage.py`

**Strengths**:
- Configurable storage backend
- Supports local and S3
- Easy to extend (Azure Blob, GCS)

**Configuration**:
```python
STORAGE_TYPE = "local"  # or "s3"
```

## Performance Characteristics

### Stage Timing (Typical)
| Stage | Duration | % of Total | Bottleneck |
|-------|----------|------------|------------|
| **Extract** | 2-3s | 18-25% | PDF parsing |
| **Map** | 6-10s | 50-70% | **LLM API calls** |
| **Embed** | 1-2s | 10-15% | Java subprocess |
| **Fill** | 0.5-1s | 5-10% | Java subprocess |
| **Total** | **10-16s** | 100% | **Mapping stage** |

### Bottlenecks

#### 1. LLM API Calls (Mapping Stage)
- **Issue**: Sequential LLM calls for each chunk
- **Mitigation**: ThreadPoolExecutor for parallel calls (default: 10 threads)
- **Configuration**: `LLM_MAX_THREADS=10`
- **Cost**: ~$0.02-0.05 per PDF (Claude Sonnet)

#### 2. Java Subprocess Overhead
- **Issue**: Subprocess spawn + JVM startup
- **Embed**: 1-2s per call
- **Fill**: 0.5-1s per call
- **Mitigation**: Keep JVM warm (not currently implemented)
- **Alternative**: Replace with Python libraries

#### 3. PDF Parsing (Extract Stage)
- **Issue**: Large PDFs with complex layouts
- **Duration**: 2-5s for typical forms
- **Scales with**: Number of pages, form fields, embedded fonts

### Scalability Limits

#### Lambda Deployment
- **Max execution time**: 15 minutes (more than enough)
- **/tmp storage**: 512 MB (sufficient for most PDFs)
- **Memory**: 1-2 GB recommended
- **Cold start**: 5-10s (mostly LLM client initialization)

#### Concurrent Processing
- **LLM API rate limits**: Claude/OpenAI rate limits apply
- **Parallel threads**: Default 10, configurable
- **Memory per PDF**: 50-100 MB

## Integration Points

### Upstream Dependencies
- **None** (orchestrator is standalone)
- Platform wrappers download files to /tmp

### Downstream Dependencies
- **PyMuPDF (Fitz)**: PDF parsing and extraction
- **LLM APIs**: Claude (Bedrock) or OpenAI
- **Java Runtime**: For embed/fill utilities (can be replaced)
- **Python Libraries**: tiktoken, pydantic, asyncio

### Platform Wrappers
- **Lambda Wrapper** (`lambda_handler.py`): Downloads from S3 → orchestrator → uploads
- **Azure Wrapper** (future): Downloads from Blob → orchestrator → uploads
- **GCP Wrapper** (future): Downloads from GCS → orchestrator → uploads

## Known Limitations

1. **LLM Provider Lock-in**: Only Claude (Bedrock) and OpenAI supported
2. **Java Dependency**: Embed and fill stages require Java runtime + JAR files
3. **No Streaming**: Pipeline processes entire PDF at once (no streaming)
4. **Single PDF**: No batch processing of multiple PDFs
5. **No Validation**: No schema validation before filling
6. **No Rollback**: Cannot undo fill operation
7. **Limited Error Recovery**: If mapping fails, entire pipeline fails
8. **No Caching**: LLM calls are not cached (duplicate PDFs re-process)
9. **Token Limits**: Very large PDFs may exceed LLM context windows
10. **No Human Review**: Cannot pause pipeline for human validation

## Refactoring Roadmap

### Phase 1: LLM Provider Abstraction (HIGH PRIORITY)
**Goal**: Support multiple LLM providers without code changes

**Tasks**:
1. Create `LLMProvider` interface (abstract base class)
2. Implement providers:
   - Claude Bedrock (existing)
   - Claude API (new, Anthropic direct)
   - OpenAI (existing)
   - Azure OpenAI (new)
   - Cohere (new)
   - AI21 (new)
3. Plugin-based registration system
4. Update configuration to support any provider
5. Update semantic mapper to use interface

**Benefits**:
- Multi-cloud deployment (not locked to AWS Bedrock)
- Easy to add new providers
- Cost optimization (choose cheapest provider)
- Failover support (fallback to secondary provider)

### Phase 2: Replace Java Utilities (HIGH PRIORITY)
**Goal**: Eliminate Java dependency, pure Python stack

**Tasks**:
1. Research Python PDF libraries (PyPDF2, pypdf, reportlab)
2. Implement Python-based embedder
3. Implement Python-based filler
4. Create abstraction layer (`PDFEmbedder`, `PDFFiller` interfaces)
5. Make Java optional (fallback mode)
6. Update tests

**Benefits**:
- No Java runtime dependency
- Faster execution (no subprocess overhead)
- Better error handling
- Easier deployment (no JAR files)
- Native Python debugging

### Phase 3: Caching Layer (MEDIUM PRIORITY)
**Goal**: Reduce duplicate processing and LLM costs

**Tasks**:
1. Implement PDF hash/fingerprinting
2. Cache extraction results (by PDF hash)
3. Cache mapping results (by PDF hash + schema hash)
4. Implement cache storage (Redis, S3, local)
5. Add cache TTL configuration
6. Add cache invalidation

**Benefits**:
- 10-100x faster for duplicate PDFs
- 90% cost reduction for duplicates
- Better user experience (instant results)

### Phase 4: Validation & Error Recovery (MEDIUM PRIORITY)
**Goal**: Robust error handling and data validation

**Tasks**:
1. Schema validation before processing
2. Field type validation after mapping
3. Confidence score validation
4. Retry logic for LLM failures
5. Partial pipeline recovery (resume from failed stage)
6. Detailed error reporting

**Benefits**:
- Fewer pipeline failures
- Better error messages
- Automatic recovery from transient failures
- Reduced manual intervention

### Phase 5: Batch Processing (LOW PRIORITY)
**Goal**: Process multiple PDFs in parallel

**Tasks**:
1. Create batch pipeline interface
2. Parallel PDF processing (ThreadPoolExecutor)
3. Progress tracking
4. Partial failure handling
5. Batch result aggregation

**Benefits**:
- Process 10-100 PDFs in parallel
- Better throughput for large batches
- Cost-effective for bulk operations

### Phase 6: Streaming & Chunking (LOW PRIORITY)
**Goal**: Handle very large PDFs efficiently

**Tasks**:
1. Implement streaming PDF parser
2. Chunked extraction (process page by page)
3. Chunked mapping (process fields in batches)
4. Memory-efficient processing

**Benefits**:
- Support PDFs > 100 pages
- Reduced memory footprint
- No token limit issues

### Phase 7: Human-in-the-Loop (LOW PRIORITY)
**Goal**: Optional human review before filling

**Tasks**:
1. Pause pipeline at validation checkpoints
2. Generate review UI data
3. Accept human corrections
4. Resume pipeline with corrections

**Benefits**:
- Higher accuracy for critical forms
- User confidence in results
- Compliance for regulated industries

## Related Modules

### Lambda Wrappers (Previously Documented)

#### pdf_upload_lambda
- **Purpose**: Upload and process PDFs
- **Integration**: Downloads S3 → calls orchestrator → uploads results
- **Dependencies**: S3, OpenAI (parallel extraction)

#### chatbot_lambda
- **Purpose**: Conversational form filling
- **Integration**: Calls orchestrator via API → manages state in S3
- **Dependencies**: OpenAI (via LangChain), S3, Auth0

#### rag_lambda
- **Purpose**: RAG-based field prediction
- **Integration**: Provides predictions to orchestrator
- **Dependencies**: OpenAI GPT-4, Sentence Transformers, S3

### Main Pipeline Flow
```
┌──────────────────┐
│   Chatbot UI     │  (User interaction)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ chatbot_lambda   │  (State management)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│pdf_upload_lambda │  (S3 → /tmp download)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  rag_lambda      │  (RAG predictions)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  ORCHESTRATOR    │  (Pure processing)
│  (src/)          │  Extract → Map → Embed → Fill
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Lambda Wrapper   │  (/tmp → S3 upload)
└──────────────────┘
```

---

**Last Updated**: 2026-03-02
**Version**: 1.0.0
**Maintainer**: Development Team
**Total Lines Documented**: 5,485 lines across all modules
