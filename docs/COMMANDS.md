# 🎯 Command Reference - PDF Autofillr

Quick reference for all available commands across different platforms.

---

## 🚀 Setup & Start Commands

### Windows (PowerShell)

```powershell
# One-time setup
.\setup.ps1

# Start server
.\start.ps1

# Start in dev mode (auto-reload)
.\start.ps1 -Dev

# Stop server
.\stop.ps1

# Custom port
.\start.ps1 -Port 8080
```

### Mac/Linux (Bash)

```bash
# Make scripts executable (first time only)
chmod +x setup.sh start.sh stop.sh

# One-time setup
./setup.sh

# Start server
./start.sh

# Start in dev mode
./start.sh --dev

# Stop server
./stop.sh

# Custom port
./start.sh --port 8080

# Skip Ollama during setup
SKIP_OLLAMA=true ./setup.sh
```

### Using Make (Cross-Platform)

```bash
# Setup
make setup

# Start server
make start

# Development mode (auto-reload)
make dev

# Stop server
make stop

# Restart server
make restart

# Check server health
make health

# View all commands
make help
```

### Using npm/package.json (Cross-Platform)

```bash
# Setup
npm run setup

# Start server
npm start

# Development mode
npm run dev

# Stop server
npm run stop

# Run tests
npm test

# Install dependencies
npm run install

# Install SDK
npm run install-sdk

# Check health
npm run health
```

---

## 🤖 Ollama Management

### Windows

```powershell
# Check if installed
ollama --version

# List installed models
ollama list

# Pull a model
ollama pull llama3.1
ollama pull llama3.1:70b
ollama pull mistral
ollama pull qwen2.5

# Remove a model
ollama rm llama3.1

# Start Ollama (if not auto-started)
Start-Process ollama -ArgumentList "serve"
```

### Mac/Linux

```bash
# Check if installed
ollama --version

# List installed models
ollama list

# Pull a model
ollama pull llama3.1
ollama pull llama3.1:70b
ollama pull mistral
ollama pull qwen2.5

# Remove a model
ollama rm llama3.1

# Start Ollama service
ollama serve &

# Mac: Use Homebrew services
brew services start ollama
brew services stop ollama
brew services restart ollama
```

### Using Make

```bash
# Setup Ollama and pull default model
make ollama-setup

# Start Ollama service
make ollama-start

# List installed models
make ollama-models
```

---

## 📦 Installation Commands

### Dependencies

```bash
# Windows PowerShell
cd modules/mapper
pip install -r requirements.txt
pip install -r requirements-api.txt

# Mac/Linux
cd modules/mapper
pip3 install -r requirements.txt
pip3 install -r requirements-api.txt

# Using Make
make install
```

### SDK Installation

```bash
# Windows PowerShell
cd sdks/python
pip install -e .

# Mac/Linux
cd sdks/python
pip3 install -e .

# Using Make
make install-sdk

# Using npm
npm run install-sdk
```

---

## 🧪 Testing Commands

### Run Tests

```bash
# Windows PowerShell
cd modules/mapper
python -m pytest tests/ -v

# Mac/Linux
cd modules/mapper
python3 -m pytest tests/ -v

# Using Make
make test

# Using npm
npm test
```

### Test Configuration

```bash
# Windows PowerShell
cd modules/mapper
python test_config.py

# Mac/Linux
cd modules/mapper
python3 test_config.py

# Using Make
make test-config
```

### Health Check

```bash
# All platforms
curl http://localhost:8000/health

# PowerShell alternative
Invoke-RestMethod http://localhost:8000/health

# Using Make
make health

# Using npm
npm run health
```

---

## 🧹 Cleanup Commands

### Clean Temp Files

```bash
# Using Make
make clean

# Windows PowerShell
Remove-Item -Recurse -Force data/modules/mapper_sample/tmp/*
Remove-Item -Recurse -Force modules/mapper/__pycache__

# Mac/Linux
rm -rf data/modules/mapper_sample/tmp/*
rm -rf modules/mapper/__pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### Deep Clean (Including Cache)

```bash
# Using Make
make clean-all

