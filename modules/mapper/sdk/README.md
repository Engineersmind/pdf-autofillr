# PDF Autofiller Python SDK — Developer Guide

The SDK ships two ways to talk to the mapper:

| Mode | Class | When to use |
|------|-------|-------------|
| **Embedded** | `PDFMapper` | Run directly inside your Python process — no server needed |
| **HTTP client** | `PDFMapperClient` | Talk to a running mapper Docker container / HTTP server |

---

## Installation

```bash
# HTTP client only (lightweight — no mapper deps required)
pip install pdf-autofiller-sdk

# Embedded SDK (installs mapper module and all ML dependencies)
pip install pdf-autofiller-sdk[embedded]
```

---

## Two-phase workflow

Understanding which JSON file goes to which phase is important:

| Phase | When | Input JSON | What it contains |
|-------|------|-----------|-----------------|
| **Embed** (extract → map → embed) | Once per PDF template | `global_json` | Keys-only schema — all values empty: `{"firstName": "", "lastName": ""}` |
| **Fill** | Once per user | `input_json` | Actual user data: `{"firstName": "Jane", "lastName": "Doe"}` |

The embed phase produces an *embedded PDF* that can be reused for thousands of users. Only the fill phase needs to run again for each new user.

---

## Embedded SDK (`PDFMapper`)

### Import

```python
from pdf_autofiller_mapper import PDFMapper
from pdf_autofiller.exceptions import PDFMapperError, ConfigurationError
```

### Constructor

```python
PDFMapper(
    config_path=None,           # Path to config.ini (recommended)
    *,
    llm_model=None,             # Override config.ini [mapping] llm_model
    headers_llm_model=None,     # Override [headers] headers_llm_model
    confidence_threshold=None,  # Override [mapping] confidence_threshold (0–1)
    use_second_mapper=None,     # Enable dual-mapper RAG pipeline
    output_dir=None,            # Where to write intermediate files
    cleanup=False,              # False | True | "on_success" | "on_error"
)
```

At least one of `config_path`, `llm_model`, or the `PDF_AUTOFILLER_CONFIG` environment variable must be set.

### Supported LLM models

```ini
# config.ini [mapping] section
llm_model = gpt-4o                                         # OpenAI
llm_model = gpt-4o-mini
llm_model = claude-3-5-sonnet-20241022                    # Anthropic
llm_model = bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0  # AWS Bedrock
llm_model = azure/gpt-4                                   # Azure OpenAI
llm_model = vertex_ai/gemini-pro                          # Google Vertex AI
llm_model = ollama/qwen2.5:14b                            # Ollama (local, free)
llm_model = ollama/llama3.1:8b
```

Credentials are read from environment variables — never passed to the constructor:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export AZURE_API_KEY=...  AZURE_API_BASE=...  AZURE_API_VERSION=...
export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_REGION_NAME=us-east-1
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
export OLLAMA_API_BASE=http://localhost:11434   # default
```

---

### `make_embed_file(pdf_path, global_json_path)` → SDKResult

Runs extract → map → embed. Call this **once per PDF template**.

```python
mapper = PDFMapper(config_path="config.ini")

result = mapper.make_embed_file(
    pdf_path="forms/application.pdf",
    global_json_path="schemas/application_keys.json",  # {"firstName": "", ...}
)

if result.ok:
    print(f"Embedded PDF: {result.embedded_pdf}")
    print(f"Mapped {result.mapped_fields} fields in {result.execution_time:.1f}s")
else:
    print(f"Failed: {result.error}")
```

`application_keys.json` — keys-only schema:
```json
{"firstName": "", "lastName": "", "dateOfBirth": "", "email": "", "phone": ""}
```

---

### `fill(embedded_pdf_path, input_json_path)` → SDKResult

Fills a previously embedded PDF with per-user data.

```python
result = mapper.fill(
    pdf_path="forms/application_embedded.pdf",   # output of make_embed_file
    input_json_path="users/jane_doe.json",        # {"firstName": "Jane", ...}
)

if result.ok:
    result.save("output/jane_filled.pdf")
