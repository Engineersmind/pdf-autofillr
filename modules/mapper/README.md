# PDF Mapper Module

Platform-agnostic PDF field extraction, mapping, embedding, and filling engine.

## 🎯 Features

- **Extract**: Extract PDF form fields using PyMuPDF
- **Map**: Map fields using semantic LLM, RAG, headers, or ensemble
- **Embed**: Embed metadata into PDFs using Java iText
- **Fill**: Fill PDF forms with data

## 📦 Installation

### Core (Platform-Agnostic)
```bash
pip install -e .
# OR
pip install -r requirements.txt
```

### With AWS Support
```bash
pip install -e .[aws]
# OR
pip install -r requirements-aws.txt
```

### With Azure Support
```bash
pip install -e .[azure]
# OR
pip install -r requirements-azure.txt
```

### With GCP Support
```bash
pip install -e .[gcp]
# OR
pip install -r requirements-gcp.txt
```

## 🚀 Usage

### Entry Points

- **AWS Lambda**: `entrypoints/aws_lambda.py`
- **Azure Functions**: `entrypoints/azure_function.py` (Coming soon)
- **GCP Functions**: `entrypoints/gcp_function.py` (Coming soon)
- **FastAPI**: `entrypoints/fastapi_app.py` (Coming soon)
- **CLI**: `entrypoints/cli.py` (Coming soon)

### Operations Supported

1. **make_embed_file** - Extract + Map + Embed
2. **check_embed_file** - Check if PDF has embedded metadata
3. **fill_pdf** - Fill PDF with data

## 🧪 Testing

```bash
pytest tests/
```

## 📝 Environment Variables

See `.env.example` for required environment variables.

## 📂 Structure

```
mapper/
├── src/                    # Core business logic (platform-independent)
│   ├── extractors/         # PDF field extraction
│   ├── mappers/            # Semantic, RAG, headers, ensemble mappers
│   ├── headers/            # Headers extractor
│   ├── fillers/            # PDF filling with Java iText
│   ├── embedders/          # Metadata embedding with Java iText
│   ├── handlers/           # Operation handlers
│   ├── core/               # Config, logger
│   ├── utils/              # Utilities
│   └── models/             # Data models
│
├── entrypoints/            # Platform-specific entry points
│   ├── aws_lambda.py       # AWS Lambda handler
│   ├── azure_function.py   # Azure Functions handler (coming soon)
│   ├── gcp_function.py     # GCP Functions handler (coming soon)
│   ├── fastapi_app.py      # FastAPI REST API (coming soon)
│   └── cli.py              # CLI tool (coming soon)
│
├── tests/                  # Unit tests
├── setup.py                # Package setup
├── requirements.txt        # Core dependencies (no cloud!)
├── requirements-aws.txt    # AWS-specific dependencies
├── requirements-azure.txt  # Azure-specific dependencies
├── requirements-gcp.txt    # GCP-specific dependencies
├── README.md               # This file
└── .env.example            # Environment variables template
```

## 🔑 Key Design Principles

1. **Platform-Agnostic Core**: `src/` has NO cloud provider dependencies
2. **Cloud-Specific Entry Points**: `entrypoints/` wraps core logic for each platform
3. **Separation of Concerns**: Business logic is independent of infrastructure
4. **Easy Testing**: Core logic can be tested without cloud setup
5. **Deploy Anywhere**: Same code works on AWS, Azure, GCP, Docker, K8s

## 🌟 Benefits

- ✅ **Multi-Cloud Ready**: Deploy to AWS, Azure, GCP with minimal changes
- ✅ **Test Locally**: No cloud dependencies in core logic
- ✅ **Smaller Builds**: Install only what you need per platform
- ✅ **Easy Migration**: Switch clouds by changing entry point only
- ✅ **Better Mocking**: Test without real cloud services
