# PDF Mapper Module

Core engine for AI-powered PDF form field extraction, semantic mapping, embedding, and filling.

---

## Module structure

```
modules/mapper/
├── src/                        # Server-side business logic
│   ├── core/                   # Config, logger
│   ├── handlers/               # Operation handlers (extract, map, embed, fill)
│   ├── extractors/             # PDF field extraction (PyMuPDF)
│   ├── mappers/                # LLM semantic mapper
│   ├── embedders/              # Java embed stage
│   ├── fillers/                # Java fill stage
│   ├── configs/                # Storage configs (local, AWS, Azure, GCP, SDK)
│   ├── storage/                # Storage backends + job context + path resolver
│   ├── clients/                # LLM client, S3 client, auth client
│   ├── utils/                  # Helpers (hash cache, jar path, ini loader, …)
│   ├── prompts/                # LLM prompt templates
│   ├── headers/                # Headers/RAG second-mapper pipeline
│   ├── chunkers/               # Text chunking strategies
│   ├── groupers/               # Field grouping logic
│   ├── models/                 # Shared data models
│   ├── validators/             # Embed validator
│   ├── java_utils/             # Java source (Maven project)
│   └── assets/                 # Compiled JARs (filler, rebuilder, refresher)
│
├── adapters/                   # Optional integrations (pipeline notifier)
│   ├── notifier.py
│   └── clients/
│
├── entrypoints/                # Platform-specific entry points
│   ├── local.py                # Local / direct Python
│   ├── http_server.py          # FastAPI HTTP server
│   ├── aws_lambda.py           # AWS Lambda handler
│   ├── azure_function.py       # Azure Function handler
│   └── gcp_function.py         # GCP Cloud Function handler
│
├── sdk/                        # Python SDK (pip install pdf-autofiller-mapper)
│   ├── pdf_autofiller_mapper/  # Package source
│   ├── tests/                  # SDK tests (105 tests)
│   ├── examples/
│   ├── pyproject.toml
│   └── README.md
│
├── tests/                      # Module-level tests
│
├── deployment/                 # All deployment configuration
│   └── docker/
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── docker-build.sh
│       ├── docker-run-local.sh
│       └── docker-test.sh
│
├── docs/                       # Documentation
│   ├── api_server.md
│   ├── architecture.md
│   ├── deployment.md
│   ├── docker.md
│   ├── docker_local_usage.md
│   ├── http_server.md
│   └── setup_guide.md
│
├── api_server.py               # FastAPI application entry point
├── config.ini                  # Active configuration (gitignored — copy from example)
├── config.ini.example          # Configuration template
├── .env                        # Runtime secrets (gitignored — copy from .env.example)
├── .env.example                # Environment variable template
├── requirements.txt            # All dependencies
└── pyproject.toml              # Module package metadata
```

---

## Quick start

### 1. Configure

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or another LLM key) and storage paths
```

### 2. Run locally

```bash
cd modules/mapper
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python api_server.py
# → http://localhost:8000
```

### 3. Run with Docker

```bash
cd modules/mapper/deployment/docker
./docker-build.sh
./docker-run-local.sh
# API available at http://localhost:8000
```

### 4. Use the Python SDK

```bash
pip install pdf-autofiller-mapper
```

```python
from pdf_autofiller_mapper import PDFMapperClient

with PDFMapperClient("http://localhost:8000") as client:
    result = client.mapper.make_embed_file(
        user_id="1", session_id="1", pdf_doc_id="100"
    )