```

`jane_doe.json` — actual user data:
```json
{"firstName": "Jane", "lastName": "Doe", "dateOfBirth": "1990-05-14", "email": "jane@example.com"}
```

---

### `process(pdf_path, global_json_path, input_json_path)` → SDKResult

Convenience method — runs the complete pipeline (extract → map → embed → fill) in one call. Useful for one-off conversions or testing.

```python
result = mapper.process(
    pdf_path="forms/application.pdf",
    global_json_path="schemas/application_keys.json",
    input_json_path="users/jane_doe.json",
)

if result.ok:
    result.save("output/jane_filled.pdf")
    print(result)   # SDKResult(status=success, fields=12/14, confidence=91%, time=18.4s)
```

---

### Individual stage methods

Run a single stage when you need fine-grained control:

```python
# Stage 1 — extract form fields from the PDF
r = mapper.extract("forms/application.pdf", "schemas/keys.json")
print(r.stages["extract"].output_file)   # path to extracted JSON

# Stage 2 — LLM semantic mapping
r = mapper.map("forms/application.pdf", "schemas/keys.json")

# Stage 3 — write field metadata into PDF (requires Java)
r = mapper.embed("forms/application.pdf", "schemas/keys.json")
```

---

### SDKResult

Every method returns an `SDKResult`:

```python
result.ok               # bool — True on success
result.status           # "success" | "error"
result.error            # error message string (when not ok)
result.embedded_pdf     # path to embedded PDF (make_embed_file / process)
result.filled_pdf       # path to filled PDF (fill / process)
result.mapping          # {"1": "firstName", "2": "lastName", ...}
result.confidence       # float 0–1, average mapping confidence
result.total_fields     # int — total form fields found
result.mapped_fields    # int — fields mapped above threshold
result.execution_time   # float — total seconds
result.stages           # dict of StageResult per stage

# Copy filled PDF to a destination
result.save("output/filled.pdf")   # raises ValueError if not ok
```

Per-stage access:

```python
map_stage = result.stages.get("map")
if map_stage:
    print(f"Map stage: {map_stage.status}, took {map_stage.execution_time:.1f}s")
    print(f"Output: {map_stage.output_file}")
```

---

### Cleanup modes

```python
# Keep all files (default)
mapper = PDFMapper(config_path="config.ini", cleanup=False)

# Always delete output_dir after each operation
mapper = PDFMapper(config_path="config.ini", cleanup=True)

# Delete only when successful (keep files on error for debugging)
mapper = PDFMapper(config_path="config.ini", cleanup="on_success")

# Delete only on failure (keep successful outputs, clean up failed runs)
mapper = PDFMapper(config_path="config.ini", cleanup="on_error")
```

### Context manager — guaranteed cleanup

```python
with PDFMapper(config_path="config.ini", cleanup=True) as mapper:
    result = mapper.process(
        "forms/application.pdf",
        "schemas/keys.json",
        "users/jane.json",
    )
    if result.ok:
        result.save("output/jane_filled.pdf")
# All temp files deleted here regardless of success/failure
```

---

### Common patterns

**Override model without editing config.ini:**
```python
mapper = PDFMapper(
    config_path="config.ini",
    llm_model="bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
    confidence_threshold=0.85,
)
```

**No config.ini — pass everything directly:**
```python
mapper = PDFMapper(llm_model="gpt-4o", confidence_threshold=0.7)
```

**Batch fill — embed once, fill many times:**
```python
mapper = PDFMapper(config_path="config.ini")

# Step 1 — embed template once
embed_result = mapper.make_embed_file("forms/application.pdf", "schemas/keys.json")
assert embed_result.ok
embedded_pdf = embed_result.embedded_pdf

# Step 2 — fill for each user
users = [
    ("users/jane.json", "output/jane_filled.pdf"),
    ("users/john.json", "output/john_filled.pdf"),
]
for data_file, out_file in users:
    r = mapper.fill(embedded_pdf, data_file)
    if r.ok:
        r.save(out_file)
    else:
        print(f"Failed {data_file}: {r.error}")
```

**Enable dual-mapper (semantic + RAG) for higher accuracy:**
```python
mapper = PDFMapper(
    config_path="config.ini",
    use_second_mapper=True,
    headers_llm_model="gpt-4o-mini",   # cheaper second model
)
```

---

### Exception handling

```python
from pdf_autofiller.exceptions import (
    PDFMapperError,      # base — catches everything
    ConfigurationError,  # missing config / files
    ExtractionError,     # PDF read failed
    MappingError,        # LLM mapping failed
    EmbeddingError,      # Java embed stage failed
    FillingError,        # Java fill stage failed
)

