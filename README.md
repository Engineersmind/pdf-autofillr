# PDF Autofillr

**Intelligent PDF Form Filling System with AI-Powered Field Mapping**

An enterprise-grade platform that automates PDF form filling by intelligently mapping data fields using Large Language Models (LLMs), extracting form structures, and providing both API and conversational interfaces for seamless document processing.

---

## ⚡ Quick Start (1 Command!)

```bash
# Windows PowerShell
.\setup.ps1
.\start.ps1

# Mac/Linux
./setup.sh
./start.sh

# Or using Make (all platforms)
make setup
make start
```

Server runs on **http://localhost:8000** using **free open-source Ollama models** (no API keys needed!)

📖 **Full guide:** [GETTING_STARTED.md](GETTING_STARTED.md)

---

## 📚 Documentation Quick Links

| Type | Document | Purpose |
|------|----------|---------|
| ⚡ **Quick Start** | **[GETTING_STARTED.md](GETTING_STARTED.md)** | **1-command setup (Windows/Mac/Linux)** |
| 🆓 **Free LLMs** | **[FREE_LOCAL_LLMS.md](FREE_LOCAL_LLMS.md)** | **Free open-source models (no API costs)** |
| 🐳 **Docker Deploy** | **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** | **Production deployment with GPU config** |
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
┌───────────────────────────────────────────────────────────────────────┐
│                        PDF AUTOFILLR SYSTEM                            │
│                         (3-Layer Architecture)                         │
└───────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────┐
                    │   LAYER 1: INPUT COLLECTION │
                    │   (User Data Sources)       │
                    └─────────────────────────────┘
                                  │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
    ┌───────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐
    │   Chatbot     │    │  PDF Upload  │    │    Manual    │
    │   Module      │    │   Module     │    │  Data Entry  │
    │ (Conversational)   │ (Doc Extract)│    │  (Forms)     │
    └───────┬───────┘    └──────┬───────┘    └──────┬───────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   LAYER 2: PROCESSING    │
                    │   (Core Engine)          │
                    └──────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
    ┌───────▼──────────┐  ┌─────▼────────┐   ┌──────▼────────┐
    │  MAPPER MODULE   │  │ RAG Module   │   │  Orchestrator │
    │                  │  │ (Optional    │   │  (Workflow)   │
    │ • Extract Fields │  │  Enhancement)│   └───────────────┘
    │ • Map Data       │  └──────┬───────┘
    │ • Embed QR/Bar   │         │
    │ • Fill PDF       │◀────────┘
    └───────┬──────────┘
            │
            └────────────────────┼────────────────────┐
                                 │                    │
                    ┌────────────▼─────────────┐      │
                    │   LAYER 3: CLIENT ACCESS │      │
                    │   (Developer Interfaces) │      │
                    └──────────────────────────┘      │
                                 │                    │
            ┌────────────────────┼────────────────┐   │
            │                    │                │   │
    ┌───────▼───────┐    ┌──────▼───────┐    ┌──▼───▼───────┐
    │   SDK/CLI     │    │  REST API    │    │   OUTPUTS    │
    │  (Python)     │    │  (FastAPI)   │    │              │
    │               │    │              │    │ • Filled PDFs│
    └───────────────┘    └──────────────┘    │ • Metadata   │
                                              │ • Cache      │
                                              └──────────────┘
                                  ┌──────────────┐
                         Optional │  RAG Module  │
                                  │  (Enhanced   │
                                  │   Mapping)   │
                                  └──────────────┘
