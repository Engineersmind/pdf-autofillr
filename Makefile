# ============================================================================
# PDF Autofillr - Makefile (Cross-platform commands)
# ============================================================================
# Easy-to-use commands for common operations
# Works on Windows (via Git Bash/WSL), Mac, and Linux

.PHONY: help setup start stop clean test install dev health check-deps

# Default target
help:
	@echo "📖 PDF Autofillr - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make setup       - Complete automated setup"
	@echo "  make start       - Start the API server"
	@echo "  make dev         - Start server in dev mode (auto-reload)"
	@echo ""
	@echo "🔧 Management:"
	@echo "  make stop        - Stop the server"
	@echo "  make restart     - Restart the server"
	@echo "  make health      - Check server health"
	@echo ""
	@echo "📦 Installation:"
	@echo "  make install     - Install dependencies only"
	@echo "  make install-sdk - Install Python SDK"
	@echo "  make clean       - Clean cache and temp files"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test        - Run tests"
	@echo "  make check-deps  - Check if dependencies are installed"
	@echo ""
	@echo "🤖 Ollama:"
	@echo "  make ollama-setup    - Install and setup Ollama"
	@echo "  make ollama-start    - Start Ollama service"
	@echo "  make ollama-models   - List installed models"
	@echo ""

# ============================================================================
# Setup & Installation
# ============================================================================

setup:
	@echo "🚀 Running automated setup..."
	@if [ -f setup.sh ]; then \
		chmod +x setup.sh start.sh stop.sh && ./setup.sh; \
	elif [ -f setup.ps1 ]; then \
		pwsh -File setup.ps1; \
	else \
		echo "❌ Setup script not found"; exit 1; \
	fi

install:
	@echo "📦 Installing dependencies..."
	@cd modules/mapper && pip install -r requirements.txt -r requirements-api.txt

install-sdk:
	@echo "🔧 Installing Python SDK..."
	@cd sdks/python && pip install -e .

check-deps:
	@echo "🔍 Checking dependencies..."
	@command -v python >/dev/null 2>&1 || { echo "❌ Python not installed"; exit 1; }
	@command -v pip >/dev/null 2>&1 || { echo "❌ pip not installed"; exit 1; }
	@echo "✅ All core dependencies found"

# ============================================================================
# Server Management
# ============================================================================

start:
	@echo "🌐 Starting server..."
	@if [ -f start.sh ]; then \
		chmod +x start.sh && ./start.sh; \
	elif [ -f start.ps1 ]; then \
		pwsh -File start.ps1; \
	else \
		cd modules/mapper && python api_server.py; \
	fi

dev:
	@echo "🔧 Starting development server (auto-reload)..."
	@cd modules/mapper && uvicorn api_server:app --reload --host 0.0.0.0 --port 8000

stop:
	@echo "🛑 Stopping server..."
	@pkill -f "api_server.py" || pkill -f "uvicorn.*api_server" || echo "No server running"

restart: stop start

health:
	@echo "🏥 Checking server health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Server not responding"

# ============================================================================
# Ollama Management
# ============================================================================

ollama-setup:
	@echo "🤖 Setting up Ollama..."
	@if command -v ollama >/dev/null 2>&1; then \
		echo "✅ Ollama already installed"; \
		ollama pull llama3.1; \
	else \
		echo "📥 Please install Ollama from https://ollama.ai/download"; \
		open https://ollama.ai/download; \
	fi

ollama-start:
	@echo "🚀 Starting Ollama..."
	@ollama serve &

ollama-models:
	@echo "📋 Installed Ollama models:"
	@ollama list

# ============================================================================
# Testing & Development
# ============================================================================

test:
	@echo "🧪 Running tests..."
	@cd modules/mapper && python -m pytest tests/ -v

test-config:
	@echo "🔧 Testing configuration..."
	@cd modules/mapper && python test_config.py

# ============================================================================
# Cleanup
# ============================================================================

clean:
	@echo "🧹 Cleaning cache and temporary files..."
	@rm -rf data/modules/mapper_sample/tmp/*
	@rm -rf modules/mapper/__pycache__
	@rm -rf modules/mapper/src/__pycache__
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "🧹 Deep cleaning (including cache)..."
	@rm -rf data/modules/mapper_sample/cache/*
	@rm -rf data/modules/mapper_sample/output/*
	@echo "✅ Deep cleanup complete"

# ============================================================================
# Docker (Optional)
# ============================================================================

docker-build:
	@echo "🐳 Building Docker image..."
	@cd modules/mapper && docker build -t pdf-autofiller-mapper .

docker-run:
	@echo "🐳 Running Docker container..."
	@cd modules/mapper && docker run -p 8000:8000 pdf-autofiller-mapper

# ============================================================================
# Utilities
# ============================================================================

logs:
	@echo "📜 Showing server logs..."
	@tail -f logs/server.log || echo "No log file found"

env-check:
	@echo "🔍 Environment check:"
	@echo "  Python: $$(python --version)"
	@echo "  pip: $$(pip --version)"
	@if command -v ollama >/dev/null 2>&1; then echo "  Ollama: $$(ollama --version)"; fi
	@echo ""
	@echo "📁 Directory structure:"
	@ls -la modules/mapper/.env 2>/dev/null && echo "  ✅ .env exists" || echo "  ❌ .env missing"
	@ls -la modules/mapper/config.ini 2>/dev/null && echo "  ✅ config.ini exists" || echo "  ❌ config.ini missing"
