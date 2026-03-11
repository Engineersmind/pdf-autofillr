# 🚀 Getting Started - PDF Autofillr

**Quick setup guide for running PDF Autofillr locally with open-source models**

---

## ⚡ Fastest Way to Start (1 Command!)

### Windows (PowerShell):
```powershell
.\setup.ps1
.\start.ps1
```

### Mac/Linux:
```bash
chmod +x setup.sh start.sh
./setup.sh
./start.sh
```

### Using Make (Cross-Platform):
```bash
make setup
make start
```

That's it! The server will be running on **http://localhost:8000** 🎉

---

## 📋 What Gets Automatically Set Up

✅ **Ollama** - Free, local open-source LLM (Llama 3.1)  
✅ **Python dependencies** - All required packages  
✅ **Directory structure** - Cache, input, output folders  
✅ **Configuration files** - .env and config.ini  
✅ **Python SDK** - Client library for easy usage  

---

## 🛠 Manual Setup (If You Prefer)

### 1. Install Ollama

**Windows:**
```powershell
# Download from: https://ollama.ai/download
# Or use winget:
winget install Ollama.Ollama

# Pull the model
ollama pull llama3.1
```

**Mac:**
```bash
brew install ollama
ollama pull llama3.1
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.1
```

### 2. Clone & Setup

```bash
cd pdf-autofillr

# Install dependencies
cd modules/mapper
pip install -r requirements.txt
pip install -r requirements-api.txt

# Configure environment
cp .env.example .env
# Edit .env and set: LLM_MODEL=ollama/llama3.1
```

### 3. Start Server

```bash
python api_server.py
```

---

## 🎯 Quick Commands Reference

| Command | Description |
|---------|-------------|
| `make setup` | Complete automated setup |
| `make start` | Start the API server |
| `make dev` | Start with auto-reload |
| `make stop` | Stop the server |
| `make health` | Check server status |
| `make test` | Run tests |
| `make clean` | Clean cache files |
| `make ollama-models` | List installed models |

**Windows users:** Use `.\setup.ps1`, `.\start.ps1` or install Make via Chocolatey:
```powershell
choco install make
```

---

## 🧪 Test the API

Once the server is running:

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 📖 Usage Examples

### Using Python SDK:

```python
from pdf_autofiller import PDFMapperClient

# Connect to local server
client = PDFMapperClient(api_url="http://localhost:8000")

# Extract fields from PDF
result = client.extract(
    pdf_path="form.pdf",
    user_id=1,
    pdf_doc_id=100
)

print(f"Found {len(result['fields'])} fields")
```

### Using CLI:

```bash
# Extract fields
pdf-autofiller --api-url http://localhost:8000 extract form.pdf

# Complete pipeline (extract + map + embed)
pdf-autofiller --api-url http://localhost:8000 make-embed form.pdf

# Fill PDF with data
pdf-autofiller --api-url http://localhost:8000 fill embedded.pdf data.json
```

### Using REST API:

```bash
# Extract fields
curl -X POST http://localhost:8000/mapper/extract \
  -F "file=@form.pdf" \
  -F "user_id=1" \
  -F "pdf_doc_id=100"
```

---

## 🔧 Configuration Options

### Using Different Models

Edit `modules/mapper/.env`:

```bash
# Use different Ollama models:
LLM_MODEL=ollama/llama3.1          # Default (7B params)
LLM_MODEL=ollama/llama3.1:70b      # Larger model (better quality)
LLM_MODEL=ollama/mistral           # Fast and efficient
LLM_MODEL=ollama/qwen2.5           # Good for technical docs
LLM_MODEL=ollama/deepseek-r1:7b    # Reasoning-focused

# Or use OpenAI (requires API key):
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key-here

# Or use Claude (requires API key):
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Available Ollama Models

```bash
# List installed models
ollama list

# Pull new models
ollama pull llama3.1:70b
ollama pull mistral
ollama pull qwen2.5
ollama pull deepseek-r1:7b
```

---

## 🐛 Troubleshooting

### Server won't start?

1. **Check if Ollama is running:**
   ```bash
   ollama list
   ```

2. **Check Python version:**
   ```bash
   python --version  # Should be 3.8+
   ```

3. **Check dependencies:**
   ```bash
   make check-deps
   ```

### Server starts but API fails?

1. **Check configuration:**
   ```bash
   make env-check
   ```

2. **Test configuration:**
   ```bash
   cd modules/mapper
   python test_config.py
   ```

3. **Check logs:**
   ```bash
   # Windows
   Get-Content logs/server.log -Tail 50
   
   # Mac/Linux
   tail -f logs/server.log
   ```

### Ollama errors?

1. **Ensure model is downloaded:**
   ```bash
   ollama pull llama3.1
   ```

2. **Restart Ollama:**
   ```bash
   # Mac
   brew services restart ollama
   
   # Linux
   systemctl restart ollama
   
   # Windows - restart from system tray
   ```

---

## 🔄 Different Deployment Options

### Option 1: Local with Ollama (Free) ✅ **Recommended for Development**
- **Cost:** Free
- **Setup:** This guide
- **Performance:** Good for testing

### Option 2: Local with OpenAI API
- **Cost:** Pay per API call
- **Setup:** Add `OPENAI_API_KEY` to `.env`
- **Performance:** Excellent

### Option 3: Docker
```bash
make docker-build
make docker-run
```

### Option 4: Cloud Deployment
See [deployment/DEPLOYMENT_PLAN.md](deployment/DEPLOYMENT_PLAN.md) for AWS/Azure/GCP options.

---

## 📚 Next Steps

1. ✅ **You are here** - Server is running!
2. 📖 **Read examples:** [examples/QUICK_START.md](examples/QUICK_START.md)
3. 🧪 **Try the SDK:** [sdks/python/README.md](sdks/python/README.md)
4. 🔍 **API Reference:** [modules/mapper/API_SERVER.md](modules/mapper/API_SERVER.md)
5. 🏗️ **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 💡 Pro Tips

- **Use Make commands** for the easiest experience across all platforms
- **Start with smaller models** (llama3.1) for faster responses during development
- **Enable auto-reload** during development: `make dev`
- **Check health endpoint** to verify server is running: `curl localhost:8000/health`
- **Use the SDK** instead of raw API calls for cleaner code

---

## 🆘 Need Help?

- 📖 **Documentation:** [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
- 🐛 **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/your-repo/discussions)
- 📧 **Security:** Support@pdffillr.ai

---

## ⚡ TL;DR - One-Line Setup

```bash
# Mac/Linux/WSL
curl -fsSL https://raw.githubusercontent.com/your-repo/main/setup.sh | bash && ./start.sh

# Windows PowerShell
irm https://raw.githubusercontent.com/your-repo/main/setup.ps1 | iex; .\start.ps1
```

🎉 **Happy PDF Autofilling!**
