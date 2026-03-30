#!/bin/bash

# =============================================================================
# SDK Generation Script
# =============================================================================
# Generates client SDKs from OpenAPI specifications using OpenAPI Generator
#
# Prerequisites:
#   - OpenAPI Generator CLI installed
#   - Java 11+ (required by OpenAPI Generator)
#
# Install OpenAPI Generator:
#   npm install @openapitools/openapi-generator-cli -g
#   # OR
#   brew install openapi-generator

set -e

echo "========================================="
echo "PDF Autofiller SDK Generation"
echo "========================================="
echo ""

# Check if openapi-generator is installed
if ! command -v openapi-generator &> /dev/null; then
    echo "❌ Error: openapi-generator not found"
    echo ""
    echo "Install with:"
    echo "  npm install @openapitools/openapi-generator-cli -g"
    echo "  OR"
    echo "  brew install openapi-generator"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to sdks directory
cd "$(dirname "$0")"

echo "Current directory: $(pwd)"
echo ""

# =============================================================================
# Generate TypeScript SDK
# =============================================================================
echo "${YELLOW}Generating TypeScript SDK...${NC}"
openapi-generator generate \
  -i openapi-mapper.yaml \
  -g typescript-axios \
  -o typescript/generated \
  --additional-properties=npmName=@engineersmind/pdf-autofiller-sdk,npmVersion=1.0.0

echo "${GREEN}✓ TypeScript SDK generated in typescript/generated/${NC}"
echo ""

# =============================================================================
# Generate Go SDK
# =============================================================================
echo "${YELLOW}Generating Go SDK...${NC}"
mkdir -p go
openapi-generator generate \
  -i openapi-mapper.yaml \
  -g go \
  -o go/ \
  --additional-properties=packageName=pdfautofiller,packageVersion=1.0.0

echo "${GREEN}✓ Go SDK generated in go/${NC}"
echo ""

# =============================================================================
# Generate Java SDK
# =============================================================================
echo "${YELLOW}Generating Java SDK...${NC}"
mkdir -p java
openapi-generator generate \
  -i openapi-mapper.yaml \
  -g java \
  -o java/ \
  --additional-properties=groupId=com.engineersmind,artifactId=pdf-autofiller-sdk,artifactVersion=1.0.0

echo "${GREEN}✓ Java SDK generated in java/${NC}"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo "========================================="
echo "SDK Generation Complete!"
echo "========================================="
echo ""
echo "Generated SDKs:"
echo "  ✓ Python      - python/ (manually created)"
echo "  ✓ TypeScript  - typescript/generated/"
echo "  ✓ Go          - go/"
echo "  ✓ Java        - java/"
echo ""
echo "Next steps:"
echo "  1. Review generated code"
echo "  2. Run tests"
echo "  3. Publish to package registries"
echo ""
