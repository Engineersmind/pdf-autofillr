"""
pdf-autofillr setup — run once after any install.

    pdf-autofillr setup

Detects which modules are installed, then writes:
  .env.example          — exact vars for your combination, commented
  configs/              — form_keys.json, mapper_config.ini, etc.
  data/                 — correct folder skeleton
  README_QUICKSTART.md  — folder layout and next steps
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


# ── Module detection ──────────────────────────────────────────────────────────

def _installed(pkg: str) -> bool:
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False


def detect_combo() -> set[str]:
    combo = set()
    if _installed("chatbot"):
        combo.add("chatbot")
    if _installed("pdf_autofillr_doc_upload"):
        combo.add("doc_upload")
    if _installed("pdf_autofillr_mapper"):
        combo.add("mapper")
    if _installed("ragpdf"):
        combo.add("rag")
    return combo


# ── Config file sources ───────────────────────────────────────────────────────

def _config_source() -> Path | None:
    """Find the config_samples directory from any installed module."""
    for pkg, subpath in [
        ("chatbot", "chatbot/config_samples"),
        ("pdf_autofillr_doc_upload", "pdf_autofillr_doc_upload/config_samples"),
    ]:
        try:
            mod = __import__(pkg)
            src = Path(mod.__file__).parent / "config_samples"
            if src.exists():
                return src
        except Exception:
            pass
    return None


# ── Folder creation ───────────────────────────────────────────────────────────

def _make_dirs(combo: set[str], dest: Path) -> list[str]:
    created = []
    dirs = ["data/input", "configs"]
    if "chatbot" in combo:
        dirs += ["data/chatbot"]
    if "doc_upload" in combo:
        dirs += ["data/doc_upload/jobs"]
    if "mapper" in combo:
        dirs += ["data/mapper/output", "data/mapper/cache"]
    if "rag" in combo:
        dirs += [
            "data/rag/vectors",
            "data/rag/predictions",
            "data/rag/metrics/time_series/global",
            "data/rag/pdf_hash_mapping",
        ]
    for d in dirs:
        p = dest / d
        p.mkdir(parents=True, exist_ok=True)
        created.append(str(p))
    # gitkeep in empty data dirs
    for gk in ["data/input", "data/rag/predictions", "data/rag/metrics"]:
        gkp = dest / gk / ".gitkeep"
        if (dest / gk).exists() and not gkp.exists():
            gkp.touch()
    return created


# ── .env.example content per combo ───────────────────────────────────────────

_ENV_HEADER = """\
# ============================================================
# pdf-autofillr — .env.example
# Combination: {combo_label}
#
# 1. Copy this file:   cp .env.example .env
# 2. Fill in API key   (OPENAI_API_KEY or equivalent)
# 3. Set PDF path      ({pdf_var})
# 4. Run setup again to verify: pdf-autofillr status
# ============================================================

# ── LLM API Keys ─────────────────────────────────────────────
# Uncomment only the block for your provider
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GROQ_API_KEY=gsk_...
# AZURE_API_KEY=
# AZURE_API_BASE=https://your-resource.openai.azure.com/
# AZURE_API_VERSION=2023-05-15
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_REGION=us-east-1
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

"""

_ENV_CHATBOT = """\
# ── CHATBOT ───────────────────────────────────────────────────
CHATBOT_LLM_MODEL=openai/gpt-4o-mini
CHATBOT_LLM_API_KEY=        # leave blank → uses OPENAI_API_KEY above

chatbot_STORAGE=local
chatbot_DATA_PATH=./data/chatbot

# Cloud storage (only set when chatbot_STORAGE != local):
# chatbot_STORAGE=s3
# AWS_OUTPUT_BUCKET=my-chatbot-output
# AWS_CONFIG_BUCKET=my-chatbot-config
# chatbot_STORAGE=gcp
# GCP_OUTPUT_BUCKET=my-chatbot-output
# GCP_CONFIG_BUCKET=my-chatbot-config
# GCP_PROJECT_ID=my-project
# chatbot_STORAGE=azure
# AZURE_OUTPUT_CONTAINER=chatbot-output
# AZURE_CONFIG_CONTAINER=chatbot-config
# AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...

chatbot_CONFIG_PATH=./configs

