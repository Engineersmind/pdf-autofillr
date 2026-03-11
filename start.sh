#!/bin/bash
# ============================================================================
# PDF Autofillr - Start Server Script (Mac/Linux)
# ============================================================================
# Usage: ./start.sh [--dev] [--port PORT]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default values
PORT=8000
DEV_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./start.sh [--dev] [--port PORT]"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}🚀 Starting PDF Autofillr Server...${NC}"
echo -e "${CYAN}==================================${NC}\n"

# Check if Ollama is running (if using Ollama)
if [ -f "modules/mapper/.env" ]; then
    if grep -q "LLM_MODEL=ollama/" modules/mapper/.env; then
        echo -e "${YELLOW}🤖 Checking Ollama...${NC}"
        if command -v ollama &> /dev/null; then
            if ollama list &> /dev/null; then
                echo -e "${GREEN}✅ Ollama is running${NC}"
            else
                echo -e "${YELLOW}⚠️  Starting Ollama...${NC}"
                # Try to start Ollama
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    open -a Ollama 2>/dev/null || ollama serve &
                else
                    ollama serve &
                fi
                sleep 2
            fi
        else
            echo -e "${YELLOW}⚠️  Ollama not found, but your config requires it!${NC}"
            echo -e "${NC}   Your .env is configured to use: LLM_MODEL=ollama/...${NC}"
            echo -e "${NC}   Options:${NC}"
            echo -e "${NC}   1. Install Ollama now (recommended)${NC}"
            echo -e "${NC}   2. Skip and start anyway (server may fail)${NC}"
            echo -e "${NC}   3. Cancel and configure a different LLM${NC}"
            
            read -p "   Enter choice (1-3) [1]: " -n 1 -r
            echo
            OLLAMA_CHOICE="${REPLY:-1}"
            
            if [[ $OLLAMA_CHOICE == "1" ]]; then
                echo -e "${YELLOW}📥 Installing Ollama...${NC}"
                
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    echo -e "${NC}   Mac detected. Options:${NC}"
                    echo -e "${NC}   a) Install via Homebrew: brew install ollama${NC}"
                    echo -e "${NC}   b) Download from: https://ollama.ai/download${NC}"
                    
                    if command -v brew &> /dev/null; then
                        read -p "   Install with Homebrew? (y/n): " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            brew install ollama
                            echo -e "${GREEN}✅ Ollama installed!${NC}"
                            echo -e "${YELLOW}📥 Pulling default model...${NC}"
                            ollama pull llama3.1
                            echo -e "${GREEN}✅ Ready!${NC}"
                        else
                            echo -e "${YELLOW}Opening download page...${NC}"
                            open https://ollama.ai/download
                            echo -e "${YELLOW}⚠️  Please install Ollama and run ./start.sh again${NC}"
                            exit 0
                        fi
                    else
                        echo -e "${YELLOW}Opening download page...${NC}"
                        open https://ollama.ai/download
                        echo -e "${YELLOW}⚠️  Please install Ollama and run ./start.sh again${NC}"
                        exit 0
                    fi
                elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
                    echo -e "${NC}   Installing Ollama for Linux...${NC}"
                    curl -fsSL https://ollama.ai/install.sh | sh
                    echo -e "${GREEN}✅ Ollama installed!${NC}"
                    echo -e "${YELLOW}📥 Pulling default model...${NC}"
                    ollama pull llama3.1
                    echo -e "${GREEN}✅ Ready!${NC}"
                else
                    echo -e "${YELLOW}Download from: https://ollama.ai/download${NC}"
                    echo -e "${YELLOW}⚠️  Please install Ollama and run ./start.sh again${NC}"
                    exit 0
                fi
            elif [[ $OLLAMA_CHOICE == "2" ]]; then
                echo -e "${YELLOW}⚠️  Continuing without Ollama - server will likely fail!${NC}"
                echo -e "${YELLOW}   The server expects Ollama at http://localhost:11434${NC}"
            else
                echo -e "${CYAN}To use a different LLM provider:${NC}"
                echo -e "${NC}   1. Edit modules/mapper/.env${NC}"
                echo -e "${NC}   2. Change LLM_MODEL to:${NC}"
                echo -e "${NC}      - gpt-4o (requires OPENAI_API_KEY)${NC}"
                echo -e "${NC}      - claude-3-5-sonnet-20241022 (requires ANTHROPIC_API_KEY)${NC}"
                echo -e "${NC}   3. Add the corresponding API key${NC}"
                echo -e "${NC}   4. Run ./start.sh again${NC}"
                exit 0
            fi
        fi
    fi
fi

# Navigate to mapper module
cd modules/mapper

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

# Start server
echo -e "\n${CYAN}🌐 Starting API server on http://localhost:$PORT...${NC}"

if [ "$DEV_MODE" = true ]; then
    echo -e "   ${NC}(Development mode with auto-reload)${NC}"
    export PYTHONPATH=.
    uvicorn api_server:app --reload --host 0.0.0.0 --port $PORT
else
    $PYTHON_CMD api_server.py
fi
