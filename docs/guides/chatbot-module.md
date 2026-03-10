# Module Documentation: chatbot_lambda

## Overview
The `chatbot_lambda` module is a conversational AI system that guides users through filling out financial forms via natural language chat. It uses a state machine to orchestrate multi-step workflows, extract structured data from user inputs, and coordinate with backend services for PDF generation.

## Purpose
- Provide conversational interface for form filling
- Guide users through investor type selection and data collection
- Extract structured data from natural language using LLM
- Validate phone numbers and handle re-entry flows
- Coordinate PDF document creation and filling via external APIs
- Maintain session state and conversation history in S3

## Architecture

### Entry Point
- **File**: `lambda_function.py`
- **Handler**: `handler(event, context)`
- **Type**: AWS Lambda Function URL handler with API key authentication

### Module Structure
```
chatbot_lambda/
├── lambda_function.py      # Entry point, authentication, notification
├── chatbot_core.py         # State machine, conversation logic (4813 lines)
├── extraction.py           # LLM-based field extraction
├── prompts.py              # Prompt templates for extraction
├── s3_helper.py            # S3 operations for state/config
├── utils.py                # Validation, formatting utilities
└── requirements.txt        # Dependencies
```

## State Machine Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CHATBOT STATE MACHINE                     │
└─────────────────────────────────────────────────────────────┘

    INIT
      │
      ├──→ Greeting shown?
      │    No: "Hi there, I'm Bot..."
      │    Yes: "Would you like to get started? (yes/no)"
      │
      ▼
    User says "yes"
      │
      ▼
    INVESTOR_TYPE_SELECT
      │
      ├──→ Show investor type options (1-10)
      │    - Individual
      │    - Partnership
      │    - Corporation
      │    - LLC
      │    - Trust
      │    - Non-Profit Organisations
      │    - Fund/Fund of Funds
      │    - IRA
      │    - Government Bodies
      │    - Education Institutions
      │
      ├──→ [PDF INITIALIZATION WORKFLOW]
      │    │
      │    ├──→ Step 1: Auth0 Authentication (10 retries)
      │    │    - Obtain access_token via client_credentials
      │    │
      │    ├──→ Step 2: Fetch PDF Doc ID (10 retries)
      │    │    - Call backend API: GET /api/v1/chat/session/{session_id}/pdf-id
      │    │    - Store pdf_doc_id in session
      │    │
      │    └──→ Step 3: Trigger make_embed_file (background)
      │         - Call main pipeline API
      │         - Run in background thread (non-blocking)
      │
      ▼
    DATA_COLLECTION (Main Loop)
      │
      ├──→ Extract fields from user input via LLM
      │    - Use ChatOpenAI (gpt-4o-mini)
      │    - Fallback to regex extraction if LLM fails
      │
      ├──→ Validate phone numbers
      │    - Check country code format
      │    - Prompt for re-entry if invalid
      │
      ├──→ Deep update live_fill_flat
      │    - Save to S3: live_fill.json
      │
      └──→ Check for overlapping fields
           - Ask user to confirm updates
      │
      ▼
    UPDATE_EXISTING_PROMPT
      │
      ├──→ User confirms field updates (yes/no)
      │
      ▼
    ANOTHER_INFO_PROMPT
      │
      ├──→ "Do you have any other information? (yes/no)"
      │    Yes: Return to DATA_COLLECTION
      │    No: Continue to validation
      │
      ▼
    CONTINUE_PROMPT
      │
      ├──→ Check for missing mandatory fields
      │    Missing? → MISSING_FIELDS_PROMPT
      │    Complete? → MAILING_ADDRESS_CHECK
      │
      ▼
    MISSING_FIELDS_PROMPT
      │
      ├──→ "Ready to continue? (yes/no)"
      │    Yes: → SEQUENTIAL_FILL
      │    No: Exit conversation
      │
      ▼
    SEQUENTIAL_FILL
      │
      ├──→ Ask for missing fields one by one
      │    - Text fields: Direct input
      │    - Boolean groups: Multiple selection
      │
      ▼
    BOOLEAN_GROUP_SELECT
      │
      ├──→ "Select applicable items (comma-separated)"
      │    - Selected: Set to true
      │    - Unselected: Set to false
      │
      ▼
    MAILING_ADDRESS_CHECK
      │
      ├──→ "Is mailing address same as registered? (yes/no)"
      │    Yes: Copy registered → mailing
      │    No: Ask for mailing address
      │
      ▼
    OPTIONAL_FIELDS_PROMPT
      │
      ├──→ "Would you like to fill optional fields? (yes/no)"
      │    Yes: Return to SEQUENTIAL_FILL (optional mode)
      │    No: Proceed to completion
      │
      ▼
    [PDF FILLING WORKFLOW]
      │
      ├──→ Step 4: Check embed_file status (polling)
      │    - Poll main pipeline API until ready
      │
      ├──→ Step 5: Upload combined_input.json to S3
      │    - Flatten live_fill_flat
      │    - Upload to bucket
      │
      └──→ Step 6: Trigger fill_pdf operation
           - Call main pipeline API
           - Generate final filled PDF
      │
      ▼
    COMPLETE
      │
      └──→ "Thank you! Your PDF has been filled successfully."
