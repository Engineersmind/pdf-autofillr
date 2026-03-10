# PDF Autofillr

**Intelligent PDF Form Filling System with AI-Powered Field Mapping**

An enterprise-grade platform that automates PDF form filling by intelligently mapping data fields using Large Language Models (LLMs), extracting form structures, and providing both API and conversational interfaces for seamless document processing.

---

## 📚 Documentation Quick Links

| Type | Document | Purpose |
|------|----------|---------|
| 🚀 **Start Here** | **[COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md)** | Complete setup guide (Modules + SDK) |
| 📖 **Overview** | [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) | All documentation organized by topic |
| ⚡ **Quick Reference** | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Commands, troubleshooting, cheat sheet |
| 🏗️ **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) | System design and technical details |
| 🗺️ **Mapper Module** | [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) | Configure & deploy mapper (REQUIRED) |
| 🐍 **Python SDK** | [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md) | Install and use SDK |
| 🔌 **API Reference** | [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md) | REST API endpoints |
| 📝 **Examples** | [sdks/python/examples/README.md](sdks/python/examples/README.md) | Code examples and scripts |

---

## 🎯 What is PDF Autofillr?

PDF Autofillr is a comprehensive system that solves the complex problem of automatically filling PDF forms with structured data. Unlike traditional PDF fillers that require manual field mapping, our system uses AI to:

1. **Intelligently understand** PDF form structures
2. **Automatically map** your data to form fields using LLMs
3. **Embed metadata** into PDFs for reusable mappings
4. **Fill forms** with actual data through APIs or conversational UI
5. **Validate and optimize** the entire process

### Key Features

✅ **AI-Powered Field Mapping** - LLM-based semantic field matching  
✅ **Zero Manual Configuration** - Automatic field detection and mapping  
✅ **Reusable Templates** - Embed mappings once, use forever  
✅ **Multi-Interface** - REST API, Python SDK, CLI, and Chatbot  
✅ **Cloud-Native** - Deployable on AWS, Azure, or GCP  
✅ **RAG-Enhanced** - Retrieval-Augmented Generation for complex forms  
✅ **Enterprise-Ready** - Caching, validation, error handling  

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PDF AUTOFILLR SYSTEM                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│   USER INPUTS    │     │     MODULES      │     │   OUTPUTS    │
└──────────────────┘     └──────────────────┘     └──────────────┘
                                                    
  ┌─────────────┐         ┌──────────────┐         ┌─────────────┐
  │  SDK/CLI    │────────▶│   MAPPER     │────────▶│ Filled PDFs │
  │  (Python/TS)│         │   Module     │         │             │
  └─────────────┘         └──────────────┘         └─────────────┘
                                 │
  ┌─────────────┐                │                  ┌─────────────┐
  │  REST API   │────────────────┤                  │  Metadata   │
  │             │                │                  │  (Embedded) │
  └─────────────┘                │                  └─────────────┘
                                 │
  ┌─────────────┐         ┌──────▼───────┐         ┌─────────────┐
  │  Chatbot    │────────▶│     RAG      │         │   Cache     │
  │  Interface  │         │   Module     │         │  Registry   │
  └─────────────┘         └──────────────┘         └─────────────┘
                                 │
                          ┌──────▼───────┐
                          │  PDF Upload  │
                          │   Module     │
                          └──────────────┘
