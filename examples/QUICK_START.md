# Quick Start - Using Mapper Module Locally

## 🎯 Three Ways to Use Mapper Module

### 1. **Direct Python Import** (Programmatic)
### 2. **API Server** (HTTP Endpoints)
### 3. **Docker** (Containerized)

---

## 1️⃣ Direct Python Import

### Setup:

```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr

# Install dependencies
cd modules/mapper
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=sk-your-key-here

# Configure for local use
cp config.ini.example config.ini
# Edit config.ini → set source_type = local
```

### Usage:

**Simple Example**:
```python
import sys
sys.path.insert(0, "modules/mapper/src")

from orchestrator import PDFAutofiller
from configs.factory import ConfigFactory

# Create config
config = ConfigFactory.create_config(source_type="local")

# Initialize
autofiller = PDFAutofiller(config)

# Process PDF
result = autofiller.process_pdf(
    pdf_path="data/modules/mapper_sample/input/small_4page.pdf",
    input_json_path="data/modules/mapper_sample/form_keys_flat.json",
    user_id="test_user",
    pdf_doc_id="test_001"
)

print(f"✅ Filled PDF: {result['filled_pdf_path']}")
```

**Run the example**:
```bash
python examples/mapper_direct_usage.py
```

### Main Functions:

```python
# Full orchestration (all steps)
autofiller.process_pdf(pdf_path, input_json_path, user_id, pdf_doc_id)

# Individual steps:
from extractors.fitz_extract_lines import FitzExtractor
from mappers.semantic_mapper import SemanticMapper
from fillers.pdf_filler import PDFFiller

extractor = FitzExtractor()
fields = extractor.extract(pdf_path)

mapper = SemanticMapper()
mappings = mapper.map(fields, input_data)

filler = PDFFiller()
filler.fill(input_pdf, mappings, output_path)
```

---

## 2️⃣ API Server (Recommended for Local Development)

### Start Server:

```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr/modules/mapper

# Install API dependencies
pip install fastapi uvicorn python-multipart

# Set environment
export OPENAI_API_KEY=sk-your-key-here

# Start server
python -m uvicorn api_server:app --reload --port 8000
```

**Server will start at**: `http://localhost:8000`

### View API Docs:

Open in browser:
- **Interactive docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

### Usage:

**1. Health Check**:
```bash
curl http://localhost:8000/health
```

**2. Extract Fields Only**:
```bash
curl -X POST http://localhost:8000/extract \
  -F "pdf=@data/modules/mapper_sample/input/small_4page.pdf"
```

**3. Map and Fill PDF**:
```bash
curl -X POST http://localhost:8000/map \
  -F "pdf=@data/modules/mapper_sample/input/small_4page.pdf" \
  -F "user_data={\"name\":\"John Doe\",\"email\":\"john@example.com\"}" \
  -F "user_id=test_user" \
  -F "pdf_doc_id=sample_001"
```

**4. Using Python**:
```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Map PDF
files = {"pdf": open("path/to/file.pdf", "rb")}
data = {
    "user_data": '{"name": "John Doe"}',
    "user_id": "test_user"
}
response = requests.post("http://localhost:8000/map", files=files, data=data)
result = response.json()
print(f"Filled PDF: {result['filled_pdf_path']}")
```

**Run the example**:
```bash
# Make sure server is running, then:
python examples/mapper_api_usage.py
```

---

## 3️⃣ Docker (Portable)

### Build Image:

```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr/modules/mapper

# Build
./docker-build.sh

# Or manually
docker build -t pdf-mapper:latest .
```

### Run Container:

```bash
docker run -p 8000:8000 \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/../../data:/data \
  pdf-mapper:latest
```

### Usage:

Same as API server (endpoints available at `http://localhost:8000`)

---

## 📊 API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check server health |
| `/extract` | POST | Extract fields from PDF |
| `/map` | POST | Map and fill PDF |
| `/docs` | GET | Interactive API documentation |
| `/redoc` | GET | Alternative API docs |

### `/map` Endpoint (Main Function):

**Parameters**:
- `pdf` (file): PDF file to process
- `user_data` (string, optional): JSON string with user data
- `input_json_path` (string, optional): Path to input JSON file
- `user_id` (string, default: "default_user"): User identifier
- `pdf_doc_id` (string, optional): PDF document identifier

**Response**:
```json
{
  "status": "success",
  "filled_pdf_path": "/path/to/filled.pdf",
  "mapping_path": "/path/to/mapping.json",
  "extraction_path": "/path/to/extraction.json",
  "fields_mapped": 42,
  "processing_time": 12.5
}
```

---

## 🔧 Configuration

