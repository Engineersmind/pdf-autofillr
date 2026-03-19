#!/bin/bash
# Run Mapper Docker container locally using .env file for secrets

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting Mapper Docker (Local)${NC}"
echo "=================================="

IMAGE_NAME="${IMAGE_NAME:-pdf-mapper:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-mapper}"
PORT="${PORT:-8000}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MODULE_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
REPO_ROOT="$( cd "$MODULE_ROOT/../.." && pwd )"

# Check image exists
if ! docker images "$IMAGE_NAME" --format "{{.Repository}}:{{.Tag}}" | grep -q "$IMAGE_NAME"; then
    echo -e "${RED}❌ Image $IMAGE_NAME not found. Build it first: ./docker-build.sh${NC}"
    exit 1
fi

# Check .env exists
if [ ! -f "$MODULE_ROOT/.env" ]; then
    echo -e "${RED}❌ .env not found at $MODULE_ROOT/.env${NC}"
    echo -e "${YELLOW}Copy the example: cp $MODULE_ROOT/.env.example $MODULE_ROOT/.env${NC}"
    exit 1
fi

# Sample data directory (used for local testing)
DATA_DIR="${DATA_DIR:-$REPO_ROOT/data/modules/mapper_sample}"
if [ ! -d "$DATA_DIR" ]; then
    echo -e "${YELLOW}⚠️  Sample data not found at $DATA_DIR${NC}"
    echo -e "${YELLOW}   Set DATA_DIR=<path> to use a different directory${NC}"
fi

# Stop existing container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}⚠️  Stopping existing container...${NC}"
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1 || true
    docker rm   "$CONTAINER_NAME" > /dev/null 2>&1 || true
fi

echo -e "${YELLOW}🚀 Starting container...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8000" \
    --env-file "$MODULE_ROOT/.env" \
    -v "$DATA_DIR:/app/data" \
    "$IMAGE_NAME"

echo -e "${GREEN}✅ Container started${NC}"

# Wait for ready
echo -e "${YELLOW}⏳ Waiting for service...${NC}"
for i in {1..15}; do
    if curl -f -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service is ready!${NC}"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${RED}❌ Service failed to start${NC}"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  API:      http://localhost:$PORT"
echo -e "  Docs:     http://localhost:$PORT/docs"
echo -e "  Data:     $DATA_DIR → /app/data${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Quick test:${NC}"
echo ""
echo "  # 1. Health check"
echo "  curl http://localhost:$PORT/health"
echo ""
echo "  # 2. Embed PDF template (run once per form)"
echo "  #    Input files must be at: {input_base_path}/{user_id}/{session_id}/{pdf_doc_id}/"
cat << 'EOF'
  curl -X POST http://localhost:8000/mapper/make-embed-file \
    -H "Content-Type: application/json" \
    -d '{"user_id": "1", "session_id": "1", "pdf_doc_id": "100"}'
EOF
echo ""
echo "  # 3. Fill form (run once per user)"
cat << 'EOF'
  curl -X POST http://localhost:8000/mapper/fill \
    -H "Content-Type: application/json" \
    -d '{"user_id": "1", "session_id": "1", "pdf_doc_id": "100"}'
EOF
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  docker logs -f $CONTAINER_NAME"
echo "  docker stop $CONTAINER_NAME"
echo "  docker exec -it $CONTAINER_NAME /bin/bash"
echo ""
