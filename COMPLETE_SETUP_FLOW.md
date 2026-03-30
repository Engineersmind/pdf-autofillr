# Complete Setup Flow: Mapper Module + SDK

This document shows the complete flow from setting up the mapper module to using the SDK.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  USER'S LAPTOP (SDK Client)                                │
│                                                             │
│  ┌────────────────────────────────────────────────┐        │
│  │ SDK (Client Side)                               │        │
│  │ - Python library: pdf_autofiller                │        │
│  │ - CLI tool: pdf-autofiller command              │        │
│  │ - Config: .env or config.json                   │        │
│  └────────────────────────────────────────────────┘        │
│                        │                                     │
│                        │ HTTP Requests                       │
│                        ▼                                     │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ http://localhost:8000
                         │
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  SERVER (Mapper Module API)                                │
│                                                             │
│  ┌────────────────────────────────────────────────┐        │
│  │ api_server.py (FastAPI)                        │        │
│  │ - Port: 8000                                    │        │
│  │ - Endpoints: /mapper/extract, /map, /fill      │        │
│  │ - Config: .env + config.ini                     │        │
│  └────────────────────────────────────────────────┘        │
│                        │                                     │
│                        │ Calls                               │
│                        ▼                                     │
│  ┌────────────────────────────────────────────────┐        │
│  │ src/orchestrator.py                             │        │
│  │ - Coordinates operations                        │        │
│  │ - Uses LLM (OpenAI/Claude/etc)                  │        │
│  │ - Reads/writes to storage                       │        │
│  └────────────────────────────────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Setup

### STEP 1: Configure Mapper Module (Server Side)

```bash
cd modules/mapper
```

#### 1.1 Create .env file

```bash
cp .env.example .env
nano .env
```

**Add your API key:**
```bash
CLOUD_PROVIDER=local
OPENAI_API_KEY=sk-your-actual-key-here
```

#### 1.2 Create config.ini file

```bash
cp config.ini.example config.ini
nano config.ini
```

**Update paths:**
```ini
[general]
source_type = local
rag_api_url = 

[mapping]
llm_model = gpt-4o
use_second_mapper = false

[local]
cache_registry_path = /Users/yourname/pdf-autofiller/cache/hash_registry.json
output_base_path = /Users/yourname/pdf-autofiller/output
```

#### 1.3 Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-api.txt
```

#### 1.4 Start Server

```bash
python api_server.py
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

#### 1.5 Verify Server

In another terminal:
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-03-09T12:00:00"
}
```

✅ **Mapper module is now running!**

---

### STEP 2: Configure SDK (Client Side)

```bash
cd ../../sdks/python
```

#### 2.1 Create SDK .env file

```bash
cp .env.example .env
nano .env
```

**Set API URL:**
```bash
PDF_AUTOFILLER_API_URL=http://localhost:8000
PDF_AUTOFILLER_API_KEY=
PDF_AUTOFILLER_USER_ID=1
PDF_AUTOFILLER_PDF_DOC_ID=100
```

#### 2.2 Install SDK

```bash
pip install -e .
```

**Expected output:**
```
Successfully installed pdf-autofiller-sdk
```

#### 2.3 Test SDK Connection

```bash
cd examples
python test_connection.py
```

**Expected output:**
```
🔗 Using API URL: http://localhost:8000
🔍 Checking server health...
✅ Server is healthy!
   Status: healthy
   Version: 1.0.0
✅ SDK is ready to use!
```

✅ **SDK is now configured and connected!**

---

### STEP 3: Use the SDK

#### Option A: CLI Tool

```bash
# Show help
pdf-autofiller --help

# Extract fields from PDF
pdf-autofiller --api-url http://localhost:8000 extract /path/to/input.pdf

# Complete pipeline (extract + map + embed)
pdf-autofiller --api-url http://localhost:8000 make-embed /path/to/input.pdf

# Fill PDF with data
pdf-autofiller --api-url http://localhost:8000 fill /path/to/embedded.pdf /path/to/data.json
```

#### Option B: Python Library

```python
from pdf_autofiller import PDFMapperClient

# Initialize client
client = PDFMapperClient(api_url="http://localhost:8000")

# Extract fields
result = client.extract(
    pdf_path="/path/to/input.pdf",
    user_id=1,
    pdf_doc_id=100
)
print(f"Extracted: {result}")

# Create embedded PDF (extract + map + embed)
embedded = client.make_embed_file(
    pdf_path="/path/to/input.pdf",
    user_id=1,
    pdf_doc_id=100
)
print(f"Embedded PDF: {embedded['embedded_pdf_path']}")