```

---

## 📦 System Modules

PDF Autofillr consists of modules organized into two categories:

### **Category 1: PDF Processing (Required)**
The core engine that processes PDF forms

### **Category 2: User Data Collection (Optional - Choose One or Both)**
Modules that collect user information through different methods

---

## Core Processing Module

### 1. **Mapper Module** 🗺️ (CORE ENGINE - REQUIRED)

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

## User Data Collection Modules

> **Note:** These modules collect user information to fill forms. Choose based on your preferred data collection method.

### 2. **Chatbot Module** 💬 (INPUT COLLECTION - CONVERSATIONAL)

**Purpose:** Collect user data through interactive conversation.

**Collection Method:** Chat-based Q&A interface

**What it does:**
- 💬 **Interactive Chat** - Guides users through conversational form filling
- 🎯 **Smart Extraction** - Extracts structured data from natural language responses
- 🔄 **State Management** - Maintains conversation context across sessions
- ✅ **Validation** - Validates phone numbers, emails, dates, and other fields in real-time
- 🤖 **Multi-Step Workflows** - Investor type selection, progressive data collection
- 🔗 **Mapper Integration** - Sends collected data to Mapper module for PDF generation

**Use Cases:**
- Users don't have existing documents
- Guided, step-by-step data entry
- Natural language interaction preferred
- Mobile-friendly conversational UI

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
📖 See **[docs/guides/chatbot-module.md](docs/guides/chatbot-module.md)**

---

### 3. **PDF Upload Module** 📤 (INPUT COLLECTION - DOCUMENT EXTRACTION)

**Purpose:** Extract user data from uploaded documents (passports, IDs, financial statements).

**Collection Method:** Document upload and automated extraction

**What it does:**
- 📤 **Document Upload** - Accept user document uploads (passport, ID, bank statements)
- 🔍 **Data Extraction** - Extract personal information from uploaded documents
- 📊 **Field Parsing** - Parse names, addresses, dates, account numbers, etc.
- ✅ **Validation** - Verify extracted data accuracy
- 🔗 **Mapper Integration** - Send extracted data to Mapper module for form filling

**Use Cases:**
- Users have existing identity/financial documents
- Faster data entry from pre-existing information
- Bulk document processing
- Automated KYC (Know Your Customer) workflows

**Key Features:**
- Multi-format support (PDF, images, scanned documents)
- OCR-based text extraction
- Intelligent field identification
- Document type detection
- Secure storage and handling

**Technology Stack:**
- Python 3.8+
- AWS Lambda / Serverless functions
- OCR engines (Tesseract, AWS Textract, Azure Form Recognizer)
- S3/Azure Blob/GCP Storage
- API Gateway

**Setup & Deployment:**
📖 See **[docs/guides/pdf-upload-module.md](docs/guides/pdf-upload-module.md)**

**Comparison: Chatbot vs PDF Upload**

| Aspect | Chatbot Module | PDF Upload Module |
|--------|----------------|-------------------|
| **Input Method** | Conversational Q&A | Document upload |
| **User Experience** | Interactive, guided | Quick, automated |
| **Best For** | Users without docs | Users with existing docs |
| **Speed** | Slower (conversation) | Faster (bulk extraction) |
| **Accuracy** | Depends on user input | Depends on document quality |
| **Use Together?** | Yes - hybrid approach for maximum flexibility |

---

## Enhancement Module

### 4. **RAG Module** 🔍 (ENHANCEMENT - OPTIONAL)

**Purpose:** Retrieval-Augmented Generation for improved field mapping on complex forms.
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
📖 See **[docs/guides/rag-module.md](docs/guides/rag-module.md)**

**Status:** � Optional - Integrates with Mapper module

**Integration:**
```ini
# In mapper config.ini
[mapping]
use_second_mapper = true

