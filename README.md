# PDF Autofillr

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Mapper Tests](https://github.com/EngineersMind/pdf-autofillr/actions/workflows/mapper-tests.yml/badge.svg?event=pull_request)](https://github.com/EngineersMind/pdf-autofillr/actions/workflows/mapper-tests.yml)
[![Platform](https://img.shields.io/badge/platform-pdffillr.ai-blue)](https://pdffillr.ai)

> **Live platform:** [pdffillr.ai](https://pdffillr.ai) — fill PDF forms in your browser with no setup.

AI-powered PDF form filling system. Extracts fields from PDF forms, maps them to your data schema using an LLM, and fills them automatically.

---

## How it works

```
PDF template + schema keys
         │
         ▼
   make_embed_file          ← run once per PDF template
   (extract → map → embed)
         │
         ▼
   Embedded PDF             ← reusable template with metadata baked in
         │
         ▼
   fill(input_json)         ← run once per user
         │
         ▼
   Filled PDF
```

---

## Project structure

```
pdf-autofillr/
├── modules/
│   ├── mapper/             # Core engine (production-ready)
│   │   ├── src/            # Server-side business logic
│   │   ├── sdk/            # Python SDK (pip install pdf-autofiller-mapper)
│   │   ├── entrypoints/    # local, HTTP server, Lambda, Azure, GCP
│   │   ├── deployment/     # Docker
│   │   ├── docs/           # Module-level docs
│   │   ├── tests/          # 169 tests
│   │   ├── api_server.py   # FastAPI entry point
│   │   └── README.md       # Module guide
│   │
│   └── chatbot/            # Conversational data collection (separate service)
│
├── sdks/
│   ├── openapi-mapper.yaml         # OpenAPI spec for mapper
│   ├── openapi-chatbot.yaml
│   ├── openapi-rag.yaml
│   ├── openapi-upload.yaml
│   └── typescript/                 # TypeScript HTTP client
│
├── docs/
│   ├── architecture/               # System design docs
│   ├── guides/                     # Per-module guides
│   └── MIGRATION_SDK_INTO_MODULES.md
│
├── benchmarks/                     # Model evaluation — datasets, tasks, metrics, leaderboard
│   ├── datasets/                   # PDF categories (financial, medical, legal, …)
│   ├── tasks/                      # field_extraction, field_mapping, form_filling
│   ├── metrics/                    # Scoring functions
│   ├── models/                     # Model config cards (gpt-4o, claude, llama, …)
│   ├── results/                    # Benchmark run outputs + leaderboard
│   └── run_benchmark.py            # Entry point
│
├── data/                           # Shared sample PDFs and JSON fixtures
├── examples/                       # Usage examples (HTTP API, direct SDK)
├── Makefile                        # Common commands
├── setup.sh / setup.ps1            # One-time project setup
└── start.sh / stop.sh              # Server lifecycle
```

---

## Quick start

### Option 1 — Automated setup

```bash
./setup.sh                        # Mac / Linux
# or
pwsh -File setup.ps1              # Windows
```

### Option 2 — Manual setup

```bash
cd modules/mapper
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config.ini.example config.ini
# set llm_model and API keys in config.ini
python api_server.py
# → http://localhost:8000
```

### Option 3 — Docker

```bash
cd modules/mapper/deployment/docker
./docker-build.sh
./docker-run-local.sh
```

Set your LLM key before starting:

```bash
export OPENAI_API_KEY=sk-...          # OpenAI
export ANTHROPIC_API_KEY=sk-ant-...   # Anthropic
# or use Ollama (free, local): set llm_model = ollama/llama3.1 in config.ini
```

---

## Python SDK

```bash
pip install pdf-autofiller-mapper           # HTTP client only
pip install pdf-autofiller-mapper[embedded] # + in-process pipeline
```

```python
# Embedded (in-process, no server needed)
from pdf_autofiller_mapper import PDFMapper

mapper = PDFMapper(config_path="config.ini")
result = mapper.make_embed_file("form.pdf", "schema_keys.json")
result.save("form_embedded.pdf")

filled = mapper.fill("form_embedded.pdf", {"firstName": "Jane", "lastName": "Doe"})
filled.save("filled.pdf")
```

```python
# HTTP client (talks to running server / Docker container)
from pdf_autofiller_mapper import PDFMapperClient

with PDFMapperClient("http://localhost:8000") as client:
    result = client.mapper.make_embed_file(pdf_path="s3://bucket/form.pdf")
```

Full SDK guide: [`modules/mapper/sdk/README.md`](modules/mapper/sdk/README.md)

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/extract` | Extract form fields from PDF |
| POST | `/map` | LLM semantic mapping |
| POST | `/embed` | Embed field metadata into PDF |
| POST | `/fill` | Fill embedded PDF with user data |
| POST | `/make-embed-file` | extract + map + embed in one call |
| POST | `/fill-pdf` | Alias for fill |
| POST | `/run-all` | Full pipeline (make-embed + fill) |
| POST | `/check-embed-file` | Check if PDF has embedded metadata |

Full API reference: [`modules/mapper/docs/api_server.md`](modules/mapper/docs/api_server.md)

---

## Makefile commands

```bash
make setup          # Full automated setup
make start          # Start the API server
make dev            # Start with auto-reload
make stop           # Stop the server
make health         # curl /health
make test           # Run all tests (169 tests)
make install        # Install Python dependencies
make install-sdk    # Install mapper Python SDK
make docker-build   # Build Docker image
make docker-run     # Run Docker container
```

---

## Configuration

Edit `modules/mapper/config.ini` (copied from `config.ini.example`):

```ini
[general]
llm_model = gpt-4o-mini       # or anthropic/claude-3-5-haiku, ollama/llama3.1
source_type = local            # local | aws | azure | gcp

[local]
workspace = /path/to/data
```

Full configuration reference: [`modules/mapper/docs/setup_guide.md`](modules/mapper/docs/setup_guide.md)

---

## Tests

```bash
# Mapper module tests
cd modules/mapper
venv/bin/python -m pytest tests/ --override-ini="addopts=" -q
# 169 passed

# SDK tests
cd modules/mapper/sdk
venv/bin/python -m pytest tests/ -q
# 101 passed
```

---

## Documentation

| Topic | Link |
|-------|------|
| Mapper module | [`modules/mapper/README.md`](modules/mapper/README.md) |
| SDK guide | [`modules/mapper/sdk/README.md`](modules/mapper/sdk/README.md) |
| API server | [`modules/mapper/docs/api_server.md`](modules/mapper/docs/api_server.md) |
| Setup guide | [`modules/mapper/docs/setup_guide.md`](modules/mapper/docs/setup_guide.md) |
| Docker | [`modules/mapper/docs/docker.md`](modules/mapper/docs/docker.md) |
| Architecture | [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md) |
| Module guides | [`docs/guides/`](docs/guides/) |
| OpenAPI specs | [`sdks/`](sdks/) |
| Benchmarks | [`benchmarks/README.md`](benchmarks/README.md) |

---

## Contributing

Contributions are welcome! Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

- Report bugs via [GitHub Issues](https://github.com/EngineersMind/pdf-autofillr/issues)
- See [good first issues](https://github.com/EngineersMind/pdf-autofillr/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) for beginner-friendly tasks
- Review our [Code of Conduct](CODE_OF_CONDUCT.md) and [Security Policy](SECURITY.md)

---

## License

MIT — see [LICENSE](LICENSE)