```

---

## 📦 System Modules

PDF Autofillr consists of 4 core modules that work together to provide a complete PDF processing pipeline:

### 1. **Mapper Module** 🗺️ (CORE ENGINE)

**Purpose:** The heart of the system - extracts, maps, embeds, and fills PDF forms.

**What it does:**
- 📄 **Extract** - Discovers all form fields in a PDF
- 🧠 **Map** - Uses LLM to intelligently match fields to your data schema
- 📝 **Embed** - Stores mapping metadata inside the PDF for reuse
- ✍️ **Fill** - Populates PDFs with actual data

**Key Features:**
- Semantic field matching using OpenAI/Claude/Bedrock
- PDF hash-based caching for speed
- Support for text fields, checkboxes, radio buttons, dropdowns
- Multi-cloud storage (AWS S3, Azure Blob, GCP Storage, Local)
- Automatic header detection and grouping
- RAG integration for complex forms

**Technology Stack:**
- Python 3.8+
- PyMuPDF (fitz) for PDF processing
- LiteLLM for unified LLM access
- FastAPI for REST API
- S3/Azure/GCP for cloud storage

**Setup & Deployment:**
📖 See **[modules/mapper/README.md](modules/mapper/README.md)**  
📖 See **[modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md)**

**Quick Start:**
```bash
cd modules/mapper
cp .env.example .env          # Add your API keys
cp config.ini.example config.ini  # Configure paths
pip install -r requirements.txt requirements-api.txt
python api_server.py          # Start server on :8000
```

---

### 2. **Chatbot Module** 💬 (CONVERSATIONAL UI)

**Purpose:** Conversational interface for users to fill forms via natural language chat.

**What it does:**
- 💬 **Interactive Chat** - Guides users through form filling conversations
- 🎯 **Smart Extraction** - Extracts structured data from natural language
- 🔄 **State Management** - Maintains conversation context across sessions
- ✅ **Validation** - Validates phone numbers, emails, and other fields
- 🤖 **Multi-Step Workflows** - Investor type selection, data collection, PDF generation

**Key Features:**
- State machine-based conversation flow
- LLM-powered field extraction from user messages
- S3-based session persistence
- Integration with Mapper and RAG modules
- Microsoft Teams notifications
- API key authentication

**Technology Stack:**
- Python 3.8+
- AWS Lambda (serverless)
- OpenAI/Claude for conversation and extraction
- S3 for session storage
- API Gateway / Function URLs

**Setup & Deployment:**
📖 See **[rough_docs/MODULE_chatbot_lambda.md](rough_docs/MODULE_chatbot_lambda.md)**

**Status:** 🚧 Code exists, needs documentation migration

---

### 3. **RAG Module** 🔍 (ENHANCED MAPPING)

**Purpose:** Retrieval-Augmented Generation for improved field mapping on complex forms.

**What it does:**
- 📚 **Document Retrieval** - Finds relevant form examples and templates
- 🧩 **Context Enhancement** - Adds domain knowledge to mapping process
- 🎯 **Accuracy Boost** - Improves mapping quality for specialized forms
- 🔄 **Parallel Processing** - Works alongside semantic mapper

**Key Features:**
- Vector-based document retrieval
- Domain-specific knowledge injection
- Fallback mapping strategy
- Combined predictions with confidence scores

**Technology Stack:**
- Python 3.8+
- Vector databases (embeddings)
- LLM integration
- AWS Lambda / API Gateway

**Setup & Deployment:**
📖 See **[rough_docs/MODULE_rag_lambda.md](rough_docs/MODULE_rag_lambda.md)** (if exists)

**Status:** 🚧 Code exists, needs documentation migration

**Integration:**
```ini
# In mapper config.ini
[mapping]
use_second_mapper = true

[general]
rag_api_url = https://your-rag-api-url.com
```

---

### 4. **PDF Upload Module** 📤 (STORAGE & MANAGEMENT)

**Purpose:** Handles PDF document uploads, storage, and retrieval.

**What it does:**
- 📤 **Upload Handling** - Receives and stores PDF files
- 🗂️ **Storage Management** - Organizes PDFs by user/document IDs
- 🔗 **URL Generation** - Creates signed URLs for secure access
- 📊 **Metadata Tracking** - Tracks upload status and document info

**Key Features:**
- Multi-cloud storage support
- Secure file uploads with validation
- Document versioning
- Integration with Mapper module

**Technology Stack:**
- Python 3.8+
- AWS S3 / Azure Blob / GCP Storage
- Lambda / Serverless functions
- API Gateway

**Setup & Deployment:**
📖 See **[rough_docs/MODULE_pdf_upload_lambda.md](rough_docs/MODULE_pdf_upload_lambda.md)** (if exists)

**Status:** 🚧 Code exists, needs documentation migration

---

## 🛠️ SDKs & Client Libraries

PDF Autofillr provides multiple ways to interact with the system:

### Python SDK 🐍

**Location:** `sdks/python/`

**What you get:**
- ✅ **Python Client Library** - `PDFMapperClient` class for programmatic access
- ✅ **CLI Tool** - `pdf-autofiller` command-line interface
- ✅ **Rich Output** - Beautiful terminal output with progress indicators
- ✅ **Full API Coverage** - All mapper endpoints available

**Installation:**
```bash
cd sdks/python
pip install -e .
```

**Setup & Usage:**
📖 See **[sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md)**  
📖 See **[sdks/python/examples/README.md](sdks/python/examples/README.md)**

**Quick Example:**
```python
from pdf_autofiller import PDFMapperClient

client = PDFMapperClient(api_url="http://localhost:8000")

# Extract + Map + Embed in one call
result = client.make_embed_file(
    pdf_path="input.pdf",
    user_id=1,
    pdf_doc_id=100
)

