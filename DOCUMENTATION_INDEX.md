git # Documentation Index

Welcome to PDF Autofillr! This index will help you find the right documentation for your needs.

---

## 🚀 Getting Started (Pick Your Path)

### I want to use the system (FASTEST - Automated Setup!)
→ **[GETTING_STARTED.md](GETTING_STARTED.md)** - 1-command setup for Windows/Mac/Linux  
→ **[COMMANDS.md](COMMANDS.md)** - Complete command reference  
→ **[README.md](README.md)** - Start here for overview  
→ **[COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md)** - Step-by-step manual setup  
→ **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick commands and cheat sheet

### I want to understand the architecture
→ **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and diagrams  
→ **[docs/architecture/](docs/architecture/)** - Detailed architecture docs

### I want to deploy/configure modules
→ **[modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md)** - Mapper setup  
→ **[modules/mapper/INSTALLATION_GUIDE.md](modules/mapper/INSTALLATION_GUIDE.md)** - Deployment guide

### I want to use the SDK
→ **[sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md)** - Python SDK guide  
→ **[sdks/python/examples/README.md](sdks/python/examples/README.md)** - Example scripts

### I want API reference
→ **[modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md)** - REST API docs  
→ **[sdks/](sdks/)** - OpenAPI specs

---

## 📚 Documentation by Type

### Overview Documents
| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](README.md) | Project overview, features, quick start | Everyone |
| [GETTING_STARTED.md](GETTING_STARTED.md) | **Automated 1-command setup** | **Everyone (START HERE!)** |
| [COMMANDS.md](COMMANDS.md) | Complete command reference for all platforms | Everyone |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design | Architects, Developers |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Quick commands and patterns | Users, Developers |
| [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md) | End-to-end manual setup guide | First-time users |

### Automation Scripts
| File | Platform | Purpose |
|------|----------|---------|
| [setup.ps1](setup.ps1) | Windows PowerShell | Automated setup script |
| [setup.sh](setup.sh) | Mac/Linux | Automated setup script |
| [start.ps1](start.ps1) | Windows PowerShell | Start server script |
| [start.sh](start.sh) | Mac/Linux | Start server script |
| [stop.ps1](stop.ps1) | Windows PowerShell | Stop server script |
| [stop.sh](stop.sh) | Mac/Linux | Stop server script |
| [Makefile](Makefile) | All (with Make) | Cross-platform commands |
| [package.json](package.json) | All (with npm) | npm-style commands |

### Module Documentation
| Module | Location | Key Files |
|--------|----------|-----------|
| **Mapper** | `modules/mapper/` | [README.md](modules/mapper/README.md), [SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md), [API_SERVER.md](modules/mapper/API_SERVER.md) |
| **Chatbot** | `modules/chatbot/` | [rough_docs/MODULE_chatbot_lambda.md](rough_docs/MODULE_chatbot_lambda.md) |
| **RAG** | `modules/rag/` | [rough_docs/MODULE_rag_lambda.md](rough_docs/MODULE_rag_lambda.md) |
| **PDF Upload** | `modules/pdf_upload/` | [rough_docs/MODULE_pdf_upload_lambda.md](rough_docs/MODULE_pdf_upload_lambda.md) |

