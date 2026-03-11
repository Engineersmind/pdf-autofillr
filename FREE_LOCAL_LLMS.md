# 🆓 Free Local LLM Options for PDF Autofillr

## Overview

You don't need expensive API keys! Here are **completely free** ways to run PDF Autofillr locally using open-source models.

---

## ✅ Option 1: Ollama (Recommended - Easiest)

### What is Ollama?
- **100% Free** - No API keys, no costs
- **Runs Locally** - Full privacy, your data never leaves your machine
- **Easy to Use** - One-command installation
- **Good Quality** - Models like Llama 3.1, Mistral, Qwen are surprisingly good

### Installation

**Windows:**
```powershell
# Option 1: Windows installer
# Download from: https://ollama.ai/download

# Option 2: winget
winget install Ollama.Ollama
```

**Mac:**
```bash
# Option 1: Homebrew (recommended)
brew install ollama

# Option 2: Download installer
# https://ollama.ai/download
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Recommended Models

```bash
# Best overall (7B - Fast, good quality)
ollama pull llama3.1

# Better quality (70B - Slower, excellent quality)
ollama pull llama3.1:70b

# Fast and efficient
ollama pull mistral

# Great for technical/code tasks
ollama pull qwen2.5

# Latest reasoning model
ollama pull deepseek-r1:7b
```

### Configure PDF Autofillr for Ollama

Edit `modules/mapper/.env`:
```bash
CLOUD_PROVIDER=local
LLM_MODEL=ollama/llama3.1
OLLAMA_API_BASE=http://localhost:11434
```

**Pro Tip:** Our setup script does this automatically when you choose option 1!

---

## ✅ Option 2: LM Studio (Alternative - GUI-based)

### What is LM Studio?
- **Free Desktop App** with nice GUI
- **Download models easily** from Hugging Face
- **No technical setup** needed
- **Works on Windows/Mac/Linux**

### Installation

1. Download from: https://lmstudio.ai/
2. Install and open LM Studio
3. Search and download a model (e.g., "Llama 3.1")
4. Start the local server (button in UI)

### Configure PDF Autofillr for LM Studio

Edit `modules/mapper/.env`:
```bash
CLOUD_PROVIDER=local
LLM_MODEL=local/llama-3.1-8b  # or whatever model you downloaded
# LM Studio runs on port 1234 by default
OPENAI_API_BASE=http://localhost:1234/v1
```

---

## ✅ Option 3: LocalAI (Advanced - Docker)

### What is LocalAI?
- **Docker-based** local LLM server
- **OpenAI-compatible API**
- **Multiple model support**

### Quick Start

```bash
# Using Docker
docker run -p 8080:8080 \
  -v $PWD/models:/models \
  localai/localai:latest

# Download a model
curl http://localhost:8080/models/apply \
  -H "Content-Type: application/json" \
  -d '{"id": "TheBloke/Llama-2-7B-Chat-GGUF"}'
```

### Configure PDF Autofillr

Edit `modules/mapper/.env`:
```bash
CLOUD_PROVIDER=local
LLM_MODEL=gpt-3.5-turbo  # LocalAI mimics OpenAI
OPENAI_API_BASE=http://localhost:8080/v1
```

---

## 📊 Comparison: Free Local Options

| Feature | Ollama | LM Studio | LocalAI |
|---------|--------|-----------|---------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Setup Time** | 2 minutes | 5 minutes | 10 minutes |
| **GUI** | ❌ CLI only | ✅ Nice GUI | ❌ CLI only |
| **Auto-setup** | ✅ Our script | ❌ Manual | ❌ Manual |
| **Model Selection** | 50+ models | 100+ models | 100+ models |
| **Performance** | Excellent | Excellent | Good |
| **Best For** | Developers | Non-technical users | Docker users |

---

## 🎯 Recommended Model by Use Case

### For Development/Testing
```bash
ollama pull llama3.1          # Fast, 7B params
# or
ollama pull mistral           # Even faster
```

### For Production Quality
```bash
ollama pull llama3.1:70b      # Slower, but much better
# or
ollama pull qwen2.5:32b       # Good balance
```

### For Technical/Code-Heavy PDFs
```bash
ollama pull qwen2.5           # Best for technical content
```

### For Reasoning-Heavy Tasks
```bash
ollama pull deepseek-r1:7b    # Good at complex reasoning
```

---

## ⚡ Performance Comparison

### Speed (Fields per second)

| Model | Size | Speed | Quality | RAM Needed |
|-------|------|-------|---------|------------|
| **llama3.1** | 7B | ⚡⚡⚡⚡ Fast | ★★★ Good | 8 GB |
| **llama3.1:70b** | 70B | ⚡ Slow | ★★★★★ Excellent | 48 GB |
| **mistral** | 7B | ⚡⚡⚡⚡⚡ Very Fast | ★★★ Good | 8 GB |
| **qwen2.5** | 7B | ⚡⚡⚡⚡ Fast | ★★★★ Great | 8 GB |
| **deepseek-r1:7b** | 7B | ⚡⚡⚡ Medium | ★★★★ Great | 8 GB |

### Cost Comparison

| Option | Setup Cost | Runtime Cost | Total Cost |
|--------|------------|--------------|------------|
| **Ollama (Local)** | $0 | $0 (electricity ~$0.01/hr) | **$0** |
| **LM Studio (Local)** | $0 | $0 (electricity ~$0.01/hr) | **$0** |
| **OpenAI API** | $0 | $0.01-0.03 per PDF | **$10-30/month** |
| **Claude API** | $0 | $0.01-0.03 per PDF | **$10-30/month** |

---

## 🔧 How to Switch Between Models

### Using Ollama - Switch Models Easily

```bash
# Download new model
ollama pull qwen2.5