# Fill the embedded PDF
filled = client.fill_pdf(
    embedded_pdf_path=result['embedded_pdf_path'],
    input_json_path="data.json",
    user_id=1,
    pdf_doc_id=100
)
```

**CLI Example:**
```bash
# Complete pipeline
pdf-autofiller make-embed input.pdf

# Fill embedded PDF
pdf-autofiller fill embedded.pdf data.json
```

---

### TypeScript SDK 📘

**Location:** `sdks/typescript/`

**What you get:**
- TypeScript type definitions
- Node.js client library
- Browser-compatible builds
- Full API coverage

**Status:** 🚧 In development

**Setup & Usage:**
📖 See **[sdks/typescript/README.md](sdks/typescript/README.md)** (coming soon)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- LLM API Key (OpenAI, Anthropic Claude, or AWS Bedrock)
- Cloud storage (AWS S3, Azure Blob, or local filesystem)

### Complete Setup Flow

**IMPORTANT: You must set up modules BEFORE using SDKs!**

#### Step 1: Set Up Mapper Module (Server)

```bash
# 1. Navigate to mapper module
cd modules/mapper

# 2. Configure environment
cp .env.example .env
cp config.ini.example config.ini

# 3. Edit .env - Add your API key
nano .env
# Add: OPENAI_API_KEY=sk-your-key-here

# 4. Edit config.ini - Set storage paths
nano config.ini
# Update [local] paths or [aws]/[azure] settings

# 5. Install dependencies
pip install -r requirements.txt requirements-api.txt

# 6. Start API server
python api_server.py
# Server runs on http://localhost:8000
```

✅ **Verify:** Open http://localhost:8000/docs in your browser

📖 **Detailed Guide:** [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md)

---

#### Step 2: Install & Configure SDK (Client)

```bash
# In a NEW terminal
cd sdks/python

# 1. Configure (optional)
cp .env.example .env
nano .env
# Set: PDF_AUTOFILLER_API_URL=http://localhost:8000

# 2. Install SDK
pip install -e .

# 3. Test connection
cd examples
python test_connection.py
```

📖 **Detailed Guide:** [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md)

---

#### Step 3: Use the System

**Option A: CLI**
```bash
pdf-autofiller extract input.pdf
pdf-autofiller make-embed input.pdf
pdf-autofiller fill embedded.pdf data.json
```

**Option B: Python**
```python
from pdf_autofiller import PDFMapperClient

client = PDFMapperClient("http://localhost:8000")
result = client.make_embed_file("input.pdf", 1, 100)
```

**Option C: REST API**
```bash
curl -X POST http://localhost:8000/mapper/extract \
  -F "pdf_file=@input.pdf" \
  -F "user_id=1" \
  -F "pdf_doc_id=100"
```

📖 **Complete Flow:** [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md)

---

## 📖 Documentation Structure

```
pdf-autofillr/
├── README.md                          ← You are here
├── COMPLETE_SETUP_FLOW.md             ← End-to-end setup guide
│
├── modules/                           ← Backend Modules
│   ├── mapper/                        ← Core PDF processing
│   │   ├── README.md                  ← Module overview
│   │   ├── SETUP_GUIDE.md             ← Configuration guide
│   │   ├── API_SERVER.md              ← API documentation
│   │   └── INSTALLATION_GUIDE.md      ← Deployment guide
│   │
│   ├── chatbot/                       ← Conversational UI
│   ├── rag/                           ← Enhanced mapping
│   └── pdf_upload/                    ← Storage management
│
├── sdks/                              ← Client Libraries
│   ├── python/                        ← Python SDK
│   │   ├── QUICKSTART.md              ← Quick start guide
│   │   ├── README.md                  ← SDK overview
│   │   └── examples/README.md         ← Example scripts
│   │
│   └── typescript/                    ← TypeScript SDK
│       └── README.md
│
├── docs/                              ← Full Documentation
│   ├── api-reference/                 ← API specs
│   ├── architecture/                  ← Architecture docs
│   └── guides/                        ← How-to guides
│
└── rough_docs/                        ← Legacy/Working Docs
    ├── MODULE_chatbot_lambda.md       ← Chatbot module details
    ├── MODULE_rag_lambda.md           ← RAG module details
    └── MODULE_pdf_upload_lambda.md    ← Upload module details
