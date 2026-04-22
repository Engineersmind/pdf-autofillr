#!/usr/bin/env bash
##############################################################################
# scripts/build_and_deploy.sh — ZIP deploy for doc-upload-lambda.
#
# This Lambda is deployed as a ZIP file (not Docker image).
# Packages: lambda_function.py, main.py, extractor_logic.py,
#           api_handler.py, s3_handler.py, logger_utils.py, teams_notifier.py
#
# Dependencies installed into a local /python layer folder then zipped.
# Requirements: PyMuPDF, Pillow, requests, python-dotenv, boto3,
#               python-docx, python-pptx, openpyxl
#
# Usage: ./scripts/build_and_deploy.sh <dev|staging|prod>
##############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CODEBASE_ROOT="$(cd "${TF_ROOT}/.." && pwd)"   # your actual code directory
ENV="${1:-dev}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  📦  Doc Upload Lambda — Build & Deploy (ZIP)"
echo "  Environment : ${ENV}"
echo "════════════════════════════════════════════════════════════"
echo ""

cd "${TF_ROOT}"
AWS_REGION=$(grep aws_region "environments/${ENV}/terraform.tfvars" | awk -F'"' '{print $2}')
LAMBDA_NAME=$(terraform output -raw lambda_function_name 2>/dev/null || echo "")
[[ -z "$LAMBDA_NAME" ]] && { echo "❌  Run constructor.sh first to create the Lambda"; exit 1; }

BUILD_DIR="/tmp/doc-upload-build-$$"
ZIP_FILE="/tmp/doc-upload-${ENV}.zip"

mkdir -p "${BUILD_DIR}"

echo "📂  Copying source files..."
# Copy your Lambda source files — adjust this list to match your actual files
cp "${CODEBASE_ROOT}/lambda_function.py"  "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/main.py"             "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/extractor_logic.py"  "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/api_handler.py"      "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/s3_handler.py"       "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/logger_utils.py"     "${BUILD_DIR}/"
cp "${CODEBASE_ROOT}/teams_notifier.py"   "${BUILD_DIR}/"

# Copy requirements if present
[[ -f "${CODEBASE_ROOT}/requirements.txt" ]] && \
  cp "${CODEBASE_ROOT}/requirements.txt" "${BUILD_DIR}/"

echo "📦  Installing dependencies..."
pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target "${BUILD_DIR}" \
  PyMuPDF==1.23.7 \
  Pillow==10.2.0 \
  requests==2.31.0 \
  python-dotenv==1.0.1 \
  boto3==1.34.0 \
  python-docx \
  python-pptx \
  openpyxl \
  --quiet

echo "🗜️   Zipping..."
cd "${BUILD_DIR}"
zip -r "${ZIP_FILE}" . --quiet
cd "${TF_ROOT}"

ZIP_SIZE=$(du -sh "${ZIP_FILE}" | cut -f1)
echo "  ✅  ${ZIP_FILE} (${ZIP_SIZE})"

# Also copy to modules/aws so Terraform can reference it
cp "${ZIP_FILE}" "${TF_ROOT}/modules/aws/lambda.zip"

echo ""
echo "⚡  Updating Lambda: ${LAMBDA_NAME}"
aws lambda update-function-code \
  --function-name "${LAMBDA_NAME}" \
  --zip-file "fileb://${ZIP_FILE}" \
  --region "${AWS_REGION}" \
  --output text

echo "⏳  Waiting for update..."
aws lambda wait function-updated \
  --function-name "${LAMBDA_NAME}" \
  --region "${AWS_REGION}"

echo "✅  Lambda updated"

# Clean up
rm -rf "${BUILD_DIR}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Deployed — ${LAMBDA_NAME} [${ENV}]"
echo "════════════════════════════════════════════════════════════"
echo ""
