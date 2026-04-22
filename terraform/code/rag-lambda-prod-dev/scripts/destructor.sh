#!/usr/bin/env bash
##############################################################################
# scripts/destructor.sh
# Tears down rag-lambda infrastructure for a given environment.
# Production destruction requires typing the env name AND "destroy" to confirm.
# Usage: ./scripts/destructor.sh <dev|staging|prod>
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV="${1:-}"
if [[ -z "$ENV" ]]; then
  echo "❌  Usage: $0 <dev|staging|prod>"
  exit 1
fi

if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
  echo "❌  Invalid environment: $ENV"
  exit 1
fi

TFVARS="${ROOT_DIR}/environments/${ENV}/terraform.tfvars"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  💣  RAG Lambda — Destructor"
echo "  Environment : ${ENV}"
echo "  Time        : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Prod guard ────────────────────────────────────────────────────────────────

if [[ "$ENV" == "prod" ]]; then
  echo "🚨  WARNING: You are about to DESTROY the PRODUCTION environment."
  echo "    This will DELETE:"
  echo "      - Both S3 buckets and ALL their contents"
  echo "      - The Lambda function and all its config"
  echo "      - ECR repository and all images"
  echo "      - All IAM roles, secrets, API Gateway, and CloudWatch resources"
  echo ""
  echo "    The prod S3 bucket (pdf-fillr-production) has force_destroy=false."
  echo "    You must manually empty it before destruction will succeed."
  echo ""
  read -rp "    Type the environment name to confirm: " ENV_CONFIRM
  if [[ "$ENV_CONFIRM" != "$ENV" ]]; then
    echo "    ❌ Confirmation did not match. Aborted."
    exit 1
  fi
  read -rp "    Type 'destroy' to proceed: " DESTROY_CONFIRM
  if [[ "$DESTROY_CONFIRM" != "destroy" ]]; then
    echo "    ❌ Aborted."
    exit 1
  fi
else
  echo "⚠️   About to destroy environment: ${ENV}"
  read -rp "    Type 'yes' to continue: " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "    Aborted."
    exit 0
  fi
fi

echo ""

# ── Pre-destroy: empty S3 buckets (needed when force_destroy=false) ───────────

echo "🪣  Emptying S3 buckets before destroy..."

RAG_BUCKET=$(terraform -chdir="${ROOT_DIR}" output -raw aws_rag_bucket_name 2>/dev/null || echo "")
PROD_BUCKET=$(terraform -chdir="${ROOT_DIR}" output -raw aws_prod_bucket_name 2>/dev/null || echo "")

empty_bucket() {
  local BUCKET="$1"
  if [[ -z "$BUCKET" ]]; then return; fi
  echo "  Emptying: s3://${BUCKET}"
  aws s3 rm "s3://${BUCKET}" --recursive --quiet || true
  # Delete all versions (versioned bucket)
  aws s3api list-object-versions \
    --bucket "$BUCKET" \
    --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
    --output json 2>/dev/null | \
    jq 'select(.Objects != null)' | \
    aws s3api delete-objects --bucket "$BUCKET" --delete file:///dev/stdin 2>/dev/null || true
  # Delete delete markers
  aws s3api list-object-versions \
    --bucket "$BUCKET" \
    --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
    --output json 2>/dev/null | \
    jq 'select(.Objects != null)' | \
    aws s3api delete-objects --bucket "$BUCKET" --delete file:///dev/stdin 2>/dev/null || true
  echo "  ✅  ${BUCKET} emptied"
}

empty_bucket "$RAG_BUCKET"
empty_bucket "$PROD_BUCKET"

echo ""

# ── Terraform init + destroy ──────────────────────────────────────────────────

cd "${ROOT_DIR}"

echo "📦  Initialising Terraform..."
terraform init -reconfigure \
  -backend-config="key=rag-lambda/${ENV}/terraform.tfstate"

echo ""
echo "💣  Destroying..."
terraform destroy \
  -var-file="${TFVARS}" \
  -auto-approve

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Destructor complete — ${ENV} is fully torn down."
echo "════════════════════════════════════════════════════════════"
echo ""