# none   = collect data only
# mapper = fill a PDF at end of conversation (requires mapper installed)
chatbot_PDF_FILLER=mapper
chatbot_PDF_PATH=./data/input/blank_form.pdf

chatbot_LOG_LEVEL=INFO
chatbot_DEBUG_LOGGING=false

"""

_ENV_DOC_UPLOAD = """\
# ── DOC_UPLOAD ────────────────────────────────────────────────
# Supported document formats: pdf, docx, pptx, xlsx, csv, json, md, txt, html, xml
DOC_UPLOAD_LLM_MODEL=openai/gpt-4.1-mini
DOC_UPLOAD_LLM_API_KEY=     # leave blank → uses OPENAI_API_KEY above

DOC_UPLOAD_STORAGE=local
DOC_UPLOAD_DATA_PATH=./data/doc_upload

# Cloud storage (only set when DOC_UPLOAD_STORAGE != local):
# DOC_UPLOAD_STORAGE=s3
# AWS_OUTPUT_BUCKET=my-doc-upload-output
# AWS_CONFIG_BUCKET=my-doc-upload-config
# DOC_UPLOAD_STORAGE=gcp
# GCP_OUTPUT_BUCKET=my-doc-upload-output
# GCP_CONFIG_BUCKET=my-doc-upload-config
# GCP_PROJECT_ID=my-project
# DOC_UPLOAD_STORAGE=azure
# AZURE_OUTPUT_CONTAINER=doc-upload-output
# AZURE_CONFIG_CONTAINER=doc-upload-config
# AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...

DOC_UPLOAD_CONFIG_PATH=./configs

# none   = extract data only, return JSON
# mapper = extract + fill a blank PDF
DOC_UPLOAD_PDF_FILLER=mapper
DOC_UPLOAD_PDF_PATH=./data/input/blank_form.pdf

DOC_UPLOAD_TELEMETRY=off
# DOC_UPLOAD_TELEMETRY=local     → writes metadata to ./telemetry/events.jsonl
# DOC_UPLOAD_TELEMETRY_PATH=./telemetry

DOC_UPLOAD_LOG_LEVEL=INFO
DOC_UPLOAD_DEBUG_LOGGING=false

"""

_ENV_MAPPER = """\
# ── MAPPER ────────────────────────────────────────────────────
# Most mapper settings are in configs/mapper_config.ini (non-secret)
# Secrets only here.

# Mapper HTTP server auth (only needed when MAPPER_API_URL is set above)
MAPPER_API_KEY=

"""

_ENV_MAPPER_CONNECTION = """\
# ── MAPPER CONNECTION ─────────────────────────────────────────
# How chatbot/doc_upload connects to the mapper
# Empty = inprocess (mapper runs inside the same Python process — easiest)
# Set URL = HTTP mode (mapper running as a separate server)
MAPPER_API_URL=
MAPPER_API_KEY=

"""

_ENV_RAG = """\
# ── MAPPER → RAG INTEGRATION ─────────────────────────────────
# Set RAG_ENABLED=true to activate RAG. Mapper calls RAG after every mapping run.
# RAG vector DB starts empty and learns from each filled form automatically.
RAG_ENABLED=true
RAG_MODE=inprocess          # inprocess | http
RAG_API_URL=                # only needed when RAG_MODE=http
RAG_API_KEY=                # only needed when RAG_MODE=http

# ── RAG STORAGE ───────────────────────────────────────────────
# Where the vector database and prediction history are stored
RAGPDF_STORAGE=local
RAGPDF_DATA_PATH=./data/rag

# Cloud RAG storage (only set when RAGPDF_STORAGE != local):
# RAGPDF_STORAGE=s3
# RAGPDF_S3_BUCKET=my-rag-bucket
# RAGPDF_S3_REGION=us-east-1
# RAGPDF_S3_PREFIX=ragpdf/
# RAGPDF_STORAGE=azure
# RAGPDF_AZURE_ACCOUNT=mystorageaccount
# RAGPDF_AZURE_CONTAINER=ragpdf
# RAGPDF_AZURE_CONN_STR=DefaultEndpointsProtocol=https;...
# RAGPDF_STORAGE=gcs
# RAGPDF_GCS_BUCKET=my-rag-bucket
# RAGPDF_GCS_PREFIX=ragpdf/

