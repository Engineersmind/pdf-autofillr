# Mapper Module

The core PDF field extraction, mapping, embedding, and filling engine.

For the full module reference see [`modules/mapper/README.md`](../../modules/mapper/README.md).

---

## What it does

| Step | Operation | Description |
|------|-----------|-------------|
| 1 | **extract** | Detect all form fields in a PDF |
| 2 | **map** | LLM maps each field to a schema key |
| 3 | **embed** | Bake the mapping metadata into the PDF |
| 4 | **fill** | Fill the embedded PDF with user data |

Steps 1–3 run once per PDF template (`make_embed_file`).
Step 4 runs once per user (`fill`).

---

## Quick start

```bash
cd modules/mapper
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config.ini.example config.ini   # set llm_model + storage paths
python api_server.py               # → http://localhost:8000
```

Full setup walkthrough: [`modules/mapper/docs/setup_guide.md`](../../modules/mapper/docs/setup_guide.md)

---

## Configuration

```ini
# modules/mapper/config.ini
[general]
llm_model = gpt-4o-mini        # or anthropic/claude-3-5-haiku, ollama/llama3.1
source_type = local            # local | aws | azure | gcp

[local]
workspace = /path/to/data
```

Set your LLM key as an environment variable:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...   # if using Anthropic
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/extract` | Extract form fields |
| POST | `/map` | LLM semantic mapping |
| POST | `/embed` | Embed metadata into PDF |
| POST | `/fill` | Fill embedded PDF |
| POST | `/make-embed-file` | extract + map + embed |
| POST | `/fill-pdf` | Alias for fill |
| POST | `/run-all` | Full pipeline |
| POST | `/check-embed-file` | Check if PDF has embedded metadata |

Full API reference: [`modules/mapper/docs/api_server.md`](../../modules/mapper/docs/api_server.md)

---

## Python SDK

```bash
pip install pdf-autofiller-mapper[embedded]   # in-process
pip install pdf-autofiller-mapper             # HTTP client only
```

```python
from pdf_autofiller_mapper import PDFMapper, PDFMapperClient
```

SDK guide: [`modules/mapper/sdk/README.md`](../../modules/mapper/sdk/README.md)

---

## Tests

```bash
cd modules/mapper
venv/bin/python -m pytest tests/ --override-ini="addopts=" -q
# 169 passed
```

---

## Deployment

- **Local**: `python api_server.py`
- **Docker**: [`modules/mapper/deployment/docker/`](../../modules/mapper/deployment/docker/)
- **AWS Lambda**: [`modules/mapper/entrypoints/aws_lambda.py`](../../modules/mapper/entrypoints/aws_lambda.py)
- **Azure Function**: [`modules/mapper/entrypoints/azure_function.py`](../../modules/mapper/entrypoints/azure_function.py)
- **GCP Function**: [`modules/mapper/entrypoints/gcp_function.py`](../../modules/mapper/entrypoints/gcp_function.py)
