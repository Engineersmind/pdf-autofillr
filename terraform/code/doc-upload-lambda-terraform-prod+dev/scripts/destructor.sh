#!/usr/bin/env bash
##############################################################################
# scripts/destructor.sh
# Tears down doc-upload-lambda infrastructure.
# Usage: ./scripts/destructor.sh <dev|staging|prod>
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV="${1:-}"
if [[ -z "$ENV" ]]; then echo "❌  Usage: $0 <dev|staging|prod>"; exit 1; fi
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then echo "❌  Invalid environment: $ENV"; exit 1; fi

TFVARS="${ROOT_DIR}/environments/${ENV}/terraform.tfvars"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  💣  Doc Upload Lambda — Destructor"
echo "  Environment : ${ENV}"
echo "  Time        : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "════════════════════════════════════════════════════════════"
echo ""

if [[ "$ENV" == "prod" ]]; then
  echo "🚨  WARNING: PRODUCTION DESTROY"
  echo "    This will delete:"
  echo "      - Lambda function + Function URL"
  echo "      - ECR repo + all images"
  echo "      - static_bucket + output_bucket + all their data"
  echo "      - IAM roles, CloudWatch, Secrets Manager"
  echo ""
  echo "    prod_bucket (pdf-fillr-production) has force_destroy=false."
  echo "    It must be manually emptied before destroy will succeed."
  echo ""
  read -rp "    Type the environment name to confirm: " C1
  [[ "$C1" == "$ENV" ]] || { echo "Aborted."; exit 1; }
  read -rp "    Type 'destroy' to proceed: " C2
  [[ "$C2" == "destroy" ]] || { echo "Aborted."; exit 1; }
else
  read -rp "⚠️   Destroy ${ENV}? Type 'yes': " CONFIRM
  [[ "$CONFIRM" == "yes" ]] || { echo "Aborted."; exit 0; }
fi

echo ""

# ── Empty S3 buckets ──────────────────────────────────────────────────────────

empty_bucket() {
  local BUCKET="$1"
  [[ -z "$BUCKET" ]] && return
  echo "  🪣  Emptying: s3://${BUCKET}"
  aws s3 rm "s3://${BUCKET}" --recursive --quiet 2>/dev/null || true

  # Delete all object versions (versioned bucket)
  aws s3api list-object-versions \
    --bucket "$BUCKET" \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
    --output json 2>/dev/null | \
    jq 'select(.Objects != null)' | \
    aws s3api delete-objects --bucket "$BUCKET" --delete file:///dev/stdin 2>/dev/null || true

  # Delete delete-markers
  aws s3api list-object-versions \
    --bucket "$BUCKET" \
    --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
    --output json 2>/dev/null | \
    jq 'select(.Objects != null)' | \
    aws s3api delete-objects --bucket "$BUCKET" --delete file:///dev/stdin 2>/dev/null || true

  echo "  ✅  ${BUCKET} emptied"
}

echo "🪣  Emptying S3 buckets..."
cd "${ROOT_DIR}"
STATIC=$(terraform output -raw static_bucket_name 2>/dev/null || echo "")
OUTPUT_B=$(terraform output -raw output_bucket_name 2>/dev/null || echo "")

empty_bucket "$STATIC"
empty_bucket "$OUTPUT_B"
# prod_bucket intentionally NOT auto-emptied — shared with rag-lambda

echo ""

# ── Destroy ───────────────────────────────────────────────────────────────────

echo "📦  Init..."
terraform init -reconfigure \
  -backend-config="key=doc-upload-lambda/${ENV}/terraform.tfstate"

echo ""
echo "💣  Destroying..."
terraform destroy \
  -var-file="${TFVARS}" \
  -auto-approve

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Destructor complete — ${ENV} torn down"
echo "════════════════════════════════════════════════════════════"
echo ""
