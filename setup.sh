#!/bin/bash
# ============================================================================
# PDF Autofillr - Automated Setup Script (Mac/Linux)
# ============================================================================
# This script automatically sets up the entire project on Mac/Linux
# Usage: ./setup.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default model
MODEL="${1:-llama3.1}"
SKIP_OLLAMA="${SKIP_OLLAMA:-false}"

echo -e "${CYAN}🚀 PDF Autofillr - Automated Setup${NC}"
echo -e "${CYAN}==================================${NC}\n"

# ============================================================================
# 1. Check Prerequisites
# ============================================================================
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
    PYTHON_VERSION=$(python --version)
    echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python not found. Please install Python 3.8+${NC}"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    PIP_CMD=pip3
elif command -v pip &> /dev/null; then
    PIP_CMD=pip
else
    echo -e "${RED}❌ pip not found. Please install pip.${NC}"
    exit 1
fi

PIP_VERSION=$($PIP_CMD --version)
echo -e "${GREEN}✅ pip found: $PIP_VERSION${NC}"

# ============================================================================
# 2. Virtual Environment Setup (Recommended)
# ============================================================================
if [ "$SKIP_VENV" != "true" ]; then
    echo -e "\n${YELLOW}🔧 Virtual Environment Setup${NC}"
    
    # Check if venv already exists
    if [ -d "venv" ]; then
        echo -e "${GREEN}✅ Virtual environment already exists${NC}"
        echo -e "${NC}   Options:${NC}"
        echo -e "${NC}   1. Use existing virtual environment (recommended)${NC}"
        echo -e "${NC}   2. Delete and recreate${NC}"
        echo -e "${NC}   3. Skip (use global Python)${NC}"
        
        read -p "   Enter choice (1-3) [1]: " -n 1 -r
        echo
        VENV_CHOICE="${REPLY:-1}"
        
        if [[ $VENV_CHOICE == "2" ]]; then
            echo -e "${YELLOW}📦 Deleting old virtual environment...${NC}"
            rm -rf venv
            echo -e "${YELLOW}📦 Creating new virtual environment...${NC}"
            $PYTHON_CMD -m venv venv
        elif [[ $VENV_CHOICE == "3" ]]; then
            echo -e "${YELLOW}⏭️  Skipping virtual environment${NC}"
            VENV_CHOICE="skip"
        fi
    else
        echo -e "${NC}   Virtual environments isolate dependencies (recommended)${NC}"
        echo -e "${NC}   Options:${NC}"
        echo -e "${NC}   1. Create new virtual environment (recommended)${NC}"
        echo -e "${NC}   2. Skip (use global Python)${NC}"
        
        read -p "   Enter choice (1 or 2) [1]: " -n 1 -r
        echo
        VENV_CHOICE="${REPLY:-1}"
        
        if [[ $VENV_CHOICE == "1" ]]; then
            echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
            $PYTHON_CMD -m venv venv
        else
            echo -e "${YELLOW}⏭️  Skipping virtual environment${NC}"
            VENV_CHOICE="skip"
        fi
    fi
    
    # Activate venv if not skipped
    if [[ $VENV_CHOICE != "skip" ]] && [ -d "venv" ]; then
        # Activate venv
        if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
            # Git Bash on Windows
            source venv/Scripts/activate 2>/dev/null || . venv/Scripts/activate
        else
            # Mac/Linux
            source venv/bin/activate
        fi
        
        # Update pip silently
        $PYTHON_CMD -m pip install --upgrade pip -q 2>/dev/null || true
        PIP_CMD="pip"
        
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
        echo -e "${YELLOW}   Note: Reactivate later with 'source venv/bin/activate' (Mac/Linux)${NC}"
        echo -e "${YELLOW}         or 'venv\\Scripts\\activate' (Windows)${NC}"
    fi
fi