# ── RAG EMBEDDINGS ────────────────────────────────────────────
# sentence_transformer = local model, NO API key needed (recommended to start)
# openai               = faster, needs OPENAI_API_KEY above
# litellm              = any LiteLLM provider
RAGPDF_EMBEDDING_BACKEND=sentence_transformer
RAGPDF_ST_MODEL=all-MiniLM-L6-v2
# RAGPDF_OPENAI_EMBEDDING_MODEL=text-embedding-3-small   (when backend=openai)
# RAGPDF_LITELLM_EMBEDDING_MODEL=openai/text-embedding-3-small  (when backend=litellm)

# ── RAG VECTOR STORE ──────────────────────────────────────────
# local    = JSON file on disk — zero deps, great for dev (start here)
# s3/azure/gcs = same JSON in cloud (uses RAGPDF_STORAGE credentials above)
# pinecone = managed vector DB
# chroma   = ChromaDB (local embedded)
# weaviate = Weaviate
RAGPDF_VECTOR_STORE=local
# PINECONE_API_KEY=pc-...                              (when RAGPDF_VECTOR_STORE=pinecone)
# RAGPDF_PINECONE_INDEX=ragpdf-vectors
# RAGPDF_PINECONE_NAMESPACE=default
# RAGPDF_CHROMA_PATH=./data/chroma                     (when RAGPDF_VECTOR_STORE=chroma)
# RAGPDF_CHROMA_COLLECTION=ragpdf_vectors
# RAGPDF_WEAVIATE_URL=http://localhost:8080             (when RAGPDF_VECTOR_STORE=weaviate)
# RAGPDF_WEAVIATE_API_KEY=
# RAGPDF_WEAVIATE_CLASS=RagpdfVector

# ── RAG LLM CORRECTOR ─────────────────────────────────────────
# Used during user feedback (submit_feedback API) to correct wrong predictions
# noop      = snake_case cleanup only, no LLM call (safe default)
# openai    = GPT model (needs OPENAI_API_KEY above)
# anthropic = Claude (needs ANTHROPIC_API_KEY above)
# litellm   = any provider
RAGPDF_CORRECTOR_BACKEND=noop
# RAGPDF_OPENAI_MODEL=gpt-4o-mini              (when backend=openai)
# RAGPDF_OPENAI_TEMPERATURE=0.3
# RAGPDF_ANTHROPIC_MODEL=claude-3-5-haiku-20241022  (when backend=anthropic)
# RAGPDF_LITELLM_CORRECTOR_MODEL=openai/gpt-4o-mini  (when backend=litellm)

# ── RAG PREDICTION TUNING ─────────────────────────────────────
# Start with defaults. Tune only if accuracy is unsatisfactory.
RAGPDF_PREDICTION_THRESHOLD=0.75
RAGPDF_TOP_K=5
RAGPDF_AMBIGUITY_THRESHOLD=0.10
RAGPDF_CONFIDENCE_DECAY_RATE=0.95
RAGPDF_CONFIDENCE_GROWTH_RATE=1.05
RAGPDF_MAX_CONFIDENCE=0.99
RAGPDF_MIN_CONFIDENCE=0.50

# ── RAG SERVER (only when RAG_MODE=http) ──────────────────────
RAGPDF_API_KEY=dev-key
# RAGPDF_SERVER_HOST=0.0.0.0
# RAGPDF_SERVER_PORT=8000

RAGPDF_LOG_LEVEL=INFO

"""


def build_env_example(combo: set[str]) -> str:
    has_chatbot = "chatbot" in combo
    has_doc = "doc_upload" in combo
    has_rag = "rag" in combo

    parts = [combo.__class__.__name__]  # placeholder replaced below
    label = " + ".join(sorted(combo)) or "standalone"
    pdf_var = "chatbot_PDF_PATH" if has_chatbot else "DOC_UPLOAD_PDF_PATH"

    content = _ENV_HEADER.format(combo_label=label, pdf_var=pdf_var)

    if has_chatbot:
        content += _ENV_CHATBOT
    if has_doc:
        content += _ENV_DOC_UPLOAD
    if "mapper" in combo:
        if has_chatbot or has_doc:
            content += _ENV_MAPPER_CONNECTION
        else:
            content += _ENV_MAPPER
    if has_rag:
        content += _ENV_RAG

    return content


# ── mapper_config.ini content ─────────────────────────────────────────────────

def build_mapper_ini(combo: set[str]) -> str:
    has_rag = "rag" in combo
    rag_section = """