try:
    result = mapper.process("form.pdf", "schema.json", "user.json")
except ConfigurationError as e:
    print(f"Check your config.ini or file paths: {e}")
except MappingError as e:
    print(f"LLM mapping failed — try a different model: {e}")
except PDFMapperError as e:
    print(f"SDK error: {e}")
```

---

## HTTP Client (`PDFMapperClient`)

Use this when the mapper runs as a separate Docker service / HTTP server.

### Import

```python
from pdf_autofiller_mapper import PDFMapperClient
from pdf_autofiller.exceptions import APIError, ConnectionError, TimeoutError
```

### Constructor

```python
PDFMapperClient(
    base_url="http://localhost:8000",  # mapper server URL
    api_key=None,                       # sent as X-API-Key header
    timeout=300.0,                      # seconds (LLM calls can take 30–120s)
)
```

### Health check

```python
with PDFMapperClient(base_url="http://localhost:8000") as client:
    health = client.health_check()
    print(health)   # {"status": "ok"}
```

### Operations

All methods are on `client.mapper` and return a plain `dict` (the server's JSON response).

#### `make_embed_file` — extract + map + embed

```python
with PDFMapperClient("http://localhost:8000") as client:
    result = client.mapper.make_embed_file(
        pdf_path="s3://my-bucket/forms/application.pdf",
        session_id="session-abc123",   # optional
    )
    print(result)   # {"status": "success", "outputs": {"embedded_pdf": ...}, ...}
```

#### `fill` — fill with per-user data

```python
result = client.mapper.fill(
    pdf_path="s3://my-bucket/forms/application_embedded.pdf",
    data={"firstName": "Jane", "lastName": "Doe"},
    session_id="session-abc123",
)
```

#### `extract`, `map`, `embed` — individual stages

```python
# Extract only
result = client.mapper.extract(pdf_path="s3://bucket/form.pdf")

# Map only
result = client.mapper.map(
    pdf_path="s3://bucket/form.pdf",
    mapper_type="ensemble",   # "semantic" | "rag" | "headers" | "ensemble"
)

# Embed only
result = client.mapper.embed(pdf_path="s3://bucket/form.pdf")
```

#### `check_embed_file` — verify embedded metadata exists

```python
result = client.mapper.check_embed_file(pdf_path="s3://bucket/form.pdf")
if result["data"]["has_metadata"]:
    print("Ready to fill")
```

#### `run_all` — complete pipeline in one request

```python
result = client.mapper.run_all(pdf_path="s3://bucket/form.pdf")
```

### Error handling

```python
from pdf_autofiller.exceptions import APIError, ConnectionError, TimeoutError

try:
    result = client.mapper.make_embed_file(pdf_path="s3://bucket/form.pdf")
except ConnectionError:
    print("Server is not running or unreachable")
except TimeoutError:
    print("LLM call timed out — increase timeout= on PDFMapperClient")
except APIError as e:
    print(f"Server error {e.status_code}: {e.response_body}")
```

---

## CLI (`pdf-autofiller`)

Requires the SDK package installed with Rich available.

```bash
pip install pdf-autofiller-sdk
```

```bash
# Health / connectivity
pdf-autofiller --api-url http://localhost:8000 check-embed form.pdf

# Prepare a template (extract + map + embed)
pdf-autofiller make-embed form.pdf --use-rag -o embedded.pdf

# Fill a prepared template
pdf-autofiller fill embedded.pdf user_data.json -o filled.pdf

# Full pipeline in one shot
pdf-autofiller run-all form.pdf user_data.json -o filled.pdf

# Individual stages
pdf-autofiller extract form.pdf -o extracted.json
pdf-autofiller map form.pdf schema.json --mapper-type semantic
pdf-autofiller embed form.pdf mapping.json

# Use a remote server
pdf-autofiller --api-url http://my-server:8000 --api-key secret make-embed form.pdf
```

---

## Running the tests

### SDK unit tests (no mapper module or Java required)

```bash
cd modules/mapper/sdk
pip install -e ".[dev]"
pytest tests/ -v
# 101 passed
```

### Mapper module tests (requires venv with all deps)

```bash
cd modules/mapper
venv/bin/python -m pytest tests/ --override-ini="addopts=" -q
# 162 passed
```