# ============================================================================
# 3. Setup Ollama (Optional)
# ============================================================================
if [ "$SKIP_OLLAMA" != "true" ]; then
    echo -e "\n${YELLOW}🤖 LLM Provider Setup${NC}"
    echo -e "${NC}   Choose your AI provider:${NC}"
    echo -e "${NC}   1. Ollama (Free, local, open-source - recommended for development)${NC}"
    echo -e "${NC}   2. OpenAI (Paid API, best quality)${NC}"
    echo -e "${NC}   3. Claude/Anthropic (Paid API, excellent quality)${NC}"
    echo -e "${NC}   4. Skip (configure manually later)${NC}"
    
    read -p "   Enter choice (1-4) [1]: " -n 1 -r
    echo
    LLM_CHOICE="${REPLY:-1}"
    
    if [[ $LLM_CHOICE == "1" ]]; then
        echo -e "${YELLOW}🤖 Setting up Ollama (Open Source LLM)...${NC}"
        
        if command -v ollama &> /dev/null; then
        OLLAMA_VERSION=$(ollama --version)
        echo -e "${GREEN}✅ Ollama found: $OLLAMA_VERSION${NC}"
        
        # Pull the model
        echo -e "${YELLOW}📥 Pulling model: $MODEL...${NC}"
        ollama pull $MODEL
            echo -e "${YELLOW}⚠️  Please install Ollama and run this script again.${NC}"
            echo -e "${YELLOW}   Or choose option 2 or 3 for cloud LLM providers.${NC}"
            exit 0
        fi
    elif [[ $LLM_CHOICE == "2" ]]; then
        echo -e "${YELLOW}🔑 OpenAI Setup${NC}"
        echo -e "${NC}   You'll need an OpenAI API key from: https://platform.openai.com/api-keys${NC}"
        read -p "   Enter your OpenAI API key (or press Enter to skip): " OPENAI_KEY
        
        if [ -n "$OPENAI_KEY" ]; then
            MODEL="gpt-4o"
            echo -e "${GREEN}✅ OpenAI configured with model: $MODEL${NC}"
        else
            echo -e "${YELLOW}⚠️  No API key provided. Update modules/mapper/.env manually.${NC}"
            MODEL="gpt-4o"
        fi
    elif [[ $LLM_CHOICE == "3" ]]; then
        echo -e "${YELLOW}🔑 Claude/Anthropic Setup${NC}"
        echo -e "${NC}   You'll need an Anthropic API key from: https://console.anthropic.com/${NC}"
        read -p "   Enter your Anthropic API key (or press Enter to skip): " ANTHROPIC_KEY
        
        if [ -n "$ANTHROPIC_KEY" ]; then
            MODEL="claude-3-5-sonnet-20241022"
            echo -e "${GREEN}✅ Claude configured with model: $MODEL${NC}"
        else
  4         echo -e "${YELLOW}⚠️  No API key provided. Update modules/mapper/.env manually.${NC}"
            MODEL="claude-3-5-sonnet-20241022"
        fi
    else
        echo -e "${YELLOW}⏭️  Skipping LLM setup - you'll need to configure manually${NC}"
        SKIP_OLLAMA=true
        MODEL="gpt-4o"
    fi
else
    echo -e "\n${YELLOW}⏭️  Skipping LLM setup${NC}"
    MODEL="gpt-4o"
    echo -e "\n${YELLOW}⏭️  Skipping Ollama setup${NC}"
fi

# ============================================================================
# 3. Create Directory Structure
# ============================================================================
echo -e "\n${YELLOW}📁 Creating directory structure...${NC}"

mkdir -p data/modules/mapper_sample/{cache,input,output,tmp,rag-data}
echo -e "${GREEN}✅ Directories created${NC}"

# ============================================================================
# 5. Configure Mapper Module
# ============================================================================
echo -e "\n${YELLOW}⚙️  Configuring mapper module...${NC}"

cd modules/mapper

# Create .env based on LLM choice
if [[ $LLM_CHOICE == "1" ]]; then
    # Ollama configuration
    cat > .env << EOF
# PDF Mapper Module - Environment Variables
# Auto-generated by setup script

CLOUD_PROVIDER=local

# LLM Configuration - Using Ollama (Open Source)
LLM_MODEL=ollama/$MODEL
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3

# Ollama Configuration
OLLAMA_API_BASE=http://localhost:11434

# Logging
LOG_LEVEL=INFO
EOF
elif [[ $LLM_CHOICE == "2" ]]; then
    # OpenAI configuration
    cat > .env << EOF
# PDF Mapper Module - Environment Variables
# Auto-generated by setup script

CLOUD_PROVIDER=local

# 6LM Configuration - Using OpenAI
LLM_MODEL=$MODEL
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3

# OpenAI API Key
OPENAI_API_KEY=${OPENAI_KEY:-your-openai-api-key-here}

# Logging
LOG_LEVEL=INFO
EOF
elif [[ $LLM_CHOICE == "3" ]]; then
    # Claude configuration
    cat > .env << EOF
# PDF Mapper Module - Environment Variables
# Auto-generated by setup script

CLOUD_PROVIDER=local

# LLM Configuration - Using Claude/Anthropic
LLM_MODEL=$MODEL
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3

# Anthropic API Key
ANTHROPIC_API_KEY=${ANTHROPIC_KEY:-your-anthropic-api-key-here}

# 8ogging
LOG_LEVEL=INFO
EOF
else
    # Default/manual configuration
    cat > .env << EOF
# PDF Mapper Module - Environment Variables
# Auto-generated by setup script - REQUIRES MANUAL CONFIGURATION

CLOUD_PROVIDER=local