# Fill embedded PDF
filled = client.fill_pdf(
    embedded_pdf_path=embedded['embedded_pdf_path'],
    input_json_path="/path/to/data.json",
    user_id=1,
    pdf_doc_id=100
)
print(f"Filled PDF: {filled['filled_pdf_path']}")
```

---

## Configuration Files Summary

### Mapper Module Configuration (modules/mapper/)

| File | Purpose | Contains | Required? |
|------|---------|----------|-----------|
| `.env` | Environment variables | API keys, cloud provider | ✅ Yes |
| `config.ini` | Storage & LLM config | Paths, model settings | ✅ Yes |
| `.env.example` | Template | Example env vars | 📝 Template |
| `config.ini.example` | Template | Example config | 📝 Template |

**DO NOT COMMIT**: `.env`, `config.ini` (already in `.gitignore`)

### SDK Configuration (sdks/python/)

| File | Purpose | Contains | Required? |
|------|---------|----------|-----------|
| `.env` | Environment variables | API URL, default IDs | 🔷 Optional |
| `config.json` | JSON config | API settings | 🔷 Optional |
| `.env.example` | Template | Example env vars | 📝 Template |
| `config.json.example` | Template | Example JSON config | 📝 Template |

**Note**: SDK config is optional - you can pass API URL directly to commands/client.

---

## File Locations Reference

```
pdf-autofillr/
│
├── modules/mapper/              ← SERVER (Mapper Module)
│   ├── .env                     ← YOUR CONFIG (add API keys)
│   ├── .env.example             ← Template
│   ├── config.ini               ← YOUR CONFIG (add paths)
│   ├── config.ini.example       ← Template
│   ├── SETUP_GUIDE.md           ← Setup instructions
│   ├── API_SERVER.md            ← API documentation
│   ├── README.md                ← Module overview
│   ├── api_server.py            ← RUN THIS (FastAPI server)
│   ├── requirements.txt         ← Dependencies
│   └── src/                     ← Core code
│
└── sdks/python/                 ← CLIENT (SDK)
    ├── .env                     ← YOUR CONFIG (optional)
    ├── .env.example             ← Template
    ├── config.json.example      ← Template
    ├── setup.py                 ← SDK installer
    ├── QUICKSTART.md            ← SDK guide
    ├── pdf_autofiller/          ← SDK code
    │   ├── cli.py               ← CLI tool
    │   ├── client.py            ← Python client
    │   └── resources/
    └── examples/                ← Example scripts
        ├── test_connection.py   ← Test SDK
        ├── example_with_config.py
        └── README.md
```

---

## Quick Command Cheat Sheet

### First Time Setup

```bash
# 1. Configure mapper module
cd modules/mapper
cp .env.example .env
cp config.ini.example config.ini
# Edit .env and config.ini with your settings
pip install -r requirements.txt requirements-api.txt

# 2. Start server
python api_server.py
# Keep this terminal open!

# 3. In NEW terminal, configure SDK
cd sdks/python
cp .env.example .env
# Edit .env with API URL
pip install -e .

# 4. Test connection
cd examples
python test_connection.py
```

### Daily Usage

```bash
# Terminal 1: Start server
cd modules/mapper
python api_server.py

# Terminal 2: Use SDK
pdf-autofiller --help
pdf-autofiller extract input.pdf
```

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| "Module 'boto3' not found" | Set `rag_api_url = ` (empty) in `modules/mapper/config.ini` |
| "OpenAI API key not found" | Add `OPENAI_API_KEY=sk-...` to `modules/mapper/.env` |
| "Connection refused" | Start server: `cd modules/mapper && python api_server.py` |
| "pdf-autofiller command not found" | Install SDK: `cd sdks/python && pip install -e .` |
| "Import error: LocalConfig" | Already fixed in api_server.py (use LocalStorageConfig) |

---

## What's Different: Mapper vs SDK Config?

### Mapper Module Config (modules/mapper/)
- **Purpose**: Configure the **server** (API)
- **Contains**: API keys, storage paths, LLM settings
- **Required**: Yes - server won't run without it
- **Files**: `.env` + `config.ini`

### SDK Config (sdks/python/)
- **Purpose**: Configure the **client** (SDK)
- **Contains**: API URL, default user/doc IDs
- **Required**: No - can pass directly to commands
- **Files**: `.env` or `config.json` (optional)

---

## Summary

1. **Mapper Module** = Server that does the work
   - Needs: `.env` (API keys) + `config.ini` (paths)
   - Run: `python api_server.py`
   
2. **SDK** = Client that calls the server
   - Needs: API URL (in `.env` or passed directly)
   - Use: `pdf-autofiller` CLI or Python library

3. **Both** have `.env.example` templates
   - Mapper: Configure API keys & cloud provider
   - SDK: Configure API URL & defaults

4. **Order**: 
   1. Configure mapper module
   2. Start server
   3. Configure SDK
   4. Use SDK

That's it! 🚀
