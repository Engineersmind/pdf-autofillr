#!/usr/bin/env bash
##############################################################################
# scripts/build_and_deploy.sh — ZIP deploy for chatbot-lambda (prod).
#
# Prod dependencies: langchain, langchain-openai, langchain-core,
#                    openai, fuzzywuzzy, boto3, psycopg2-binary
# NOTE: prod does NOT include aiohttp/asyncio (different codebase from dev)
#
# Usage: ./scripts/build_and_deploy.sh [prod]
##############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CODEBASE_ROOT="$(cd "${TF_ROOT}/.." && pwd)"
ENV="${1:-prod}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  📦  Chatbot Lambda PROD — Build & Deploy (ZIP)"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Prod confirmation ─────────────────────────────────────────────────────────
echo "⚠️   Deploying to PRODUCTION Lambda."
read -rp "    Type 'prod' to confirm: " CONFIRM
[[ "$CONFIRM" == "prod" ]] || { echo "Aborted."; exit 1; }
echo ""

cd "${TF_ROOT}"
AWS_REGION=$(grep aws_region "environments/${ENV}/terraform.tfvars" | awk -F'"' '{print $2}')
LAMBDA_NAME=$(terraform output -raw lambda_function_name 2>/dev/null || echo "")
[[ -z "$LAMBDA_NAME" ]] && { echo "❌  Run constructor.sh first"; exit 1; }

BUILD_DIR="/tmp/chatbot-prod-build-$$"
ZIP_FILE="/tmp/chatbot-prod.zip"
mkdir -p "${BUILD_DIR}"

echo "📂  Copying source files..."
cp "${CODEBASE_ROOT}/lambda_function.py"        "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/chatbot_core.py"           "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/s3_helper.py"              "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/knowledge_base_builder.py" "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/rds_helper.py"             "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/teams_notifier.py"         "${BUILD_DIR}/"

[[ -f "${CODEBASE_ROOT}/requirements.txt" ]] && \
  cp "${CODEBASE_ROOT}/requirements.txt" "${BUILD_DIR}/"

echo "📦  Installing prod dependencies (no aiohttp — prod codebase)..."
pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target "${BUILD_DIR}" \
  "langchain-openai==0.2.12" \
  "langchain-core==0.3.28" \
  "langchain==0.3.13" \
  "openai==1.59.6" \
  "fuzzywuzzy==0.18.0" \
  "boto3==1.35.93" \
  "psycopg2-binary==2.9.10" \
  --quiet

echo "🗜️   Zipping..."
cd "${BUILD_DIR}"
zip -r "${ZIP_FILE}" . --quiet
cd "${TF_ROOT}"

ZIP_SIZE=$(du -sh "${ZIP_FILE}" | cut -f1)
echo "  ✅  ${ZIP_FILE} (${ZIP_SIZE})"

cp "${ZIP_FILE}" "${TF_ROOT}/modules/aws/lambda.zip"

echo ""
echo "⚡  Updating PROD Lambda: ${LAMBDA_NAME}"
aws lambda update-function-code \
  --function-name "${LAMBDA_NAME}" \
  --zip-file "fileb://${ZIP_FILE}" \
  --region "${AWS_REGION}" \
  --output text

echo "⏳  Waiting..."
aws lambda wait function-updated \
  --function-name "${LAMBDA_NAME}" \
  --region "${AWS_REGION}"

echo "✅  Lambda updated"
rm -rf "${BUILD_DIR}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Deployed — ${LAMBDA_NAME} [PROD]"
echo "════════════════════════════════════════════════════════════"
echo ""
