# PDF Autofillr - Quick Reference Guide

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                      PDF AUTOFILLR ECOSYSTEM                        │
└────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  TIER 1: CLIENT INTERFACES (How users interact)                  │
└──────────────────────────────────────────────────────────────────┘
    │
    ├── Python SDK        → pip install -e sdks/python
    ├── CLI Tool          → pdf-autofiller command
    ├── TypeScript SDK    → npm install (coming soon)
    ├── REST API          → curl / HTTP requests
    └── Chatbot UI        → Conversational interface
    
┌──────────────────────────────────────────────────────────────────┐
│  TIER 2: CORE MODULES (Backend services)                         │
└──────────────────────────────────────────────────────────────────┘
    │
    ├── MAPPER Module     → PDF extraction, mapping, filling
    │   ├── Extract fields from PDF
    │   ├── Map to schema using LLM
    │   ├── Embed metadata
    │   └── Fill PDF with data
    │
    ├── CHATBOT Module    → Conversational interface
    │   ├── Natural language understanding
    │   ├── State management
    │   └── User guidance
    │
    ├── RAG Module        → Enhanced mapping
    │   ├── Document retrieval
    │   └── Context enhancement
    │
    └── PDF UPLOAD Module → Storage management
        ├── File uploads
        └── Document tracking

┌──────────────────────────────────────────────────────────────────┐
│  TIER 3: INFRASTRUCTURE (Where it runs)                          │
└──────────────────────────────────────────────────────────────────┘
    │
    ├── Local Development → FastAPI server
    ├── AWS Lambda        → Serverless functions
    ├── Azure Functions   → Serverless functions
    └── GCP Cloud Func    → Serverless functions
```

---

## Module Responsibilities

### 🗺️ Mapper Module (THE CORE)
**What it does:** Everything related to PDF processing
- Extract form fields
- Map fields to your data
- Embed metadata
- Fill PDFs

**When to use:** Always! This is required for any PDF operation.

**Setup:** [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md)

---

### 💬 Chatbot Module
**What it does:** Chat-based form filling
- Guides users through conversations
- Extracts data from natural language
- Calls mapper module to generate PDFs

**When to use:** When you want conversational UI instead of API.

**Setup:** [rough_docs/MODULE_chatbot_lambda.md](rough_docs/MODULE_chatbot_lambda.md)

---

### 🔍 RAG Module
**What it does:** Improves mapping accuracy
- Retrieves relevant examples
- Adds domain knowledge
- Boosts confidence scores

**When to use:** For complex forms that need extra context.

**Setup:** Optional integration with mapper module.

---

### 📤 PDF Upload Module
**What it does:** Manages PDF storage
- Handles file uploads
- Organizes documents
- Generates access URLs

**When to use:** When you need centralized PDF storage.

**Setup:** Integration with mapper module.

---

## Setup Priority Order

```
Priority 1: MAPPER MODULE
   │
   ├── Configure .env (API keys)
   ├── Configure config.ini (paths)
   ├── Install dependencies
   └── Start server
   
   ✅ NOW SDK CAN BE USED

Priority 2: CHATBOT MODULE (Optional)
   │
   ├── Deploy Lambda function
   ├── Configure S3 for sessions
   └── Set up API Gateway
   
   ✅ NOW CHAT UI AVAILABLE

Priority 3: RAG MODULE (Optional)
   │
   ├── Deploy RAG service
   ├── Set rag_api_url in mapper config
   └── Enable use_second_mapper = true
   
   ✅ NOW ENHANCED MAPPING AVAILABLE

Priority 4: PDF UPLOAD MODULE (Optional)
   │
   └── Deploy upload service
   
   ✅ NOW CENTRALIZED STORAGE AVAILABLE
```

---

## Configuration Files Locations

### Mapper Module (REQUIRED)
```
modules/mapper/
├── .env                  ← ADD YOUR API KEYS HERE
├── .env.example          ← Template (copy this)
├── config.ini            ← ADD YOUR PATHS HERE
└── config.ini.example    ← Template (copy this)
```

### SDK (Optional - can pass directly)
```
sdks/python/
├── .env                  ← ADD API URL HERE (optional)
└── .env.example          ← Template
```

---

## Common Workflows

### Workflow 1: First-Time PDF Processing
```
1. User uploads PDF → Upload Module (optional)
2. SDK calls /mapper/extract → Mapper extracts fields
3. SDK calls /mapper/map → Mapper maps with LLM
4. SDK calls /mapper/embed → Mapper embeds metadata
   Result: Embedded PDF ready for filling
```

### Workflow 2: Filling Embedded PDF
```
1. User provides data JSON
2. SDK calls /mapper/fill → Mapper fills embedded PDF
   Result: Completed PDF