### SDK Documentation
| SDK | Location | Key Files |
|-----|----------|-----------|
| **Python** | `sdks/python/` | [QUICKSTART.md](sdks/python/QUICKSTART.md), [examples/README.md](sdks/python/examples/README.md) |
| **TypeScript** | `sdks/typescript/` | [README.md](sdks/typescript/README.md) _(coming soon)_ |
**Option A: Automated (Recommended)**
1. **Quick Start Guide** → [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Run setup script** → `./setup.sh` or `.\setup.ps1` or `make setup`
3. **Start server** → `./start.sh` or `.\start.ps1` or `make start`
4. **Follow commands** → [COMMANDS.md](COMMANDS.md)

**Option B: Manual**

### API Documentation
| Type | Location | Purpose |
|------|----------|---------|
| REST API | [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md) | Endpoint reference |
| OpenAPI Specs | `sdks/*.yaml` | Machine-readable specs |
| Interactive Docs | http://localhost:8000/docs | Live API testing |

---

## 🎯 Documentation by Task

### Setting Up for First Time

1. **Read overview** → [README.md](README.md)
2. **Follow setup** → [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md)
3. **Configure mapper** → [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md)
4. **Install SDK** → [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md)
5. **Run examples** → [sdks/python/examples/README.md](sdks/python/examples/README.md)

### Deploying to Production

1. **Read architecture** → [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Choose deployment** → [modules/mapper/INSTALLATION_GUIDE.md](modules/mapper/INSTALLATION_GUIDE.md)
3. **Configure for cloud** → [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) (AWS/Azure/GCP sections)
4. **Deploy modules** → `deployment/aws/` or `deployment/azure/` or `deployment/gcp/`

### Integrating into Your App

1. **Understand API** → [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md)
2. **Choose SDK** → [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md) or [sdks/typescript/README.md](sdks/typescript/README.md)
3. **Review examples** → [sdks/python/examples/](sdks/python/examples/)
4. **Test integration** → [sdks/python/examples/test_connection.py](sdks/python/examples/test_connection.py)

### Troubleshooting Issues

1. **Check quick reference** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (Troubleshooting section)
2. **Review setup guide** → [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) (Troubleshooting section)
3. **Check module logs** → See [modules/mapper/README.md](modules/mapper/README.md) (Logging section)
4. **Search issues** → [GitHub Issues](https://github.com/Engineersmind/pdf-autofillr/issues)

### Understanding the Code

1. **Architecture overview** → [ARCHITECTURE.md](ARCHITECTURE.md)
2. **Module structure** → [modules/mapper/README.md](modules/mapper/README.md)
3. **Code organization** → [rough_docs/ARCHITECTURE_SUMMARY_FINAL.md](rough_docs/ARCHITECTURE_SUMMARY_FINAL.md)
4. **API design** → [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md)

---

## 📖 Documentation by Module

### Mapper Module (Core Engine)

| Document | Purpose |
|----------|---------|
| [modules/mapper/README.md](modules/mapper/README.md) | Module overview and structure |
| [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) | **Configuration and setup** |
| [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md) | **REST API reference** |
| [modules/mapper/INSTALLATION_GUIDE.md](modules/mapper/INSTALLATION_GUIDE.md) | Deployment options |
| [modules/mapper/config.ini.example](modules/mapper/config.ini.example) | Configuration template |
| [modules/mapper/.env.example](modules/mapper/.env.example) | Environment variables template |

**Start here:** [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md)

### Chatbot Module

| Document | Purpose |
|----------|---------|
| [rough_docs/MODULE_chatbot_lambda.md](rough_docs/MODULE_chatbot_lambda.md) | Complete module documentation |

**Status:** 🚧 Documentation exists, code migration in progress

### RAG Module

| Document | Purpose |
|----------|---------|
| [rough_docs/MODULE_rag_lambda.md](rough_docs/MODULE_rag_lambda.md) | Module documentation |

**Status:** 🚧 Documentation exists, code migration in progress

### PDF Upload Module

| Document | Purpose |
|----------|---------|
| [rough_docs/MODULE_pdf_upload_lambda.md](rough_docs/MODULE_pdf_upload_lambda.md) | Module documentation |

**Status:** 🚧 Documentation exists, code migration in progress

---

## 🛠️ SDK Documentation

### Python SDK

| Document | Purpose |
|----------|---------|
| [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md) | **Quick start guide** |
| [sdks/python/README.md](sdks/python/README.md) | SDK overview |
| [sdks/python/examples/README.md](sdks/python/examples/README.md) | **Example scripts** |
| [sdks/python/.env.example](sdks/python/.env.example) | Configuration template |
| [sdks/python/config.json.example](sdks/python/config.json.example) | Alternative config format |

**Start here:** [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md)

**Example scripts:**
- [test_connection.py](sdks/python/examples/test_connection.py) - Test SDK connection
- [example_with_config.py](sdks/python/examples/example_with_config.py) - Full example
- [basic_usage.py](sdks/python/examples/basic_usage.py) - Basic operations
- [context_manager.py](sdks/python/examples/context_manager.py) - Advanced usage

### TypeScript SDK

| Document | Purpose |
|----------|---------|
| [sdks/typescript/README.md](sdks/typescript/README.md) | SDK documentation |

**Status:** 📝 Coming soon

---

## 🗂️ Additional Resources

### Architecture & Design

- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete system architecture
- [rough_docs/ARCHITECTURE_SUMMARY_FINAL.md](rough_docs/ARCHITECTURE_SUMMARY_FINAL.md) - Legacy architecture docs
- [rough_docs/DUAL_MAPPER_FILE_FLOW.md](rough_docs/DUAL_MAPPER_FILE_FLOW.md) - Dual mapper design

### API Specifications

- [sdks/openapi-mapper.yaml](sdks/openapi-mapper.yaml) - Mapper API spec
- [sdks/openapi-chatbot.yaml](sdks/openapi-chatbot.yaml) - Chatbot API spec
- [sdks/openapi-rag.yaml](sdks/openapi-rag.yaml) - RAG API spec
- [sdks/openapi-orchestrator.yaml](sdks/openapi-orchestrator.yaml) - Orchestrator API spec

### Development Guides

- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community guidelines
- [rough_docs/CORRECT_REPO_STRUCTURE.md](rough_docs/CORRECT_REPO_STRUCTURE.md) - Repository structure

### Legacy Documentation

- [rough_docs/](rough_docs/) - Working documents and module details
- [rough_docs/DOCUMENTATION_SUMMARY.md](rough_docs/DOCUMENTATION_SUMMARY.md) - Documentation summary

---

## 🔍 Quick Find

| I need to... | Go to... |
|--------------|----------|
| **Set up the system** | [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md) |
| **Configure mapper module** | [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) |
| **Use Python SDK** | [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md) |
| **See API endpoints** | [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md) |
| **Run examples** | [sdks/python/examples/README.md](sdks/python/examples/README.md) |
| **Understand architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Deploy to AWS** | [modules/mapper/INSTALLATION_GUIDE.md](modules/mapper/INSTALLATION_GUIDE.md) |
| **Troubleshoot** | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| **See quick commands** | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| **Understand chatbot** | [rough_docs/MODULE_chatbot_lambda.md](rough_docs/MODULE_chatbot_lambda.md) |

---

## 📞 Need Help?

1. **Check documentation** - Use this index to find relevant docs
2. **Review examples** - See [sdks/python/examples/](sdks/python/examples/)
3. **Read troubleshooting** - See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
4. **Search issues** - [GitHub Issues](https://github.com/Engineersmind/pdf-autofillr/issues)
5. **Ask questions** - [GitHub Discussions](https://github.com/Engineersmind/pdf-autofillr/discussions)

---

## 🗺️ Recommended Learning Path

### For End Users (Using SDK)

1. [README.md](README.md) - Understand what PDF Autofillr does
2. [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md) - Set up mapper module
3. [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md) - Install and use SDK
4. [sdks/python/examples/README.md](sdks/python/examples/README.md) - Try examples
5. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Keep as reference

### For Developers (Integrating)

1. [README.md](README.md) - Overview
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand design
3. [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md) - Study API
4. [sdks/python/QUICKSTART.md](sdks/python/QUICKSTART.md) - Use SDK
5. [sdks/python/examples/](sdks/python/examples/) - Review code examples

### For System Administrators (Deploying)

1. [README.md](README.md) - Overview
2. [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
3. [modules/mapper/SETUP_GUIDE.md](modules/mapper/SETUP_GUIDE.md) - Configuration
4. [modules/mapper/INSTALLATION_GUIDE.md](modules/mapper/INSTALLATION_GUIDE.md) - Deployment
5. [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md) - Complete process

### For Contributors (Contributing Code)

1. [README.md](README.md) - Project overview
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture
3. [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
4. [rough_docs/ARCHITECTURE_SUMMARY_FINAL.md](rough_docs/ARCHITECTURE_SUMMARY_FINAL.md) - Code structure
5. Module-specific documentation in [modules/](modules/)

---

## 📊 Documentation Status

| Module/SDK | Documentation Status | Completeness |
|------------|---------------------|--------------|
| **Mapper Module** | ✅ Complete | 100% |
| **Python SDK** | ✅ Complete | 100% |
| **Setup Guides** | ✅ Complete | 100% |
| **API Reference** | ✅ Complete | 100% |
| **Architecture** | ✅ Complete | 95% |
| **Chatbot Module** | 🚧 Partial | 70% (needs migration) |
| **RAG Module** | 🚧 Partial | 60% (needs migration) |
| **Upload Module** | 🚧 Partial | 50% (needs migration) |
| **TypeScript SDK** | 📝 Planned | 0% |
| **Web Dashboard** | 📝 Planned | 0% |

---

## 🔄 Documentation Updates

This documentation is actively maintained. Last major update: March 2026

To request documentation improvements:
- Open an issue: [GitHub Issues](https://github.com/Engineersmind/pdf-autofillr/issues)
- Submit a PR: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Quick Start: [COMPLETE_SETUP_FLOW.md](COMPLETE_SETUP_FLOW.md)**
