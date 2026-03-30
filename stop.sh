#!/bin/bash
# ============================================================================
# PDF Autofillr - Stop Server Script (Mac/Linux)
# ============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Stopping PDF Autofillr Server...${NC}"

# Kill API server processes
pkill -f "api_server.py" || pkill -f "uvicorn.*api_server"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Server stopped${NC}"
else
    echo -e "${GREEN}✅ No server processes found${NC}"
fi