```

## Key Operations

### 1. Field Extraction (`extraction.py`)
- **Purpose**: Extract structured data from natural language user input
- **Primary Method**: LLM extraction using ChatOpenAI
- **Fallback**: Regex-based extraction if LLM fails
- **Process**:
  1. Build comprehensive prompt with ALL form fields (mandatory + optional)
  2. Include chat history for context
  3. Call OpenAI gpt-4o-mini (temperature=0.0)
  4. Parse JSON response
  5. Validate against schema
  6. Fall back to regex if extraction returns empty

### 2. Phone Validation (`utils.py`)
- **Purpose**: Ensure phone numbers have valid country code format
- **Validation Rules**:
  - Must start with `+` followed by 1-4 digit country code
  - Example: `+1 555 123 4567` (USA)
- **Error Types**:
  - `missing_country_code`: No `+` prefix
  - `invalid_country_code`: Non-numeric or >4 digits
  - `invalid_phone_part`: Malformed number
- **Re-entry Flow**: If invalid, prompt user to re-enter with correct format

### 3. Session State Management (`s3_helper.py`)
- **Files Stored**:
  - `session_state.json`: Current conversation state
  - `live_fill.json`: Form data being filled (nested)
  - `live_fill_flat.json`: Flattened form data
  - `conversation_history.json`: User/bot message history
  - `session_log.json`: Event log with timestamps
  - `debug_conversation.json`: Comprehensive debug logs
  - `pdf_filling_logs.json`: PDF workflow progress
- **Storage**: S3 bucket structure: `{user_id}/sessions/{session_id}/`

### 4. PDF Initialization Workflow (Steps 1-3)
**Triggered**: After investor type selection

**Step 1: Auth0 Authentication**
- **Endpoint**: `https://{AUTH0_DOMAIN}/oauth/token`
- **Method**: Client credentials grant
- **Retry**: Up to 10 attempts with 2s delay
- **Environment Variables**:
  - `AUTH0_DOMAIN`
  - `AUTH0_CLIENT_ID`
  - `AUTH0_CLIENT_SECRET`
  - `AUTH0_AUDIENCE`
- **Output**: `access_token`

**Step 2: Fetch PDF Doc ID**
- **Endpoint**: `{BACKEND_URL}/api/v1/chat/session/{session_id}/pdf-id`
- **Method**: GET with Bearer token
- **Retry**: Up to 10 attempts with 2s delay
- **Output**: `pdf_doc_id` (stored in session)

**Step 3: Trigger make_embed_file (Background)**
- **Call**: Main pipeline Lambda API
- **Operation**: `make_embed_file`
- **Payload**:
  ```json
  {
    "operation": "make_embed_file",
    "user_id": 12345,
    "pdf_doc_id": 789,
    "session_id": "session_abc",
    "investor_type": "Individual",
    "use_second_mapper": true
  }
  ```
- **Execution**: Background thread (non-blocking)
- **Purpose**: Pre-generate embedded PDF while user continues chatting

### 5. PDF Filling Workflow (Steps 4-6)
**Triggered**: After all mandatory fields collected

**Step 4: Check embed_file Status (Polling)**
- **Operation**: `check_embed_file`
- **Polling**: Every 10s, max 48 attempts (8 minutes)
- **Wait**: Until `embedded_pdf_created: true`