```

### Workflow 3: Complete Pipeline
```
1. SDK calls /mapper/make-embed → Extract + Map + Embed
2. SDK calls /mapper/fill-pdf → Fill embedded PDF
   Result: Completed PDF
```

### Workflow 4: Conversational
```
1. User chats with Chatbot → Chatbot collects data
2. Chatbot calls Mapper → Generate filled PDF
3. Chatbot returns PDF → User downloads
```

---

## API Endpoints Quick Reference

### Mapper Module Endpoints
```
GET  /                     → API info
GET  /health               → Health check
POST /mapper/extract       → Extract fields from PDF
POST /mapper/map           → Map fields to schema
POST /mapper/embed         → Embed metadata in PDF
POST /mapper/fill          → Fill PDF with data
POST /mapper/make-embed    → Extract + Map + Embed (recommended)
POST /mapper/fill-pdf      → Fill embedded PDF
POST /mapper/check-embed   → Check if PDF has embeddings
POST /mapper/run-all       → Complete pipeline
```

---

## SDK Usage Patterns

### Pattern 1: Full Pipeline (Recommended)
```python
from pdf_autofiller import PDFMapperClient

client = PDFMapperClient("http://localhost:8000")

# One call: extract + map + embed
embedded = client.make_embed_file("input.pdf", 1, 100)

# Fill with data
filled = client.fill_pdf(
    embedded['embedded_pdf_path'],
    "data.json",
    1, 100
)
```

### Pattern 2: Step-by-Step
```python
# Step 1: Extract
extracted = client.extract("input.pdf", 1, 100)

# Step 2: Map
mapped = client.map_fields(1, 100)

# Step 3: Embed
embedded = client.embed("input.pdf", 1, 100)

# Step 4: Fill
filled = client.fill(embedded['embedded_pdf_path'], "data.json", 1, 100)
```

### Pattern 3: CLI
```bash
# All-in-one
pdf-autofiller make-embed input.pdf
pdf-autofiller fill embedded.pdf data.json

# Or step-by-step
pdf-autofiller extract input.pdf
pdf-autofiller map --user-id 1 --pdf-doc-id 100
pdf-autofiller embed input.pdf
pdf-autofiller fill embedded.pdf data.json
```

---

## Troubleshooting Decision Tree

```
Problem: SDK not working
│
├─ Is server running?
│  No → cd modules/mapper && python api_server.py
│  Yes → Continue
│
├─ Can you reach http://localhost:8000/health?
│  No → Check firewall, port conflicts
│  Yes → Continue
│
├─ Is SDK installed?
│  No → cd sdks/python && pip install -e .
│  Yes → Continue
│
└─ Check API URL in .env or pass directly to client
```

```
Problem: Server won't start
│
├─ Missing dependencies?
│  → pip install -r requirements.txt requirements-api.txt
│
├─ Config files missing?
│  → cp .env.example .env
│  → cp config.ini.example config.ini
│
├─ API key missing?
│  → Add OPENAI_API_KEY to .env
│
└─ Port 8000 in use?
   → Change port in api_server.py or kill existing process
```

```
Problem: Mapping fails
│
├─ LLM API key valid?
│  → Check OPENAI_API_KEY / ANTHROPIC_API_KEY in .env
│
├─ LLM model available?
│  → Check llm_model in config.ini
│
└─ RAG error?
   → Set rag_api_url = (empty) in config.ini
```

---

## Files You Need to Edit

### First Time Setup

1. **`modules/mapper/.env`**
   - Add your LLM API key
   - Set cloud provider

2. **`modules/mapper/config.ini`**
   - Set storage paths
   - Choose LLM model
   - Configure caching

3. **`sdks/python/.env`** (optional)
   - Set API URL

That's it! Everything else is optional.

---

## Quick Command Reference

```bash
# SETUP (one-time)
cd modules/mapper
cp .env.example .env && cp config.ini.example config.ini
# Edit both files
pip install -r requirements.txt requirements-api.txt

# RUN SERVER
python api_server.py

# INSTALL SDK (new terminal)
cd ../../sdks/python
pip install -e .

# USE SDK
pdf-autofiller make-embed input.pdf
pdf-autofiller fill embedded.pdf data.json

# OR USE PYTHON
python -c "
from pdf_autofiller import PDFMapperClient
client = PDFMapperClient('http://localhost:8000')
print(client.health_check())
"
```

---

## Module Status Legend

✅ **Complete** - Fully functional with documentation  
🚧 **In Progress** - Code exists, docs need migration  
📝 **Planned** - On roadmap  
🔷 **Optional** - Not required for basic usage  

---

## Need Help?

1. **Start Here:** [README.md](README.md)
2. **Setup Issues:** [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md)
3. **SDK Questions:** [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md)
4. **API Reference:** [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md)
5. **Complete Flow:** [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md)
