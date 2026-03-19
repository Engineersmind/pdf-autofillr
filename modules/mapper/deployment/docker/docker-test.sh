#!/bin/bash
# Test Mapper Docker image: health, make_embed_file, and fill

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🧪 Testing Mapper Docker Image${NC}"
echo "================================"

IMAGE_NAME="${IMAGE_NAME:-pdf-mapper:latest}"
PORT="${PORT:-8001}"
CONTAINER_NAME="mapper-test-$$"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MODULE_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
REPO_ROOT="$( cd "$MODULE_ROOT/../.." && pwd )"

# Test IDs — files must be at {input_base_path}/{USER_ID}/{SESSION_ID}/{PDF_DOC_ID}/
USER_ID="1"
SESSION_ID="1"
PDF_DOC_ID="100"
DATA_DIR="${DATA_DIR:-$REPO_ROOT/data/modules/mapper_sample}"

# Helpers
pass() { echo -e "${GREEN}  ✅ $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; cleanup; exit 1; }

cleanup() {
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1 || true
    docker rm   "$CONTAINER_NAME" > /dev/null 2>&1 || true
}
trap cleanup EXIT

# Pre-flight checks
if ! docker images "$IMAGE_NAME" --format "{{.Repository}}:{{.Tag}}" | grep -q "$IMAGE_NAME"; then
    echo -e "${RED}❌ Image $IMAGE_NAME not found. Build it first: ./docker-build.sh${NC}"
    exit 1
fi

if [ ! -f "$MODULE_ROOT/.env" ]; then
    echo -e "${RED}❌ .env not found at $MODULE_ROOT/.env${NC}"
    exit 1
fi

if [ ! -d "$DATA_DIR" ]; then
    echo -e "${RED}❌ Sample data not found at $DATA_DIR${NC}"
    echo -e "${YELLOW}   Set DATA_DIR=<path> to use a different directory${NC}"
    exit 1
fi

echo -e "${YELLOW}Starting container on port $PORT...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8000" \
    --env-file "$MODULE_ROOT/.env" \
    -v "$DATA_DIR:/app/data" \
    "$IMAGE_NAME" > /dev/null

# Wait for ready
echo -e "${YELLOW}Waiting for service...${NC}"
for i in {1..20}; do
    if curl -f -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        break
    fi
    if [ $i -eq 20 ]; then
        echo -e "${RED}❌ Service failed to start${NC}"
        docker logs "$CONTAINER_NAME" 2>&1 | tail -20
        exit 1
    fi
    sleep 1
done
pass "Service is up"

BASE_URL="http://localhost:$PORT"

# ── Test 1: Health ─────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[1/3] Health check${NC}"
HEALTH=$(curl -s "$BASE_URL/health")
echo "  Response: $HEALTH"
echo "$HEALTH" | grep -q "ok\|healthy\|status" && pass "Health check passed" || fail "Health check failed"

# ── Test 2: make_embed_file ────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/3] POST /mapper/make-embed-file${NC}"
EMBED_RESPONSE=$(curl -s -X POST "$BASE_URL/mapper/make-embed-file" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$USER_ID\", \"session_id\": \"$SESSION_ID\", \"pdf_doc_id\": \"$PDF_DOC_ID\"}")

echo "  Response: $EMBED_RESPONSE"

if echo "$EMBED_RESPONSE" | grep -q '"error"\|"detail"'; then
    fail "make_embed_file: error in response"
fi
pass "make_embed_file succeeded"

# ── Test 3: fill ───────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/3] POST /mapper/fill${NC}"
FILL_RESPONSE=$(curl -s -X POST "$BASE_URL/mapper/fill" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$USER_ID\", \"session_id\": \"$SESSION_ID\", \"pdf_doc_id\": \"$PDF_DOC_ID\"}")

echo "  Response: $FILL_RESPONSE"

if echo "$FILL_RESPONSE" | grep -q '"error"\|"detail"'; then
    fail "fill: error in response"
fi
pass "fill succeeded"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}🎉 All tests passed!${NC}"