### Environment Variables:

```bash
# Required
export OPENAI_API_KEY=sk-your-key-here

# Optional
export SOURCE_TYPE=local                    # local, aws, azure, gcp
export LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR
export LLM_MODEL=gpt-4o                     # LLM model to use
export LLM_TEMPERATURE=0.05                 # LLM temperature (0.0-1.0)
```

### Config File (`config.ini`):

```ini
[general]
source_type = local
pdf_cache_enabled = true

[mapping]
llm_model = gpt-4o
llm_temperature = 0.05
use_second_mapper = true

[local]
cache_registry_path = /path/to/cache/hash_registry.json
output_base_path = /path/to/output
local_input_pdf = /path/to/input.pdf
```

---

## 📁 File Paths

### Input Files:
```
data/modules/mapper_sample/
├── input/
│   └── small_4page.pdf          # Sample PDF
└── form_keys_flat.json          # Sample input data
```

### Output Files (Auto-Generated):
```
data/modules/mapper_sample/output/users/{user_id}/pdfs/{pdf_doc_id}/
├── extraction/
│   └── {filename}_extracted.json      # Extracted fields
├── mapping/
│   └── {filename}_mapped.json         # Field mappings
├── embedding/
│   └── {filename}_embedded.pdf        # PDF with QR/barcodes
└── filling/
    └── {filename}_filled.pdf          # Final filled PDF
```

---

## 🧪 Quick Test

### Test 1: Direct Import

```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr

python << 'EOF'
import sys
sys.path.insert(0, "modules/mapper/src")
from orchestrator import PDFAutofiller
from configs.factory import ConfigFactory

config = ConfigFactory.create_config(source_type="local")
autofiller = PDFAutofiller(config)
result = autofiller.process_pdf(
    pdf_path="data/modules/mapper_sample/input/small_4page.pdf",
    input_json_path="data/modules/mapper_sample/form_keys_flat.json",
    user_id="test",
    pdf_doc_id="quick_test"
)
print(f"✅ Success! Output: {result['filled_pdf_path']}")
EOF
```

### Test 2: API Server

```bash
# Terminal 1: Start server
cd modules/mapper
python -m uvicorn api_server:app --reload

# Terminal 2: Test endpoints
curl http://localhost:8000/health

curl -X POST http://localhost:8000/map \
  -F "pdf=@../../data/modules/mapper_sample/input/small_4page.pdf" \
  -F "user_id=test"
```

### Test 3: Docker

```bash
cd modules/mapper

# Build and run
./docker-build.sh
docker run -p 8000:8000 \
  -e SOURCE_TYPE=local \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  pdf-mapper:latest

# Test
curl http://localhost:8000/health
```

---

## 🐛 Troubleshooting

### Issue: Import errors

```bash
# Add mapper to Python path
export PYTHONPATH="${PYTHONPATH}:/Users/raghava/Documents/EMC/pdf-autofillr/modules/mapper/src"

# Or in Python:
import sys
sys.path.insert(0, "/Users/raghava/Documents/EMC/pdf-autofillr/modules/mapper/src")
```

### Issue: API server not starting

```bash
# Check if port is in use
lsof -ti:8000

# Kill process using port
kill -9 $(lsof -ti:8000)

# Restart server
python -m uvicorn api_server:app --reload --port 8000
```

### Issue: Missing dependencies

```bash
cd modules/mapper
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart
```

### Issue: OpenAI API errors

```bash
# Verify API key
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## 📚 Next Steps

1. **Try the examples**:
   ```bash
   python examples/mapper_direct_usage.py
   python examples/mapper_api_usage.py
   ```

2. **Explore API docs**:
   - Start server: `cd modules/mapper && python -m uvicorn api_server:app --reload`
   - Open: http://localhost:8000/docs

3. **Read documentation**:
   - [Module README](../modules/mapper/README.md)
   - [API Server Guide](../modules/mapper/API_SERVER.md)
   - [Setup Guide](../modules/mapper/SETUP_GUIDE.md)

4. **Deploy to cloud**:
   - [AWS Deployment](../deployment/aws/mapper/README.md)
   - [Docker Guide](../modules/mapper/DOCKER.md)

---

## 💡 Tips

- **Development**: Use API server (auto-reload with `--reload`)
- **Testing**: Use direct imports (easier debugging)
- **Production**: Use Docker (consistent environment)
- **Integration**: Use SDK/CLI (coming soon)

---

## 🆘 Support

If you encounter issues:
1. Check logs: `tail -f logs/mapper.log`
2. Enable debug: `export LOG_LEVEL=DEBUG`
3. Review documentation
4. Open GitHub issue