```

See `sdk/README.md` for the full SDK guide.

---

## Two-phase workflow

| Phase | Run once | Input files needed | What it does |
|---|---|---|---|
| **make_embed_file** | Per PDF template | `input.pdf`, `global_schema.json` | extract → map → embed |
| **fill** | Per user submission | `input_data.json` | fill embedded PDF with user data |

**`global_schema.json`** — keys-only schema (all values empty):
```json
{"firstName": "", "lastName": "", "dateOfBirth": "", "email": ""}
```

**`input_data.json`** — actual user data:
```json
{"firstName": "Jane", "lastName": "Doe", "dateOfBirth": "1990-05-14", "email": "jane@example.com"}
```

---

## Storage layout

All input files must be placed at the paths determined by `MAPPER_*` env vars before calling any endpoint.

```
{MAPPER_INPUT_PATH}/
└── {user_id}/
    └── {session_id}/
        └── {pdf_doc_id}/
            ├── input.pdf              ← original PDF template
            ├── global_schema.json     ← keys-only schema  (needed by make_embed_file)
            └── input_data.json        ← user fill data    (needed by fill)

{MAPPER_OUTPUT_PATH}/
└── {user_id}/
    └── {session_id}/
        └── {pdf_doc_id}/
            ├── extracted.json
            ├── mapping.json
            ├── embedded.pdf           ← produced by make_embed_file
            └── filled.pdf             ← produced by fill
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/upload/{user_id}/{session_id}/{pdf_doc_id}/{filename}` | **Upload** input file (multipart) |
| POST | `/mapper/make-embed-file` | **Extract + Map + Embed** — main prep step |
| POST | `/mapper/fill` | **Fill** embedded PDF with user data |
| GET | `/download?path=<path>` | **Download** any output file (local or cloud URI) |
| POST | `/mapper/check-embed-file` | Check whether embedded PDF is ready |
| POST | `/mapper/fill-pdf` | Alias for `/mapper/fill` |
| POST | `/mapper/run-all` | Full pipeline (extract → map → embed → fill) |
| POST | `/mapper/extract` | Extract form fields only |
| POST | `/mapper/map` | LLM semantic mapping only |
| POST | `/mapper/embed` | Embed field metadata only |

---

## Four key endpoints

### 1. `POST /upload/{user_id}/{session_id}/{pdf_doc_id}/{filename}`

Upload input files before calling any processing endpoint.
The server stores the file at `{MAPPER_INPUT_PATH}/{user_id}/{session_id}/{pdf_doc_id}/{filename}`.

**Accepted filenames**

| Filename | Used by |
|---|---|
| `input.pdf` | `make_embed_file`, `run_all` |
| `global_schema.json` | `make_embed_file`, `run_all` |
| `input_data.json` | `fill`, `run_all` |

**Request** — multipart/form-data
```bash
# Upload the PDF template
curl -X POST \
  "http://localhost:8000/upload/1/1/100/input.pdf" \
  -F "file=@/local/path/application.pdf"

# Upload the keys-only schema
curl -X POST \
  "http://localhost:8000/upload/1/1/100/global_schema.json" \
  -F "file=@/local/path/schema_keys.json"

# Upload per-user fill data
curl -X POST \
  "http://localhost:8000/upload/1/1/100/input_data.json" \
  -F "file=@/local/path/jane_doe.json"
