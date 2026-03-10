# PDF Autofillr Documentation

Complete documentation for the PDF Autofillr system.

---

## 📚 Documentation Structure

### Module Guides
Detailed documentation for each system module:

- **[Mapper Module](guides/mapper-module.md)** - Core PDF processing engine (extract, map, embed, fill)
- **[Chatbot Module](guides/chatbot-module.md)** - Conversational data collection via chat interface
- **[PDF Upload Module](guides/pdf-upload-module.md)** - Document upload and user data extraction
- **[RAG Module](guides/rag-module.md)** - Retrieval-Augmented Generation for enhanced mapping
- **[Orchestrator Module](guides/orchestrator-module.md)** - Workflow coordination

### Architecture Documentation
System design and technical architecture:

- **[System Overview](architecture/system-overview.md)** - Complete system architecture
- **[Dual Mapper Flow](architecture/dual-mapper-flow.md)** - Dual mapper design and workflow

### API Reference
API specifications and references:

- **[Mapper API](../modules/mapper/API_SERVER.md)** - REST API endpoints
- **[OpenAPI Specs](../sdks/)** - Machine-readable API specifications

---

## 🎯 Module Overview

### Core Processing Module

#### **Mapper Module** 🗺️
**Purpose:** PDF form processing engine  
**Functions:**
- Extract form fields from PDFs
- Map fields to data schema using LLM
- Embed metadata into PDFs
- Fill PDFs with actual data

**Documentation:** [guides/mapper-module.md](../modules/mapper/README.md)  
**Setup:** [modules/mapper/SETUP_GUIDE.md](../modules/mapper/SETUP_GUIDE.md)

---

### Input Collection Modules

These modules collect user data through different methods:

#### **Chatbot Module** 💬
**Purpose:** Conversational data collection  
**Method:** Chat-based interface  
**Functions:**
- Interactive Q&A with users
- Extract structured data from natural language
- Guide users through form filling
- State management across conversations

**Documentation:** [guides/chatbot-module.md](guides/chatbot-module.md)  
**Use Case:** When users prefer conversational interface

#### **PDF Upload Module** 📤
**Purpose:** Document-based data extraction  
**Method:** Upload existing documents  
**Functions:**
- Accept user document uploads
- Extract data from uploaded documents
- Parse identity documents, financial statements, etc.
- Pre-fill forms with extracted information

**Documentation:** [guides/pdf-upload-module.md](guides/pdf-upload-module.md)  
**Use Case:** When users have existing documents with their information

> **Note:** Both Chatbot and PDF Upload modules serve the same purpose - collecting user data to fill forms. The difference is the collection method (conversation vs document upload).

---

### Enhancement Module

#### **RAG Module** 🔍
**Purpose:** Enhanced field mapping  
**Functions:**
- Retrieve relevant form examples
- Add domain-specific context
- Improve mapping accuracy
- Parallel processing with semantic mapper

**Documentation:** [guides/rag-module.md](guides/rag-module.md)  
**Use Case:** Complex forms requiring additional context

---

## 🔄 System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION PHASE                         │
└─────────────────────────────────────────────────────────────────┘

Option 1: Conversational                Option 2: Document Upload
┌──────────────────┐                    ┌──────────────────┐
│ CHATBOT MODULE   │                    │ PDF UPLOAD       │
│                  │                    │ MODULE           │
│ • Chat with user │                    │ • Upload docs    │
│ • Extract data   │                    │ • Extract data   │
│ • Validate info  │                    │ • Parse fields   │
└────────┬─────────┘                    └────────┬─────────┘
         │                                        │
         └────────────────┬───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   COLLECTED USER DATA │
              │   (JSON format)       │
              └───────────┬───────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING PHASE                              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   MAPPER MODULE       │
              │                       │
              │   1. Extract fields   │
              │   2. Map to schema    │◄────┐
              │   3. Embed metadata   │     │
              │   4. Fill PDF         │     │
              └───────────────────────┘     │
                                             │
                     Optional: RAG Module ───┘
                     (Enhanced mapping)
                          │
                          ▼
              ┌───────────────────────┐
              │   FILLED PDF FORM     │
              └───────────────────────┘