```

---

## 🔧 Module Setup Order

**Before using any SDK, you MUST set up the corresponding module(s):**

| Module | Setup Required? | Documentation | Status |
|--------|----------------|---------------|--------|
| **Mapper** | ✅ Required for SDK | [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) | ✅ Complete |
| **Chatbot** | ✅ Required for chat UI | [rough_docs/MODULE_chatbot_lambda.md](rough_docs/MODULE_chatbot_lambda.md) | 🚧 Needs migration |
| **RAG** | 🔷 Optional | [rough_docs/](rough_docs/) | 🚧 Needs migration |
| **PDF Upload** | 🔷 Optional | [rough_docs/](rough_docs/) | 🚧 Needs migration |

### Setup Checklist

- [ ] **Mapper Module** - Configure `.env` and `config.ini`
- [ ] **Start Server** - Run `python api_server.py`
- [ ] **Verify Server** - Check http://localhost:8000/health
- [ ] **Install SDK** - Run `pip install -e sdks/python`
- [ ] **Test Connection** - Run SDK example scripts
- [ ] **(Optional) Chatbot** - Deploy Lambda function
- [ ] **(Optional) RAG** - Set up RAG API endpoint

---

## 🎯 Use Cases

### 1. **Financial Forms**
- Investment applications
- Account opening forms
- Tax documents (W-8BEN, W-9)
- Compliance forms

### 2. **Legal Documents**
- Contracts and agreements
- Power of attorney forms
- Affidavits

### 3. **Healthcare Forms**
- Patient intake forms
- Insurance claims
- Medical records requests

### 4. **Government Forms**
- Visa applications
- Permit requests
- Regulatory filings

### 5. **HR & Employment**
- Job applications
- Onboarding forms
- Benefits enrollment

---

## 🏢 Deployment Options

### Local Development
```bash
python api_server.py
```

### Docker
```bash
docker build -t pdf-autofiller .
docker run -p 8000:8000 --env-file .env pdf-autofiller
```

### AWS Lambda
- Serverless deployment
- Auto-scaling
- Pay-per-use pricing

📖 See `deployment/aws/`

### Azure Functions
- Serverless deployment
- Azure Blob Storage integration

📖 See `deployment/azure/`

### GCP Cloud Functions
- Serverless deployment
- GCS integration

📖 See `deployment/gcp/`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific module tests
cd modules/mapper
pytest tests/

# With coverage
pytest --cov=src --cov-report=html
```

---

## 📊 Performance

- **Extraction:** ~2-5 seconds per PDF
- **Mapping:** ~10-30 seconds (LLM call)
- **Embedding:** ~1-2 seconds
- **Filling:** <1 second
- **Caching:** 95%+ speed improvement on repeat PDFs

---

## 🔒 Security

- API key authentication
- Secure file uploads
- Environment variable configuration
- No credentials in code
- Cloud storage encryption
- HTTPS/TLS in production

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

See [LICENSE](LICENSE) file for details.

---

## 🆘 Support & Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Module 'boto3' not found" | Set `rag_api_url = ` (empty) in config.ini |
| "OpenAI API key not found" | Add `OPENAI_API_KEY=sk-...` to .env |
| "Connection refused" | Start server: `cd modules/mapper && python api_server.py` |
| "Command not found: pdf-autofiller" | Install SDK: `cd sdks/python && pip install -e .` |

### Getting Help

- 📖 **Documentation:** Check module-specific READMEs
- 🐛 **Issues:** [GitHub Issues](https://github.com/Engineersmind/pdf-autofillr/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/Engineersmind/pdf-autofillr/discussions)

---

## 🗺️ Roadmap

- [x] Core mapper module with LLM mapping
- [x] Python SDK with CLI
- [x] FastAPI server
- [x] Cloud storage support (AWS, Azure, GCP)
- [x] Caching system
- [x] RAG integration
- [x] Chatbot interface
- [ ] TypeScript SDK
- [ ] Web UI dashboard
- [ ] Batch processing
- [ ] Webhook notifications
- [ ] Advanced analytics
- [ ] Multi-language support

---

## 🌟 Quick Links

| Resource | Link |
|----------|------|
| **Setup Guide** | [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md) |
| **Mapper Module** | [modules/mapper/README.md](modules/mapper/README.md) |
| **Python SDK** | [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md) |
| **API Docs** | [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md) |
| **Examples** | [sdks/python/examples/](sdks/python/examples/) |
| **Architecture** | [docs/architecture/](docs/architecture/) |

---

## 💡 TL;DR

```bash
# 1. Set up mapper module
cd modules/mapper
cp .env.example .env && cp config.ini.example config.ini
# Edit files, add API key
pip install -r requirements.txt requirements-api.txt
python api_server.py

# 2. Install SDK (new terminal)
cd sdks/python
pip install -e .

# 3. Use it
pdf-autofiller make-embed input.pdf
pdf-autofiller fill embedded.pdf data.json
```

**That's it!** 🚀

---

Made with ❤️ by [Engineersmind](https://github.com/Engineersmind)

