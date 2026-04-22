#!/usr/bin/env bash
##############################################################################
# scripts/bootstrap_backend.sh
# One-time: creates S3 state bucket + DynamoDB lock table.
# Usage: ./scripts/bootstrap_backend.sh [region]
##############################################################################

set -euo pipefail

REGION="${1:-us-east-1}"
STATE_BUCKET="doc-upload-tfstate"
LOCK_TABLE="doc-upload-tflock"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🗄️   PDF Extractor — Terraform Backend Bootstrap"
echo "  Region : ${REGION}"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── S3 state bucket ───────────────────────────────────────────────────────────

if aws s3api head-bucket --bucket "${STATE_BUCKET}" --region "${REGION}" 2>/dev/null; then
  echo "✅  State bucket already exists"
else
  echo "🪣  Creating state bucket: ${STATE_BUCKET}"
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "${STATE_BUCKET}" --region "${REGION}"
  else
    aws s3api create-bucket \
      --bucket "${STATE_BUCKET}" \
      --region "${REGION}" \
      --create-bucket-configuration LocationConstraint="${REGION}"
  fi

  aws s3api put-bucket-versioning \
    --bucket "${STATE_BUCKET}" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "${STATE_BUCKET}" \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

  aws s3api put-public-access-block \
    --bucket "${STATE_BUCKET}" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

  echo "✅  State bucket created"
fi

# ── DynamoDB lock table ───────────────────────────────────────────────────────

if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${REGION}" 2>/dev/null; then
  echo "✅  Lock table already exists"
else
  echo "🔒  Creating lock table: ${LOCK_TABLE}"
  aws dynamodb create-table \
    --table-name "${LOCK_TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${REGION}"

  aws dynamodb wait table-exists \
    --table-name "${LOCK_TABLE}" \
    --region "${REGION}"

  echo "✅  Lock table created"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Backend bootstrap complete"
echo "  Run: ./scripts/constructor.sh dev"
echo "════════════════════════════════════════════════════════════"
echo ""
