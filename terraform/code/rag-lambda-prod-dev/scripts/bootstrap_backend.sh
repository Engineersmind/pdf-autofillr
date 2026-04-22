#!/usr/bin/env bash
##############################################################################
# scripts/bootstrap_backend.sh
# One-time setup: creates the S3 bucket + DynamoDB table used for
# Terraform remote state. Run this ONCE before constructor.sh.
# Usage: ./scripts/bootstrap_backend.sh <aws_region>
##############################################################################

set -euo pipefail

REGION="${1:-ap-south-1}"
STATE_BUCKET="rag-lambda-tfstate"
LOCK_TABLE="rag-lambda-tflock"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🗄️   Terraform Backend Bootstrap"
echo "  Region      : ${REGION}"
echo "  State bucket: ${STATE_BUCKET}"
echo "  Lock table  : ${LOCK_TABLE}"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── S3 state bucket ───────────────────────────────────────────────────────────

if aws s3api head-bucket --bucket "${STATE_BUCKET}" --region "${REGION}" 2>/dev/null; then
  echo "✅  State bucket already exists: ${STATE_BUCKET}"
else
  echo "🪣  Creating state bucket..."
  aws s3api create-bucket \
    --bucket "${STATE_BUCKET}" \
    --region "${REGION}" \
    --create-bucket-configuration LocationConstraint="${REGION}"

  aws s3api put-bucket-versioning \
    --bucket "${STATE_BUCKET}" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption \
    --bucket "${STATE_BUCKET}" \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'

  aws s3api put-public-access-block \
    --bucket "${STATE_BUCKET}" \
    --public-access-block-configuration \
      "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

  echo "✅  State bucket created"
fi

# ── DynamoDB lock table ───────────────────────────────────────────────────────

if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${REGION}" 2>/dev/null; then
  echo "✅  Lock table already exists: ${LOCK_TABLE}"
else
  echo "🔒  Creating DynamoDB lock table..."
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
echo "  ✅  Backend bootstrap complete."
echo "  Now run: ./scripts/constructor.sh <dev|staging|prod>"
echo "════════════════════════════════════════════════════════════"
echo ""
