# PDF Autofillr

AI-powered PDF form filling. Extracts fields from a PDF, maps them to your data schema using an LLM, and fills the form automatically — with caching so each template is only processed once.

---

## How it works

```
PDF template + your data schema
         │
         ▼
  make_embed_file          ← run once per PDF template
  (extract → map → embed)
         │
         ▼
  Embedded PDF             ← reusable, metadata baked in
         │
         ▼
  fill_pdf(user data)      ← run once per user
         │
         ▼
  Filled PDF
```

---

## Modules

| Module | Purpose | Status |
|--------|---------|--------|
| **mapper** | Core engine — extract, map, embed, fill | Production |
| **chatbot** | Collect user data through conversation | Production |
| **doc_upload** | Extract user data from uploaded documents | Production |
| **rag-pdf-fillr** | RAG-enhanced mapping for complex forms | Production |

---

## LLM options

You can use any of the following — configure via environment variables:

**Cloud (API key required):**
```bash
# OpenAI
OPENAI_API_KEY=sk-...
# LLM_MODEL=openai/gpt-4o-mini

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
# LLM_MODEL=anthropic/claude-haiku-4-5

# AWS Bedrock (uses IAM — no API key needed)
# LLM_MODEL=bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

**Local — free, no API key:**
```bash
# 1. Install Ollama: https://ollama.com
# 2. Pull a model:
ollama pull llama3.1

# 3. Set in .env:
LLM_MODEL=ollama/llama3.1
OLLAMA_API_BASE=http://localhost:11434
```

Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers) works.

---

## Local development

```bash
cd modules/mapper

# 1. Create virtual environment
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set LLM_MODEL and the matching API key (or Ollama settings above)

# 4. Start FastAPI server
DEPLOY_MODE=fastapi python -m pdf_autofillr_mapper.entrypoints.fastapi_app
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

**Run tests:**
```bash
cd modules/mapper
pytest tests/
```

---

## Production deployment (AWS Lambda)

The mapper runs as a Lambda container image. See [modules/mapper/deploy/terraform/aws/](modules/mapper/deploy/terraform/aws/) for Terraform configuration.

```bash
# Build image
cd modules/mapper
docker build -t pdf-autofillr-mapper:latest .

# Push to ECR and deploy
# See modules/mapper/deploy.sh for the full flow
```

---

## Python SDK

For services that need to call the deployed mapper Lambda programmatically:

```bash
pip install pdf-autofiller
```

```python
from pdf_autofiller import MapperClient

client = MapperClient(api_key="your-api-key")

# Step 1 — process the PDF template (run once per template)
client.make_embed_file(
    user_id=1,
    pdf_doc_id=42,
    session_id="sess-abc",
    env="prod",
)

# Step 2 — check if already cached (optional)
result = client.check_embed_file(user_id=1, pdf_doc_id=42, session_id="sess-abc", env="prod")

# Step 3 — fill with user data
client.fill_pdf(user_id=1, pdf_doc_id=42, session_id="sess-abc", env="prod")
```

For local development, point the SDK at your local FastAPI server:
```python
client = MapperClient(api_key="dev-key", function_url="http://localhost:8000")
```

See [sdks/python/](sdks/python/) for full SDK documentation.

---

## Repository structure

```
pdf-autofillr/
├── modules/
│   ├── mapper/             ← Core PDF processing engine
│   ├── chatbot/            ← Conversational data collection
│   ├── doc_upload/         ← Document upload & extraction
│   └── rag-pdf-fillr/      ← RAG-enhanced mapping
│
├── sdks/
│   ├── python/             ← Python SDK (pdf-autofiller on PyPI)
│   ├── typescript/         ← TypeScript SDK (in progress)
│   └── openapi/            ← OpenAPI specs for all modules
│
├── packages/
│   ├── core/               ← pdf-autofiller-core (extension interfaces)
│   └── plugins/            ← pdf-autofiller-plugins (storage adapters)
│
├── benchmarks/             ← Evaluation datasets and metrics
│   └── datasets/           ← financial, government, hr, insurance, legal, medical
│
└── docs/                   ← Architecture and module guides
```

---

## Contributing

1. Fork the repo and create a branch from `dev`
2. Set up the mapper locally (see [Local development](#local-development) above)
3. Make changes and add tests
4. Open a PR against `dev` — CI runs mapper tests automatically

For questions or bugs, open an issue on [GitHub](https://github.com/Engineersmind/pdf-autofillr/issues).

---

## License

See [LICENSE](LICENSE).
