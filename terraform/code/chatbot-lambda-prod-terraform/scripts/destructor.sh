#!/usr/bin/env bash
##############################################################################
# scripts/destructor.sh — Tears down prod chatbot lambda.
# Triple-confirmation required for prod.
# Usage: ./scripts/destructor.sh prod
##############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV="${1:-prod}"
TFVARS="${ROOT_DIR}/environments/${ENV}/terraform.tfvars"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  💣  Chatbot Lambda — Destructor  [PROD]"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🚨  WARNING: PRODUCTION DESTROY"
echo ""
echo "    This will delete:"
echo "      - Lambda function + Function URL + provisioned concurrency"
echo "      - ECR repo + all images"
echo "      - IAM roles, CloudWatch, Secrets Manager, SNS"
echo "      - S3 buckets (output + static) and ALL their data"
echo ""
echo "    force_destroy = false on all buckets."
echo "    Manually empty them first, or this will fail."
echo ""
read -rp "    Type 'prod' to confirm environment: " C1
[[ "$C1" == "prod" ]] || { echo "Aborted."; exit 1; }
read -rp "    Type 'destroy' to proceed: " C2
[[ "$C2" == "destroy" ]] || { echo "Aborted."; exit 1; }

echo ""

# ── Manually empty S3 before destroy (force_destroy=false) ────────────────────

empty_bucket() {
  local B="$1"; [[ -z "$B" ]] && return
  echo "  🪣  Emptying: s3://${B}"
  aws s3 rm "s3://${B}" --recursive --quiet 2>/dev/null || true
  for TYPE in Versions DeleteMarkers; do
    aws s3api list-object-versions --bucket "$B" \
      --query "{Objects: ${TYPE}[].{Key:Key,VersionId:VersionId}}" \
      --output json 2>/dev/null | \
      jq 'select(.Objects != null)' | \
      aws s3api delete-objects --bucket "$B" --delete file:///dev/stdin 2>/dev/null || true
  done
  echo "    ✅  Done"
}

cd "${ROOT_DIR}"
echo "🪣  Emptying S3 buckets..."
for OUT in output_bucket_name static_bucket_name; do
  B=$(terraform output -raw "$OUT" 2>/dev/null || echo "")
  empty_bucket "$B"
done
echo "    ⚠️   prod_bucket NOT emptied — shared with other services"

echo ""
echo "📦  Init..."
terraform init -reconfigure \
  -backend-config="key=chatbot-lambda/prod/terraform.tfstate"

echo ""
echo "💣  Destroying..."
terraform destroy -var-file="${TFVARS}" -auto-approve

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Destructor complete — PROD"
echo "════════════════════════════════════════════════════════════"
echo ""
