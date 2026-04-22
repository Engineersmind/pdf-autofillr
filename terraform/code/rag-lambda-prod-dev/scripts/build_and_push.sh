#!/usr/bin/env bash
##############################################################################
# scripts/build_and_push.sh
# Builds the Lambda container image and pushes it to ECR.
# Usage: ./scripts/build_and_push.sh <dev|staging|prod> [image_tag]
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"   # points to codebase root (above terraform/)

ENV="${1:-dev}"
TAG="${2:-latest}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🐳  RAG Lambda — Build & Push"
echo "  Environment : ${ENV}"
echo "  Tag         : ${TAG}"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Derive ECR URL from Terraform output ─────────────────────────────────────

cd "${SCRIPT_DIR}/.."   # terraform root

ECR_URL=$(terraform output -raw aws_ecr_repository_url 2>/dev/null)
if [[ -z "$ECR_URL" ]]; then
  echo "❌  Could not read aws_ecr_repository_url from Terraform state."
  echo "    Run constructor.sh first."
  exit 1
fi

AWS_REGION=$(grep aws_region "environments/${ENV}/terraform.tfvars" | awk -F'"' '{print $2}')
AWS_ACCOUNT=$(echo "$ECR_URL" | cut -d'.' -f1)

IMAGE_URI="${ECR_URL}:${TAG}"

echo "  ECR         : ${ECR_URL}"
echo "  Image URI   : ${IMAGE_URI}"
echo ""

# ── Login to ECR ──────────────────────────────────────────────────────────────

echo "🔑  Logging into ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo ""

# ── Build ─────────────────────────────────────────────────────────────────────

echo "🏗️   Building image (this bakes in all-MiniLM-L6-v2 — takes a few minutes first time)..."
docker build \
  --platform linux/amd64 \
  -t "${IMAGE_URI}" \
  -f "${ROOT_DIR}/Dockerfile" \
  "${ROOT_DIR}"

echo ""
echo "✅  Build complete"
echo ""

# ── Push ──────────────────────────────────────────────────────────────────────

echo "📤  Pushing to ECR..."
docker push "${IMAGE_URI}"

echo ""
echo "✅  Push complete: ${IMAGE_URI}"
echo ""

# ── Update Lambda ─────────────────────────────────────────────────────────────

LAMBDA_NAME=$(terraform output -raw aws_lambda_function_name 2>/dev/null)

if [[ -n "$LAMBDA_NAME" ]]; then
  echo "⚡  Updating Lambda image..."
  aws lambda update-function-code \
    --function-name "${LAMBDA_NAME}" \
    --image-uri "${IMAGE_URI}" \
    --region "${AWS_REGION}" \
    --output text

  echo "⏳  Waiting for update to complete..."
  aws lambda wait function-updated \
    --function-name "${LAMBDA_NAME}" \
    --region "${AWS_REGION}"

  echo ""
  echo "✅  Lambda updated: ${LAMBDA_NAME}"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Build & Push complete — ${ENV}"
echo "  Image URI: ${IMAGE_URI}"
echo "════════════════════════════════════════════════════════════"
echo ""