**Step 5: Upload combined_input.json**
- **Process**:
  1. Flatten `live_fill_flat` (nested → flat)
  2. Upload to S3: `{user_id}/sessions/{session_id}/combined_input.json`
- **Format**: Key-value pairs for API consumption

**Step 6: Trigger fill_pdf**
- **Operation**: `fill_pdf`
- **Payload**:
  ```json
  {
    "operation": "fill_pdf",
    "user_id": 12345,
    "pdf_doc_id": 789,
    "session_id": "session_abc",
    "use_profile_info": true
  }
  ```
- **Output**: Final filled PDF with presigned URL

### 6. Notification System (Optional)
- **Status**: Currently disabled (`NOTIFICATIONS_ENABLED = False`)
- **Purpose**: Send real-time events to backend notification service
- **Events**:
  - `chatbot_message_processed` (success/failed)
- **Levels**: LOW, NORMAL, HIGH, CRITICAL
- **Protocol**: Async HTTP POST with `X-Event-Key` header

## API Contract

### Input (Lambda Function URL)
```json
{
  "headers": {
    "X-API-Key": "required_api_key",
    "Content-Type": "application/json"
  },
  "body": {
    "user_id": "12345",
    "session_id": "session_abc",
    "user_input": "I am an Individual investor. My name is John Doe and email is john@example.com"
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
    "user_id": "12345",
    "session_id": "session_abc",
    "response": "Thank you! I've recorded that information. Do you have any other information you'd like to provide? (yes/no):",
    "session_complete": false
  }
}
```

### Output (Session Complete)
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "user_id": "12345",
    "session_id": "session_abc",
    "response": "Great! Your form has been filled successfully. Your PDF will be ready shortly.",
    "session_complete": true
  }
}
```

### Output (Error)
```json
{
  "statusCode": 400,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "error": "user_id and session_id are required"
  }
}
```

## Environment Variables

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `AUTH_TOKEN` | API key for Lambda auth | `secret-key` |
| `S3_OUTPUT_BUCKET` | S3 bucket for session state | `chatbot-outputs-prod` |
| `STATIC_BUCKET` | S3 bucket for config files | `config-bucket` |
| `OUTPUT_BUCKET` | S3 bucket for outputs | `output-bucket` |
| `AUTH0_DOMAIN` | Auth0 tenant domain | `tenant.auth0.com` |
| `AUTH0_CLIENT_ID` | Auth0 client ID | `abc123` |
| `AUTH0_CLIENT_SECRET` | Auth0 client secret | `secret` |
| `AUTH0_AUDIENCE` | Auth0 API audience | `https://api.example.com` |
| `BACKEND_URL` | Backend API base URL | `https://api.example.com` |

### Optional (Notifications - Currently Disabled)
| Variable | Description | Default |
|----------|-------------|---------|
| `NOTIFICATION_URL` | Notification service URL | N/A |
| `X_EVENT_KEY` | Event API key | N/A |

## Hardcoded Dependencies (Requiring Refactoring)

### 🔴 LLM Provider (CRITICAL)
**Location**: `extraction.py` lines 19-23

```python
def llm_extract(..., openai_api_key: str, ...):
    llm_extraction = ChatOpenAI(
        model="gpt-4o-mini",              # ❌ HARDCODED
        temperature=0.0,                   # ❌ HARDCODED
        openai_api_key=openai_api_key
    )
```

**Additional Locations**:
- `chatbot_core.py` line 15: `from langchain_openai import ChatOpenAI`
- `lambda_function.py` lines 180-183: OpenAI API key validation

**Issues**:
- Model name `gpt-4o-mini` is hardcoded
- Temperature is hardcoded (0.0)
- Only supports OpenAI via LangChain
- No support for Anthropic, Azure OpenAI, AWS Bedrock
- LangChain dependency ties to OpenAI-specific implementation

**Refactoring Required**:
1. Create LLM provider abstraction layer
2. Support multiple providers (OpenAI, Anthropic, Azure, Bedrock)
3. Make model and temperature configurable via environment variables
4. Remove LangChain dependency for provider-agnostic implementation
5. Example:
   ```python
   LLM_PROVIDER = "openai"  # or "anthropic", "azure", "bedrock"
   LLM_MODEL = "gpt-4o-mini"
   LLM_TEMPERATURE = 0.0
   ```