[rag]
# Set enabled=true AND RAG_ENABLED=true in .env to activate RAG
enabled = true
mode = inprocess
api_url =
api_key =
""" if has_rag else """
[rag]
# RAG is not in your installed combination.
# To add: pip install "pdf-autofillr[chatbot,rag]" and re-run pdf-autofillr setup
enabled = false
"""
    return f"""\
# pdf-autofillr-mapper configuration
# Non-secret settings only. API keys go in .env.
# Combination: {" + ".join(sorted(combo))}

[general]
source_type = local          # local | aws | azure | gcp
pdf_cache_enabled = true

[mapping]
# Any LiteLLM model string — must match your API key in .env
# openai:   gpt-4o, gpt-4.1-mini
# anthropic: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
# bedrock:  bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
# azure:    azure/gpt-4o
# ollama:   ollama/llama3.1  (no key needed)
llm_model = gpt-4o
llm_temperature = 0.0
llm_max_tokens = 4096
llm_timeout = 120
llm_max_retries = 3
confidence_threshold = 0.7
chunking_strategy = page     # page | window
chunking_chunk_size = 9
chunking_overlap = 1
include_description = 1
use_second_mapper = false

[headers]
headers_llm_model = gpt-4o
headers_temperature = 0.0
headers_max_tokens = 8192
headers_chunk_size = 5
headers_max_workers = 3

[local]
output_base_path = ./data/mapper/output
cache_registry_path = ./data/mapper/cache/hash_registry.json
temp_local_dir = /tmp

[aws]
output_base_path = s3://YOUR_BUCKET/mapper/output
cache_registry_path = s3://YOUR_BUCKET/mapper/cache/hash_registry.json
temp_local_dir = /tmp

[azure]
output_base_path = azure://YOUR_CONTAINER/mapper/output
cache_registry_path = azure://YOUR_CONTAINER/mapper/cache/hash_registry.json
temp_local_dir = /tmp

[gcp]
output_base_path = gs://YOUR_BUCKET/mapper/output
cache_registry_path = gs://YOUR_BUCKET/mapper/cache/hash_registry.json
temp_local_dir = /tmp

[notifications]
teams_notifications_enabled = false
teams_webhook_url =
{rag_section}"""


# ── README_QUICKSTART.md ──────────────────────────────────────────────────────

def build_quickstart(combo: set[str]) -> str:
    label = " + ".join(sorted(combo)) or "standalone"
    has_chatbot = "chatbot" in combo
    has_doc = "doc_upload" in combo
    has_rag = "rag" in combo

    folder_lines = ["```", "data/", "├── input/", "│   └── blank_form.pdf   ← PUT YOUR BLANK PDF HERE"]
    if has_chatbot:
        folder_lines += [
            "├── chatbot/", "│   └── {user_id}/sessions/{session_id}/",
            "│       ├── final_output_flat.json   ← all collected fields",
            "│       ├── fill_report.json          ← which fields were filled",
            "│       └── filled.pdf                ← the filled PDF",
        ]
    if has_doc:
        folder_lines += [
            "├── doc_upload/", "│   └── jobs/{job_id}/",
            "│       ├── output_flat.json   ← extracted fields",
            "│       └── filled.pdf         ← the filled PDF",
        ]
    if "mapper" in combo:
        folder_lines += [
            "├── mapper/", "│   ├── output/{user_id}/pdfs/{pdf_id}/",
            "│   │   ├── blank_form_extracted.json",
            "│   │   ├── blank_form_mapped.json",
            "│   │   └── blank_form_filled.pdf",
            "│   └── cache/hash_registry.json",
        ]
    if has_rag:
        folder_lines += [
            "└── rag/", "    ├── vectors/vector_database.json   ← grows automatically",
            "    ├── predictions/{user_id}/{session_id}/{pdf_id}/",
            "    └── metrics/time_series/",
        ]
    folder_lines.append("```")

    next_steps = []
    if has_chatbot:
        next_steps.append("- **Start chatbot:** `chatbot-server` or `python api_server.py` in chatbot/")
    if has_doc:
        next_steps.append("- **Start doc_upload:** `doc-upload-server` or `python entrypoints/fastapi_app.py` in doc_upload/")
    if "mapper" in combo and not has_chatbot and not has_doc:
        next_steps.append("- **Start mapper:** `pdf-mapper-server` or `python api_server.py` in mapper/")
    if has_rag:
        next_steps.append("- **Start RAG server (HTTP mode):** `ragpdf-server` in rag/")

    return f"""\