```

**Response — success**
```json
{
  "status": "success",
  "path": "/app/data/input/1/1/100/input.pdf",
  "user_id": "1",
  "session_id": "1",
  "pdf_doc_id": "100",
  "filename": "input.pdf",
  "size_bytes": 204800
}
```

**Response — invalid filename (400)**
```json
{
  "detail": "Filename 'form.pdf' is not allowed. Must be one of: ['global_schema.json', 'input.pdf', 'input_data.json']"
}
```

---

### 2. `POST /mapper/make-embed-file`

Runs the full prepare pipeline — **extract → map → embed** — in a single call.
Call this once per unique PDF template. The output embedded PDF can be reused for every user.

**Request**
```json
{
  "user_id": "1",
  "session_id": "1",
  "pdf_doc_id": "100",
  "investor_type": "individual",
  "use_second_mapper": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | string | yes | User identifier |
| `session_id` | string | yes | Session identifier |
| `pdf_doc_id` | string | yes | PDF document identifier |
| `investor_type` | string | no | `"individual"` (default) or `"entity"` |
| `use_second_mapper` | bool | no | Enable RAG second-mapper for higher accuracy (default: `false`) |

**Response — success**
```json
{
  "status": "success",
  "output_paths": {
    "embedded_pdf": "/app/data/output/1/1/100/embedded.pdf",
    "extracted_json": "/app/data/output/1/1/100/extracted.json",
    "mapping_json": "/app/data/output/1/1/100/mapping.json"
  },
  "execution_time": 14.3,
  "mapped_fields": 12,
  "total_fields": 14,
  "confidence": 0.91
}
```

**Response — missing input files (400)**
```json
{
  "detail": {
    "missing_files": [
      "input_pdf not found: /app/data/input/1/1/100/input.pdf",
      "global_json not found: /app/data/input/1/1/100/global_schema.json"
    ]
  }
}
```

---

### 3. `POST /mapper/fill`

Fills a previously embedded PDF with per-user data.
The embedded PDF must have been produced by `/mapper/make-embed-file` first,
and `input_data.json` must be at the configured input path.

**Request**
```json
{
  "user_id": "1",
  "session_id": "1",
  "pdf_doc_id": "100"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | string | yes | User identifier |
| `session_id` | string | yes | Session identifier |
| `pdf_doc_id` | string | yes | PDF document identifier |

**Response — success**
```json
{
  "status": "success",
  "output_paths": {
    "filled_pdf": "/app/data/output/1/1/100/filled.pdf"
  },
  "execution_time": 2.1
}
```

**Response — embedded PDF not ready (400)**
```json
{
  "detail": {
    "missing_files": [
      "embedded_pdf not found: /app/data/output/1/1/100/embedded.pdf"
    ]
  }
}
```

---

### 4. `GET /download?path=<path>`

Downloads any output file (PDF, JSON) generated by the mapper.
Works for local filesystem paths and all cloud storage backends.
The `path` value is the exact string returned in `output_paths` by any processing endpoint.

**Request**
```bash
# Local storage
GET /download?path=/app/data/output/1/1/100/filled.pdf

# AWS S3
GET /download?path=s3://my-bucket/prefix/output/1/1/100/filled.pdf

# Azure Blob
GET /download?path=azure://my-container/prefix/output/1/1/100/filled.pdf

# GCP Cloud Storage
GET /download?path=gs://my-bucket/prefix/output/1/1/100/filled.pdf
```

**Response**

Returns the raw file as `application/octet-stream` with `Content-Disposition: attachment`.

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="filled.pdf"

<binary file content>
```

**Error — file not found (404)**
```json
{"detail": "File not found: s3://my-bucket/prefix/output/1/1/100/filled.pdf"}
```

---

## Typical request sequence

```
1. POST /upload/1/1/100/input.pdf           ← upload PDF template
2. POST /upload/1/1/100/global_schema.json  ← upload keys-only schema

3. POST /mapper/make-embed-file  {"user_id":"1","session_id":"1","pdf_doc_id":"100"}
   → returns output_paths.embedded_pdf  (reusable for all users)

4. POST /upload/1/1/100/input_data.json     ← upload per-user fill data

5. POST /mapper/fill  {"user_id":"1","session_id":"1","pdf_doc_id":"100"}
   → returns output_paths.filled_pdf

6. GET /download?path=<filled_pdf_path>     ← download completed PDF
```

---

## Health check

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

---

## Tests

```bash
# Module tests
venv/bin/python -m pytest tests/ --override-ini="addopts=" -q

# SDK tests
cd sdk && python -m pytest tests/ -q
# 105 passed
```

---

## Configuration reference

See `.env.example` for all available environment variables.
See `config.ini.example` for operational settings (LLM model, mapping thresholds, etc.)
See `docs/setup_guide.md` for a full walkthrough.