### 🔴 Storage Provider (CRITICAL)
**Locations**: 
- `s3_helper.py` (entire file - 733 lines)
- `lambda_function.py` line 10: `from s3_helper import S3Helper`
- `chatbot_core.py` line 178: `s3 = S3Helper()`

```python
# s3_helper.py
class S3Helper:
    def __init__(self, bucket_name=None, config_bucket=None):
        self.s3 = boto3.client('s3')                           # ❌ AWS S3-SPECIFIC
        self.bucket = bucket_name or os.environ.get('OUTPUT_BUCKET')
        self.config_bucket = config_bucket or os.environ.get('STATIC_BUCKET')
    
    def get_form_keys(self):
        response = self.s3.get_object(                         # ❌ S3-SPECIFIC
            Bucket=self.config_bucket,
            Key='form_keys.json'
        )
```

**Issues**:
- All storage operations assume AWS S3
- Uses boto3 client directly (AWS-specific)
- No support for Azure Blob Storage, Google Cloud Storage
- Environment variables `OUTPUT_BUCKET`, `STATIC_BUCKET` are S3-specific
- S3 URI patterns hardcoded throughout

**Refactoring Required**:
1. Create `StorageProvider` abstraction layer
2. Implement providers: S3, Azure Blob, GCS, local filesystem
3. Use provider-agnostic configuration
4. Example:
   ```python
   STORAGE_PROVIDER = "s3"  # or "azure_blob", "gcs", "local"
   OUTPUT_BUCKET = "my-bucket"
   STATIC_BUCKET = "config-bucket"
   
   # Abstract interface:
   storage.get_object(bucket, key)
   storage.put_object(bucket, key, data)
   ```

### 🔴 Backend API Dependency (CRITICAL)
**Location**: `chatbot_core.py` lines 1218-1500

```python
def _initialize_pdf_session(self, user_id, session_id, container_id, s3_bucket):
    # Step 1: Auth0 Authentication
    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')            # ❌ HARDCODED AUTH METHOD
    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
    AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE')
    BACKEND_URL = os.environ.get('BACKEND_URL')              # ❌ DIRECT COUPLING
    
    login_response = requests.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",               # ❌ HARDCODED AUTH0
        ...
    )
    
    # Step 2: Fetch PDF ID
    pdf_id_response = requests.get(
        f"{BACKEND_URL}/api/v1/chat/session/{session_id}/pdf-id",  # ❌ HARDCODED ENDPOINT
        headers={"Authorization": f"Bearer {access_token}"},
        ...
    )
```

**Issues**:
- Tightly coupled to specific backend API
- Auth0 authentication is hardcoded (no support for other auth providers)
- API endpoints are hardcoded (`/api/v1/chat/session/{session_id}/pdf-id`)
- No abstraction for different authentication methods (JWT, IAM, API key)
- Retry logic is hardcoded (10 attempts, 2s delay)

**Refactoring Required**:
1. Create backend client abstraction
2. Support multiple authentication methods (Auth0, JWT, API key, IAM)
3. Make endpoints configurable
4. Support different deployment scenarios (local, cloud)
5. Example:
   ```python
   AUTH_PROVIDER = "auth0"  # or "jwt", "api_key", "iam"
   BACKEND_CLIENT = "rest_api"  # or "lambda_invoke", "local"
   ```

### 🔴 Main Pipeline API Dependency (CRITICAL)
**Location**: Background thread execution in `chatbot_core.py`

```python
# Step 3: Trigger make_embed_file (background)
# Calls main pipeline Lambda API
# ❌ HARDCODED: Direct coupling to main pipeline operations
```

**Issues**:
- Tightly coupled to main pipeline Lambda
- Operations hardcoded: `make_embed_file`, `check_embed_file`, `fill_pdf`
- No abstraction for different pipeline implementations
- Background thread may not survive Lambda cold starts

**Refactoring Required**:
1. Create pipeline client abstraction
2. Support different invocation methods (Lambda, HTTP API, local)
3. Use Step Functions or SQS for asynchronous workflows
4. Make operations configurable

### 🟡 RDS Database Dependency (MEDIUM - Currently Disabled)
**Location**: `lambda_function.py` lines 11, 179

