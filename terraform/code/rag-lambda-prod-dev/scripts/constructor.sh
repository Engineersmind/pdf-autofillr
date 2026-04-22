#!/usr/bin/env bash
##############################################################################
# scripts/constructor.sh
# Provisions all rag-lambda infrastructure for a given environment.
# Usage: ./scripts/constructor.sh <dev|staging|prod>
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Args ─────────────────────────────────────────────────────────────────────

ENV="${1:-}"
if [[ -z "$ENV" ]]; then
  echo "❌  Usage: $0 <dev|staging|prod>"
  exit 1
fi

if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
  echo "❌  Invalid environment: $ENV  (must be dev, staging, or prod)"
  exit 1
fi

TFVARS="${ROOT_DIR}/environments/${ENV}/terraform.tfvars"
if [[ ! -f "$TFVARS" ]]; then
  echo "❌  tfvars not found: $TFVARS"
  exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🏗️   RAG Lambda — Constructor"
echo "  Environment : ${ENV}"
echo "  Time        : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Secret checks ─────────────────────────────────────────────────────────────

REQUIRED_SECRETS=(
  TF_VAR_openai_api_key
  TF_VAR_x_api_key
  TF_VAR_teams_webhook_url
)

echo "🔐  Checking required secret env vars..."
MISSING=()
for VAR in "${REQUIRED_SECRETS[@]}"; do
  if [[ -z "${!VAR:-}" ]]; then
    MISSING+=("$VAR")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo ""
  echo "❌  Missing required secret env vars:"
  for M in "${MISSING[@]}"; do
    echo "    - $M"
  done
  echo ""
  echo "  Set them with:"
  echo "    export TF_VAR_openai_api_key=\"sk-...\""
  echo "    export TF_VAR_x_api_key=\"...\""
  echo "    export TF_VAR_teams_webhook_url=\"https://...\""
  exit 1
fi
echo "  ✅  All secrets present"
echo ""

# ── Terraform init ────────────────────────────────────────────────────────────

cd "${ROOT_DIR}"

echo "📦  Initialising Terraform..."
terraform init -upgrade -reconfigure \
  -backend-config="key=rag-lambda/${ENV}/terraform.tfstate"

echo ""
echo "✅  Init complete"
echo ""

# ── Plan ─────────────────────────────────────────────────────────────────────

PLAN_FILE="/tmp/rag-lambda-${ENV}.tfplan"

echo "📋  Planning..."
terraform plan \
  -var-file="${TFVARS}" \
  -out="${PLAN_FILE}" \
  -compact-warnings

echo ""

# ── Confirmation gate for prod ────────────────────────────────────────────────

if [[ "$ENV" == "prod" ]]; then
  echo "⚠️   You are about to apply changes to PRODUCTION."
  read -rp "    Type 'yes' to continue: " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "    Aborted."
    exit 0
  fi
fi

# ── Apply ─────────────────────────────────────────────────────────────────────

echo "🚀  Applying..."
terraform apply "${PLAN_FILE}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Constructor complete — ${ENV}"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Print key outputs ─────────────────────────────────────────────────────────

echo "📤  Key outputs:"
terraform output -json | jq -r '
  to_entries[] |
  "  \(.key): \(.value.value)"
'

echo ""
echo "  Next step: build & push your Docker image then re-apply to update ecr_image_uri."
echo "  Run:  ./scripts/build_and_push.sh ${ENV}"
echo ""