[general]
rag_api_url = https://your-rag-api-url.com
```

---

## 🔄 Complete System Flow

```
┌────────────────────────────────────────────────────────────────┐
│                   PHASE 1: DATA COLLECTION                      │
│              (Choose Chatbot OR Upload OR Both)                 │
└────────────────────────────────────────────────────────────────┘

  Option A: Conversational          Option B: Document Upload
  ┌──────────────────┐              ┌──────────────────┐
  │ CHATBOT MODULE   │              │ PDF UPLOAD       │
  │                  │              │ MODULE           │
  │ User: "My name   │              │ [Upload passport]│
  │ is John Doe"     │              │ [Upload bank     │
  │                  │              │  statement]      │
  │ Bot extracts:    │              │                  │
  │ {name:"John Doe"}│              │ Extracts:        │
  │                  │              │ {name, address,  │
  │ Interactive Q&A  │              │  account, etc.}  │
  └────────┬─────────┘              └────────┬─────────┘
           │                                  │
           └──────────────┬───────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   COLLECTED USER DATA │
              │   (Standardized JSON) │
              │                       │
              │   {                   │
              │     "firstName": "...",│
              │     "lastName": "...", │
              │     "address": "...",  │
              │     ...               │
              │   }                   │
              └───────────┬───────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│              PHASE 2: PDF PROCESSING                            │
│                 (Mapper Module)                                 │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   MAPPER MODULE       │
              │                       │
              │ 1. Extract PDF fields │
              │ 2. Map to user data   │◄──── Optional: RAG
              │ 3. Embed metadata     │      (Enhanced mapping)
              │ 4. Fill PDF form      │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   COMPLETED PDF       │
              │   Ready for download  │
              └───────────────────────┘
```

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
├── QUICK_REFERENCE.md                 ← Commands and troubleshooting
├── ARCHITECTURE.md                    ← System architecture
├── DOCUMENTATION_INDEX.md             ← Complete documentation index
│
├── docs/                              ← 📚 Complete Documentation
│   ├── README.md                      ← Documentation hub
│   ├── guides/                        ← Module guides
│   │   ├── mapper-module.md           ← Mapper module guide
│   │   ├── chatbot-module.md          ← Chatbot module guide
│   │   ├── pdf-upload-module.md       ← PDF upload module guide
│   │   ├── rag-module.md              ← RAG module guide
│   │   └── orchestrator-module.md     ← Orchestrator guide
│   │
│   ├── architecture/                  ← Architecture docs
│   │   ├── system-overview.md         ← Complete system architecture
│   │   └── dual-mapper-flow.md        ← Dual mapper design
│   │
│   └── api-reference/                 ← API specifications
│       └── (OpenAPI specs in sdks/)
│
├── modules/                           ← Backend Modules
│   ├── mapper/                        ← Core PDF processing
│   │   ├── README.md                  ← Module overview
│   │   ├── SETUP_GUIDE.md             ← Configuration guide
│   │   ├── API_SERVER.md              ← API documentation
│   │   └── INSTALLATION_GUIDE.md      ← Deployment guide
│   │
│   ├── chatbot/                       ← Conversational data collection
│   ├── pdf_upload/                    ← Document upload & extraction
│   └── rag/                           ← Enhanced mapping
│
└── sdks/                              ← Client Libraries
    ├── python/                        ← Python SDK
    │   ├── QUICKSTART.md              ← Quick start guide
    │   ├── README.md                  ← SDK overview
    │   └── examples/README.md         ← Example scripts
    │
    └── typescript/                    ← TypeScript SDK
        └── README.md
```

---

## 🔧 Module Setup Order

**Before using any SDK, you MUST set up the corresponding module(s):**

| Module | Type | Setup Required? | Documentation | Status |
|--------|------|----------------|---------------|--------|
| **Mapper** | Processing | ✅ Required | [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) | ✅ Complete |
| **Chatbot** | Input Collection | 🔷 Optional | [docs/guides/chatbot-module.md](docs/guides/chatbot-module.md) | ✅ Complete |
| **PDF Upload** | Input Collection | 🔷 Optional | [docs/guides/pdf-upload-module.md](docs/guides/pdf-upload-module.md) | ✅ Complete |
| **RAG** | Enhancement | 🔷 Optional | [docs/guides/rag-module.md](docs/guides/rag-module.md) | ✅ Complete |

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