# pdf-autofillr Quickstart
**Combination:** {label}

## 1. Configure
```bash
cp .env.example .env
# Edit .env:
#   Set your API key (OPENAI_API_KEY or equivalent)
#   Set the path to your blank PDF form
```

## 2. Drop your blank PDF
```
data/input/blank_form.pdf
```
This is the empty PDF form that will be filled with investor data.

## 3. Folder structure
{chr(10).join(folder_lines)}

## 4. Start
{chr(10).join(next_steps)}

## Key files
| File | Purpose |
|------|---------|
| `.env` | All secrets and runtime config |
| `configs/form_keys.json` | Your field schema — defines all fillable fields |
| `configs/mapper_config.ini` | Mapper LLM model, chunking, storage, RAG toggle |
| `data/input/blank_form.pdf` | The blank PDF to fill |

## Connections
{'- chatbot → mapper: inprocess by default (set MAPPER_API_URL to use HTTP mode)' if has_chatbot else ''}
{'- doc_upload → mapper: inprocess by default (set MAPPER_API_URL to use HTTP mode)' if has_doc else ''}
{'- mapper → rag: set RAG_ENABLED=true in .env and [rag] enabled=true in mapper_config.ini' if has_rag else ''}

## Docs
- chatbot/README.md
- doc_upload/README.md
- mapper/README.md
- rag/README.md
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def run_setup(dest_str: str = ".") -> None:
    dest = Path(dest_str).resolve()
    combo = detect_combo()

    if not combo:
        print("No pdf-autofillr modules detected.")
        print("Install one first, e.g.: pip install pdf-autofillr[chatbot]")
        return

    label = " + ".join(sorted(combo))
    print(f"\n📦 Detected modules: {label}\n")

    # 1. Create folder skeleton
    created_dirs = _make_dirs(combo, dest)
    print(f"✅ Folders: {len(created_dirs)} directories created/verified")

    # 2. Copy config files from installed modules
    config_src = _config_source()
    configs_dst = dest / "configs"
    configs_dst.mkdir(parents=True, exist_ok=True)

    if config_src and config_src.exists():
        shutil.copytree(str(config_src), str(configs_dst), dirs_exist_ok=True)
        print(f"✅ Configs copied to {configs_dst}")
    else:
        print("⚠  Could not find config_samples — install chatbot or doc_upload to get them")

    # 3. Write mapper_config.ini (always — overwrite with combo-aware version)
    if "mapper" in combo:
        ini_path = configs_dst / "mapper_config.ini"
        ini_path.write_text(build_mapper_ini(combo))
        print(f"✅ mapper_config.ini written: {ini_path}")

    # 4. Write .env.example
    env_path = dest / ".env.example"
    env_path.write_text(build_env_example(combo))
    print(f"✅ .env.example written: {env_path}")

    # 5. Write README_QUICKSTART.md
    qs_path = dest / "README_QUICKSTART.md"
    qs_path.write_text(build_quickstart(combo))
    print(f"✅ README_QUICKSTART.md written: {qs_path}")

    # 6. Print next steps
    has_env = (dest / ".env").exists()
    has_pdf = (dest / "data" / "input" / "blank_form.pdf").exists()

    print(f"""
{'='*60}
Setup complete for: {label}

Next steps:
{'  ✅ .env already exists' if has_env else '  1. cp .env.example .env'}
{'  ✅ blank_form.pdf found' if has_pdf else '  2. Drop your blank PDF into: data/input/blank_form.pdf'}
  {'3' if (has_env and has_pdf) else '3'}. Edit .env → set your API key (OPENAI_API_KEY)
  4. pdf-autofillr status   ← verify everything is ready
{'='*60}
""")
