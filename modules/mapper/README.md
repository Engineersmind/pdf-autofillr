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
│   ├── tests/                  # SDK tests (101 tests)
│   ├── examples/
│   ├── pyproject.toml
│   └── README.md
│
├── tests/                      # Module-level tests (169 tests)
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
├── requirements.txt            # All dependencies (core + API server + cloud SDKs)
└── pyproject.toml              # Module package metadata
```

---

## Quick start

### 1. Configure

```bash
cp config.ini.example config.ini
# Edit config.ini: set llm_model, storage paths, API keys
```

Set your LLM API key in the environment:
```bash
export OPENAI_API_KEY=sk-...          # OpenAI
export ANTHROPIC_API_KEY=sk-ant-...   # Anthropic
# or use Ollama (free, local): llm_model = ollama/llama3.1 in config.ini
```

### 2. Install and run locally

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
```

### 4. Use the Python SDK

```bash
pip install pdf-autofiller-mapper          # HTTP client only
pip install pdf-autofiller-mapper[embedded] # + in-process pipeline
```

```python
# Embedded (in-process)
from pdf_autofiller_mapper import PDFMapper

mapper = PDFMapper(config_path="config.ini")
result = mapper.make_embed_file("form.pdf", "schema_keys.json")
result.save("form_embedded.pdf")

# HTTP client
from pdf_autofiller_mapper import PDFMapperClient

with PDFMapperClient("http://localhost:8000") as client:
    result = client.mapper.make_embed_file(pdf_path="s3://bucket/form.pdf")
```

See `sdk/README.md` for the full SDK guide.

---

## Two-phase workflow

| Phase | Run | Input JSON | What it does |
|---|---|---|---|
| **make_embed_file** | Once per PDF template | `global_json` — keys-only schema: `{"firstName": ""}` | extract → map → embed |
| **fill** | Once per user | `input_json` — actual data: `{"firstName": "Jane"}` | fill |

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/extract` | Extract form fields from PDF |
| POST | `/map` | LLM semantic mapping |
| POST | `/embed` | Embed field metadata into PDF |
| POST | `/fill` | Fill embedded PDF with user data |
| POST | `/make-embed-file` | extract + map + embed in one call |
| POST | `/fill-pdf` | Alias for fill |
| POST | `/run-all` | Full pipeline |
| POST | `/check-embed-file` | Check if PDF has embedded metadata |

---

## Tests

```bash
# Module tests
venv/bin/python -m pytest tests/ --override-ini="addopts=" -q
# 169 passed

# SDK tests
cd sdk && venv/bin/python -m pytest tests/ -q
# 101 passed
```

---

## Configuration reference

See `config.ini.example` for all available settings.
See `docs/setup_guide.md` for a walkthrough.
