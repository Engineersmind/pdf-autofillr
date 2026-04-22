#!/usr/bin/env bash
##############################################################################
# scripts/build_and_push.sh — Build + push prod chatbot Lambda image.
# Usage: ./scripts/build_and_push.sh [prod] [tag]
#
# Prod requirements.txt has: langchain, langchain-openai, fuzzywuzzy, openai,
# boto3, psycopg2-binary. Does NOT have: aiohttp, asyncio (those are dev-only).
##############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CODEBASE_ROOT="$(cd "${TF_ROOT}/.." && pwd)"
ENV="${1:-prod}"
TAG="${2:-latest}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🐳  Chatbot Lambda PROD — Build & Push  [${TAG}]"
echo "════════════════════════════════════════════════════════════"
echo ""

cd "${TF_ROOT}"
AWS_REGION=$(grep aws_region "environments/${ENV}/terraform.tfvars" | awk -F'"' '{print $2}')
ECR_URL=$(terraform output -raw ecr_repository_url 2>/dev/null)
[[ -z "$ECR_URL" ]] && { echo "❌  Run constructor.sh first"; exit 1; }

AWS_ACCOUNT=$(echo "$ECR_URL" | cut -d'.' -f1)
IMAGE_URI="${ECR_URL}:${TAG}"

echo "  ECR   : ${ECR_URL}"
echo "  Image : ${IMAGE_URI}"
echo ""

echo "🔑  ECR login..."
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin \
    "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo ""
echo "🏗️   Building prod image..."
echo "    Prod deps: langchain, langchain-openai, fuzzywuzzy, openai, boto3, psycopg2"
docker build --platform linux/amd64 \
  -t "${IMAGE_URI}" \
  -f "${CODEBASE_ROOT}/Dockerfile" \
  "${CODEBASE_ROOT}"

echo "📤  Pushing..."
docker push "${IMAGE_URI}"
echo "✅  Push complete"

LAMBDA_NAME=$(terraform output -raw lambda_function_name 2>/dev/null || echo "")
if [[ -n "$LAMBDA_NAME" ]]; then
  echo ""
  echo "⚡  Updating prod Lambda: ${LAMBDA_NAME}"
  aws lambda update-function-code \
    --function-name "${LAMBDA_NAME}" \
    --image-uri "${IMAGE_URI}" \
    --region "${AWS_REGION}" \
    --output text
  aws lambda wait function-updated \
    --function-name "${LAMBDA_NAME}" \
    --region "${AWS_REGION}"
  echo "✅  Lambda updated"

  FUNC_URL=$(terraform output -raw lambda_function_url 2>/dev/null || echo "")
  [[ -n "$FUNC_URL" ]] && echo "  🌐 Prod Function URL: ${FUNC_URL}"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Complete — ${IMAGE_URI}"
echo "════════════════════════════════════════════════════════════"
echo ""