# Edit .env
nano modules/mapper/.env

# Change this line:
LLM_MODEL=ollama/qwen2.5

# Restart server
./stop.sh
./start.sh
```

### Test Different Models

```bash
# Test with llama3.1 (fast)
LLM_MODEL=ollama/llama3.1 ./start.sh

# Test with qwen2.5 (technical)
LLM_MODEL=ollama/qwen2.5 ./start.sh

# Test with mistral (fastest)
LLM_MODEL=ollama/mistral ./start.sh
```

---

## 🆚 Local vs Cloud APIs

### When to Use Local (Free)
✅ Development and testing  
✅ Privacy-sensitive data  
✅ High volume (1000+ PDFs)  
✅ No budget for APIs  
✅ Learning and experimenting  

### When to Use Cloud APIs (Paid)
✅ Production with SLA requirements  
✅ Need absolute best quality  
✅ Low volume (< 100 PDFs/month)  
✅ Don't want to manage infrastructure  
✅ Need 24/7 reliability  

---

## 💡 Pro Tips for Free Local Setup

### 1. Start Small, Scale Up
```bash
# Start with small model
ollama pull llama3.1

# If quality isn't good enough, upgrade
ollama pull llama3.1:70b
```

### 2. Use GPU if Available
Ollama automatically uses your GPU if available:
- **NVIDIA GPU:** 10-50x faster
- **Apple Silicon (M1/M2/M3):** 5-20x faster
- **CPU only:** Still works, just slower

### 3. Combine Free + Paid
```bash
# Development: Free Ollama
LLM_MODEL=ollama/llama3.1

# Production: Paid OpenAI
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

### 4. Use Smaller Models for Extraction, Bigger for Mapping
Our system can use different models for different tasks (coming soon!)

---

## 🚀 Quick Start with Free Setup

**Complete free setup in 3 commands:**

```bash
# 1. Install Ollama
brew install ollama  # Mac
# or: winget install Ollama.Ollama  # Windows

# 2. Pull a model
ollama pull llama3.1

# 3. Run setup script (choose option 1)
./setup.sh
```

**Or use our automated setup:**
```bash
./setup.sh
# Choose: 1 (Virtual environment)
# Choose: 1 (Ollama)
# Done! 100% free setup
```

---

## 🎓 FAQ

### Q: Which free option is best?
**A:** Ollama. It's the easiest to set up, best integrated with our scripts, and has excellent model selection.

### Q: Will free models work well?
**A:** Yes! Llama 3.1 and Qwen 2.5 are surprisingly good for form filling. For 90% of use cases, they're perfectly adequate.

### Q: How much slower is local vs cloud?
**A:** On modern hardware with GPU:
- Local (GPU): 2-5 seconds per PDF
- Cloud API: 1-3 seconds per PDF

Not much difference!

### Q: Can I use multiple free models?
**A:** Yes! Download multiple with Ollama and switch between them:
```bash
ollama pull llama3.1
ollama pull mistral
ollama pull qwen2.5

# Switch in .env as needed
```

### Q: What if I run out of RAM?
**A:** Use smaller models:
- 7B models: Need ~8 GB RAM
- 13B models: Need ~16 GB RAM
- 70B models: Need ~48 GB RAM

Most laptops can run 7B models fine!

---

## 📖 Related Documentation

- [Setup Guide](GETTING_STARTED.md)
- [Commands Reference](COMMANDS.md)
- [Troubleshooting](SETUP_IMPROVEMENTS.md)

---

## 🎉 Summary

**Best Free Option:** Ollama with Llama 3.1
- ✅ $0 cost forever
- ✅ 2-minute setup
- ✅ Good quality
- ✅ Full privacy
- ✅ Auto-configured by our scripts

**Run this to get started:**
```bash
./setup.sh  # Choose option 1 for both prompts
./start.sh
```

**You're ready to process PDFs for FREE!** 🚀