# LLM Configuration - UPDATE THIS!
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3

# Add your API key here:
# For OpenAI:
# OPENAI_API_KEY=sk-your-key-here

# For Claude:
# ANTHROPIC_API_KEY=sk-ant-your-key-here

# For Ollama (local):
# LLM_MODEL=ollama/llama3.1
# OL[ $VENV_CHOICE == "1" ]]; then
    echo -e "\n${CYAN}💡 Virtual Environment:${NC}"
    echo -e "   ${NC}To reactivate later, run:${NC}"
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo -e "      ${YELLOW}source venv/Scripts/activate${NC} (Git Bash)"
        echo -e "      ${YELLOW}venv\\Scripts\\activate${NC} (PowerShell)"
    else
        echo -e "      ${YELLOW}source venv/bin/activate${NC}"
    fi
fi

if [[ $LLM_CHOICE == "2" ]] && [ -z "$OPENAI_KEY" ]; then
    echo -e "\n${YELLOW}⚠️  Remember: Add your OpenAI API key${NC}"
    echo -e "   ${YELLOW}Edit modules/mapper/.env and add: OPENAI_API_KEY=sk-...${NC}"
elif [[ $LLM_CHOICE == "3" ]] && [ -z "$ANTHROPIC_KEY" ]; then
    echo -e "\n${YELLOW}⚠️  Remember: Add your Anthropic API key${NC}"
    echo -e "   ${YELLOW}Edit modules/mapper/.env and add: ANTHROPIC_API_KEY=sk-ant-...${NC}"
elif [ "$SKIP_OLLAMA" = "true" ]; then
    echo -e "\n${YELLOW}⚠️  Remember: You skipped LLM setup.${NC}"
    echo -e "   ${YELLOW}Update modules/mapper/.env with your
LOG_LEVEL=INFO
EOF
fi

echo -e "${GREEN}✅ .env file configured${NC}"

# ============================================================================
# 5. Install Python Dependencies
# ============================================================================
echo -e "\n${YELLOW}📦 Installing Python dependencies...${NC}"

echo -e "   ${NC}Installing core requirements...${NC}"
$PIP_CMD install -r requirements.txt -q

echo -e "   ${NC}Installing API server requirements...${NC}"
$PIP_CMD install -r requirements-api.txt -q

echo -e "${GREEN}✅ Dependencies installed${NC}"

# ============================================================================
# 6. Install SDK (Optional)
# ============================================================================
echo -e "\n${YELLOW}🔧 Installing Python SDK...${NC}"
cd ../../sdks/python

# Create SDK .env
cat > .env << EOF
# PDF Autofiller SDK Configuration
PDF_AUTOFILLER_API_URL=http://localhost:8000
PDF_AUTOFILLER_API_KEY=
PDF_AUTOFILLER_USER_ID=1
PDF_AUTOFILLER_PDF_DOC_ID=100
EOF

$PIP_CMD install -e . -q
echo -e "${GREEN}✅ SDK installed${NC}"

# ============================================================================
# 7. Test Configuration
# ============================================================================
cd ../..
echo -e "\n${YELLOW}🧪 Testing configuration...${NC}"

if $PYTHON_CMD -c "from modules.mapper.src.core.config import GlobalConfig; print('Config loaded successfully')" 2>/dev/null; then
    echo -e "${GREEN}✅ Configuration valid${NC}"
else
    echo -e "${YELLOW}⚠️  Configuration test failed (non-critical)${NC}"
fi

# ============================================================================
# Setup Complete
# ============================================================================
echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"

echo -e "\n${CYAN}📝 Next Steps:${NC}"
echo -e "   ${NC}1. Start the server:${NC}"
echo -e "      ${YELLOW}./start.sh${NC}"
echo -e "\n   ${NC}2. Or manually:${NC}"
echo -e "      ${YELLOW}cd modules/mapper${NC}"
echo -e "      ${YELLOW}python api_server.py${NC}"
echo -e "\n   ${NC}3. Test the API:${NC}"
echo -e "      ${YELLOW}curl http://localhost:8000/health${NC}"

if [ "$SKIP_OLLAMA" = "true" ]; then
    echo -e "\n${YELLOW}⚠️  Remember: You skipped Ollama setup.${NC}"
    echo -e "   ${YELLOW}Update modules/mapper/.env with your OpenAI API key${NC}"
fi

echo -e "\n${CYAN}📖 Documentation:${NC}"
echo -e "   ${NC}- Setup Guide: modules/mapper/SETUP_GUIDE.md${NC}"
echo -e "   ${NC}- Quick Ref: QUICK_REFERENCE.md${NC}"
echo -e "   ${NC}- Examples: examples/QUICK_START.md${NC}"

echo -e "\n${GREEN}🎉 Happy coding!${NC}"