```python
from rds_helper import RDSHelper                              # ❌ IMPORT EXISTS
from chatbot_core import ChatbotCore, DummyRDS

# In handler:
rds = DummyRDS()                                              # ✅ CURRENTLY DISABLED
```

**Status**: 
- RDSHelper exists but is NOT used
- DummyRDS is used instead (no-op implementation)
- All `rds.log_event()` calls are no-ops

**Issues** (if re-enabled):
- Hardcoded to AWS RDS (PostgreSQL/MySQL)
- No support for other databases (DynamoDB, CosmosDB, MongoDB)
- No abstraction layer

**Refactoring Required** (if re-enabled):
1. Create database abstraction layer
2. Support multiple databases (RDS, DynamoDB, MongoDB, etc.)
3. Make database type configurable

### 🟡 State Machine Hardcoding (MEDIUM)
**Location**: `chatbot_core.py` lines 20-31

```python
class State:
    INIT = "init"
    SAVED_INFO_CHECK = "saved_info_check"
    INVESTOR_TYPE_SELECT = "investor_type_select"
    DATA_COLLECTION = "data_collection"
    CONTINUE_PROMPT = "continue_prompt"
    # ... 12 states total
```

**Issues**:
- States are hardcoded in code (not configurable)
- State transitions are embedded in logic
- Difficult to add new states or modify flow
- No visual representation of state machine

**Refactoring Required**:
1. Define state machine in configuration file (YAML/JSON)
2. Create generic state machine engine
3. Support dynamic state addition/removal
4. Generate state diagram from configuration

### 🟡 Investor Type Mapping (MEDIUM)
**Location**: `chatbot_core.py` lines 759-775

```python
keyword_mappings = {
    "Trade Booking": ["trade", "booking", "initial", "subs", "trade booking"],
    "Individual": ["individual", "person", "self"],
    "Partnership": ["partnership", "partner"],
    # ... hardcoded mappings
}
```

**Issues**:
- Investor types are hardcoded in code
- Keywords for fuzzy matching are hardcoded
- Difficult to add new investor types
- No localization support

**Refactoring Required**:
1. Move investor types to configuration file
2. Support multiple languages
3. Make keyword mappings configurable

## Configuration Files (S3-Stored)

### Required Files in STATIC_BUCKET
| File | Purpose | Structure |
|------|---------|-----------|
| `form_keys.json` | Form schema (nested) | Nested JSON object |
| `meta_form_keys.json` | Field metadata (types) | Nested JSON with field types |
| `mandatory.json` | Mandatory fields by investor type | `{"Type of Investors": {...}}` |
| `field_questions.json` | Custom questions for fields | Field path → question text |
| `form_keys_label.json` | Human-readable field labels | Field path → label |

## Performance Considerations

### Conversation Latency
- **LLM Extraction**: 2-5s per message (OpenAI API call)
- **Fallback Extraction**: <100ms (regex-based)
- **S3 Operations**: 50-200ms per save
- **Total per message**: 2-6s

### PDF Workflow Latency
- **Step 1 (Auth0)**: 500ms-2s
- **Step 2 (PDF ID)**: 500ms-2s
- **Step 3 (make_embed_file)**: Background (non-blocking)
- **Step 4 (Polling)**: Up to 8 minutes (48 × 10s)
- **Step 5 (Upload)**: 100-500ms
- **Step 6 (fill_pdf)**: 10-30s
- **Total**: 10-35s (excluding step 4 wait time)

### Retry Logic
- **Auth0 Authentication**: Max 10 attempts, 2s delay
- **PDF ID Fetch**: Max 10 attempts, 2s delay
- **Total max retry time**: 40s per step (20s × 2 steps)

## Error Handling

### Authentication Errors (401/403)
- Missing `X-API-Key` header
- Invalid API token
- Auth0 authentication failure

### Validation Errors (400)
- Missing `user_id` or `session_id`
- Invalid phone number format

### Configuration Errors (500)
- Missing `OPENAI_API_KEY`
- Missing Auth0 credentials
- Missing S3 bucket configuration

### External API Errors (500)
- Backend API timeout
- PDF ID fetch failure
- Main pipeline API failure

## Dependencies