```

---

## 📖 Quick Navigation

### By Task

| Task | Documentation |
|------|---------------|
| **Set up the system** | [Complete Setup Flow](../COMPLETE_SETUP_FLOW.md) |
| **Configure mapper** | [Mapper Setup Guide](../modules/mapper/SETUP_GUIDE.md) |
| **Deploy chatbot** | [Chatbot Module Guide](guides/chatbot-module.md) |
| **Set up document upload** | [PDF Upload Module Guide](guides/pdf-upload-module.md) |
| **Enable RAG** | [RAG Module Guide](guides/rag-module.md) |
| **Use Python SDK** | [SDK Quickstart](../sdks/python/QUICKSTART.md) |
| **API Reference** | [Mapper API](../modules/mapper/API_SERVER.md) |
| **Understand architecture** | [System Overview](architecture/system-overview.md) |

### By Role

#### **End Users**
- [Main README](../README.md) - What is PDF Autofillr?
- [Quick Reference](../QUICK_REFERENCE.md) - Commands and usage
- [SDK Quickstart](../sdks/python/QUICKSTART.md) - Using the SDK

#### **Developers**
- [System Architecture](architecture/system-overview.md) - Technical design
- [Mapper API](../modules/mapper/API_SERVER.md) - REST API
- [Module Guides](guides/) - Individual module documentation
- [Examples](../sdks/python/examples/) - Code examples

#### **System Administrators**
- [Setup Guide](../COMPLETE_SETUP_FLOW.md) - Installation
- [Mapper Setup](../modules/mapper/SETUP_GUIDE.md) - Configuration
- [Deployment Options](../modules/mapper/INSTALLATION_GUIDE.md) - Cloud deployment

---

## 🔍 Understanding the Modules

### Module Categories

**1. Core Processing (Required)**
- Mapper Module - The engine that processes PDFs

**2. Input Collection (Choose One or Both)**
- Chatbot Module - Collect data via conversation
- PDF Upload Module - Extract data from uploaded documents

**3. Enhancement (Optional)**
- RAG Module - Improve mapping accuracy

### When to Use Each Input Collection Method

**Use Chatbot Module When:**
- Users don't have existing documents
- You want guided form filling experience
- Natural language input is preferred
- Step-by-step data collection needed

**Use PDF Upload Module When:**
- Users have existing documents (passports, statements, etc.)
- Faster data entry from existing information
- Batch processing of documents
- Automated data extraction needed

**Use Both When:**
- Maximum flexibility for users
- Some fields from documents, some from conversation
- Hybrid data collection approach

---

## 📝 Module Status

| Module | Status | Documentation | Code |
|--------|--------|---------------|------|
| **Mapper** | ✅ Production | Complete | Complete |
| **Chatbot** | ✅ Production | [Complete](guides/chatbot-module.md) | Complete |
| **PDF Upload** | ✅ Production | [Complete](guides/pdf-upload-module.md) | Complete |
| **RAG** | ✅ Production | [Complete](guides/rag-module.md) | Complete |
| **Orchestrator** | ✅ Production | [Complete](guides/orchestrator-module.md) | Complete |

---

## 🚀 Getting Started

### Minimum Setup (PDF Processing Only)

```bash
# 1. Set up mapper module
cd modules/mapper
cp .env.example .env
cp config.ini.example config.ini
# Edit files with your API keys and paths
pip install -r requirements.txt requirements-api.txt
python api_server.py
```

### Full Setup (With Data Collection)

```bash
# 1. Set up mapper (required)
cd modules/mapper
# ... (same as above)

# 2. Deploy chatbot (optional - for conversational data collection)
cd modules/chatbot
# Follow deployment guide

# 3. Deploy PDF upload (optional - for document-based data collection)
cd modules/pdf_upload
# Follow deployment guide

# 4. Enable RAG (optional - for enhanced mapping)
# Configure in mapper config.ini:
# use_second_mapper = true
# rag_api_url = https://your-rag-endpoint
```

---

## 🔗 External Links

- **GitHub Repository:** https://github.com/Engineersmind/pdf-autofillr
- **Issues:** https://github.com/Engineersmind/pdf-autofillr/issues
- **Discussions:** https://github.com/Engineersmind/pdf-autofillr/discussions

---

## 📞 Support

- Review [Quick Reference](../QUICK_REFERENCE.md) for troubleshooting
- Check [Module Guides](guides/) for specific module issues
- Search [GitHub Issues](https://github.com/Engineersmind/pdf-autofillr/issues)
- Ask in [Discussions](https://github.com/Engineersmind/pdf-autofillr/discussions)

---

**Last Updated:** March 2026