# Manual
rm -rf data/modules/mapper_sample/cache/*
rm -rf data/modules/mapper_sample/output/*
```

---

## 🐳 Docker Commands (Optional)

### Build & Run

```bash
# Using Make
make docker-build
make docker-run

# Using npm
npm run docker:build
npm run docker:run

# Manual - Windows/Mac/Linux
cd modules/mapper
docker build -t pdf-autofiller-mapper .
docker run -p 8000:8000 pdf-autofiller-mapper

# Run with local Ollama
docker run -p 8000:8000 \
  -e OLLAMA_API_BASE=http://host.docker.internal:11434 \
  pdf-autofiller-mapper
```

---

## 🔧 Configuration Commands

### Switch Models

```bash
# Edit .env file
# Windows
notepad modules/mapper/.env

# Mac/Linux
nano modules/mapper/.env
# or
vim modules/mapper/.env

# Change LLM_MODEL to:
# - ollama/llama3.1 (default)
# - ollama/llama3.1:70b (better quality)
# - ollama/mistral (faster)
# - gpt-4o (requires OPENAI_API_KEY)
# - claude-3-5-sonnet-20241022 (requires ANTHROPIC_API_KEY)
```

### Environment Check

```bash
# Using Make
make env-check

# Manual
python --version
pip --version
ollama --version

# Check if .env exists
ls -la modules/mapper/.env

# Check if config.ini exists
ls -la modules/mapper/config.ini
```

---

## 📊 Usage Examples

### Using Python SDK

```python
from pdf_autofiller import PDFMapperClient

# Initialize client
client = PDFMapperClient(api_url="http://localhost:8000")

# Extract fields
result = client.extract(
    pdf_path="form.pdf",
    user_id=1,
    pdf_doc_id=100
)

# Create embedded PDF
embedded = client.make_embed_file(
    pdf_path="form.pdf",
    user_id=1,
    pdf_doc_id=100
)

# Fill PDF
filled = client.fill_pdf(
    embedded_pdf_path=embedded['embedded_pdf_path'],
    input_json_path="data.json",
    user_id=1,
    pdf_doc_id=100
)
```

### Using CLI

```bash
# Extract fields
pdf-autofiller --api-url http://localhost:8000 extract form.pdf

# Create embedded PDF
pdf-autofiller --api-url http://localhost:8000 make-embed form.pdf

# Fill PDF
pdf-autofiller --api-url http://localhost:8000 fill embedded.pdf data.json

# With custom output path
pdf-autofiller --api-url http://localhost:8000 extract form.pdf --output ./output/
```

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Extract fields
curl -X POST http://localhost:8000/mapper/extract \
  -F "file=@form.pdf" \
  -F "user_id=1" \
  -F "pdf_doc_id=100"

# Map fields
curl -X POST http://localhost:8000/mapper/map \
  -F "file=@form.pdf" \
  -F "user_id=1" \
  -F "pdf_doc_id=100"

# Fill PDF
curl -X POST http://localhost:8000/mapper/fill \
  -F "file=@embedded.pdf" \
  -F "input_json=@data.json" \
  -F "user_id=1" \
  -F "pdf_doc_id=100"
```

---

## 🔍 Debugging Commands

### Check Logs

```bash
# Windows PowerShell
Get-Content logs/server.log -Tail 50
Get-Content logs/server.log -Wait  # Follow logs

# Mac/Linux
tail -f logs/server.log
tail -n 50 logs/server.log

# Using Make
make logs
```

### Check Running Processes

```bash
# Windows PowerShell
Get-Process | Where-Object {$_.ProcessName -eq "python"}

# Mac/Linux
ps aux | grep python
ps aux | grep api_server

# Check what's using port 8000
# Windows
netstat -ano | findstr :8000

# Mac/Linux
lsof -i :8000
```

---

## 🎯 Quick Troubleshooting

### Port Already in Use

```bash
# Find and kill process on port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:8000 | xargs kill -9
```

### Ollama Not Running

```bash
# Start Ollama
# Windows: Click Ollama in system tray
# Mac
brew services start ollama
# Linux
systemctl start ollama
# Or manually
ollama serve
```

### Dependencies Issues

```bash
# Reinstall all dependencies
make install

# Or manually
cd modules/mapper
pip install --upgrade -r requirements.txt
pip install --upgrade -r requirements-api.txt
```

---

## 📱 Platform-Specific Notes

### Windows
- Use PowerShell (not CMD)
- Scripts: `.\setup.ps1`, `.\start.ps1`, `.\stop.ps1`
- Make: Install via Chocolatey: `choco install make`

### Mac
- Prefer Homebrew for Ollama: `brew install ollama`
- Scripts require execute permission: `chmod +x *.sh`
- Use `python3` and `pip3` explicitly

### Linux
- May need to install make: `sudo apt install make` or `sudo yum install make`
- Scripts require execute permission: `chmod +x *.sh`
- Ollama install: `curl -fsSL https://ollama.ai/install.sh | sh`

### WSL (Windows Subsystem for Linux)
- Use Linux commands
- Can access Windows Ollama via `host.docker.internal:11434`

---

## 🎓 Learning Path

1. ✅ **Setup:** Run `./setup.sh` or `.\setup.ps1`
2. ✅ **Start:** Run `./start.sh` or `.\start.ps1`
3. ✅ **Test:** Run `curl http://localhost:8000/health`
4. 📖 **Learn:** Read [GETTING_STARTED.md](GETTING_STARTED.md)
5. 🧪 **Experiment:** Try [examples/QUICK_START.md](examples/QUICK_START.md)
6. 🚀 **Build:** Use the SDK in your project

---

**Pro Tip:** Use `make` commands for the simplest cross-platform experience! 🎉