### Python Packages (requirements.txt)
```
langchain-openai     # OpenAI integration via LangChain
openai              # OpenAI API client
boto3               # AWS S3 operations
requests            # HTTP API calls
fuzzywuzzy          # Fuzzy string matching (investor types)
aiohttp             # Async HTTP (notifications)
```

## Integration Points

### Upstream Dependencies
- **S3**: Configuration files (`form_keys.json`, `meta_form_keys.json`, `mandatory.json`)
- **S3**: Session state storage
- **OpenAI API**: Field extraction
- **Auth0**: Authentication for backend API

### Downstream Dependencies
- **Backend API**: PDF session management (`/api/v1/chat/session/{session_id}/pdf-id`)
- **Main Pipeline Lambda**: `make_embed_file`, `check_embed_file`, `fill_pdf` operations
- **S3**: Output storage (live_fill.json, combined_input.json)

## Known Limitations

1. **OpenAI Dependency**: Cannot switch to other LLM providers without code changes
2. **S3 Dependency**: Cannot use Azure Blob or GCS without rewriting storage layer
3. **Backend Coupling**: Tightly coupled to specific backend API and Auth0
4. **State Machine Rigidity**: Cannot modify conversation flow without code changes
5. **Single User Per Conversation**: No support for multi-user collaboration
6. **No Conversation Recovery**: If Lambda times out during PDF workflow, manual intervention required
7. **English Only**: No localization support for other languages
8. **Sequential Processing**: Cannot handle multiple concurrent messages per session
9. **Long-Running Workflows**: PDF polling can timeout (15-minute Lambda limit)
10. **No Undo/Redo**: Users cannot correct previous answers easily

## Refactoring Roadmap

### Phase 1: Configuration Externalization
- Move all hardcoded values to environment variables
- Create configuration schema
- Add validation layer

### Phase 2: LLM Provider Abstraction
- Create `LLMProvider` interface
- Implement OpenAI, Anthropic, Azure OpenAI providers
- Remove LangChain dependency
- Make provider configurable via environment variable

### Phase 3: Storage Provider Abstraction
- Create `StorageProvider` interface
- Implement S3, Azure Blob, GCS providers
- Unify configuration across providers

### Phase 4: Backend Client Abstraction
- Create backend client interface
- Support multiple authentication methods (Auth0, JWT, API key)
- Make endpoints configurable
- Add circuit breaker for resilience

### Phase 5: State Machine Externalization
- Define state machine in YAML/JSON
- Create generic state machine engine
- Support dynamic state modifications
- Generate documentation from configuration

### Phase 6: Async Workflow Orchestration
- Replace background threads with Step Functions or SQS
- Implement resumable workflows
- Add dead-letter queues for failures
- Support long-running operations beyond Lambda timeout

### Phase 7: Monitoring & Observability
- Add distributed tracing (X-Ray)
- Implement structured logging
- Add custom CloudWatch metrics
- Create dashboards for conversation analytics

## Related Modules

### Main Pipeline (`src/`)
- Provides: `make_embed_file`, `check_embed_file`, `fill_pdf` operations
- Dependency: This module calls main pipeline APIs

### pdf_upload_lambda (Previously Documented)
- Purpose: Process uploaded PDFs
- Integration: Both modules call main pipeline operations

### rag_lambda (To Be Documented)
- Purpose: TBD
- Integration: TBD

## Debug Logging

### Debug Log Structure
The module includes comprehensive debug logging (`DebugLogger` class):

**Categories**:
- `initialization`: Module startup, session creation
- `extraction`: LLM/fallback extraction operations
- `validation`: Phone number, field validation
- `state_machine`: State transitions, handler execution
- `file_operation`: S3 read/write operations
- `background_task`: PDF workflow steps

**Log Entry**:
```json
{
  "entry_id": 1,
  "timestamp": "2026-03-02T10:30:45.123Z",
  "category": "extraction",
  "level": "info",
  "message": "Extraction completed using llm",
  "data": {
    "method": "llm",
    "fields_extracted": 15,
    "latency_seconds": 2.456
  }
}
```

**Storage**: `{user_id}/sessions/{session_id}/debug_conversation.json`

---

**Last Updated**: 2026-03-02
**Version**: 1.0.0
**Maintainer**: Development Team
