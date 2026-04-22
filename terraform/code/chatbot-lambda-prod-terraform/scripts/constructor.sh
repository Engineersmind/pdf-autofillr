#!/usr/bin/env bash
##############################################################################
# scripts/constructor.sh — Provisions prod chatbot lambda infrastructure.
# Usage: ./scripts/constructor.sh prod
#
# Prod requires typing environment name to confirm (not just "yes").
##############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV="${1:-prod}"
TFVARS="${ROOT_DIR}/environments/${ENV}/terraform.tfvars"
[[ -f "$TFVARS" ]] || { echo "❌  Missing: $TFVARS"; exit 1; }

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🏗️   Chatbot Lambda — Constructor"
echo "  Environment : ${ENV}"
echo "  Time        : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "════════════════════════════════════════════════════════════"
echo ""

# ── Required secrets ─────────────────────────────────────────────────────────
REQUIRED=(
  TF_VAR_auth_token
  TF_VAR_openai_api_key
  TF_VAR_auth0_client_id
  TF_VAR_auth0_client_secret
  TF_VAR_pdf_api_key
  TF_VAR_teams_webhook_url   # Active in prod — required
)

echo "🔐  Checking secrets..."
MISSING=()
for V in "${REQUIRED[@]}"; do
  [[ -z "${!V:-}" ]] && MISSING+=("$V")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "❌  Missing:"
  for M in "${MISSING[@]}"; do echo "    - $M"; done
  echo ""
  echo "  Export them (prod values differ from dev):"
  cat <<'EOF'
    export TF_VAR_auth_token="7KmP@9xQ2NvL5!"
    export TF_VAR_openai_api_key="sk-proj-..."
    export TF_VAR_auth0_client_id="ZdwNOcyrlOMwt24cDHwtTEXb278E3QlM"
    export TF_VAR_auth0_client_secret="qKx92yxfRx5mYy-..."
    export TF_VAR_pdf_api_key="7KmP@9xQ2NvL5!"
    export TF_VAR_teams_webhook_url="https://defaultb3869958a2da40b3a9a11..."
    export TF_VAR_x_event_key="123456"
    export TF_VAR_admin_username="subhamsuvendu98@gmail.com"
    export TF_VAR_admin_password="..."
EOF
  exit 1
fi
echo "  ✅  All secrets present"
echo ""

# ── Prod confirmation ─────────────────────────────────────────────────────────
echo "⚠️   You are about to deploy to PRODUCTION."
echo ""
echo "    Auth0 Domain : dev-ust08ro3ukgmtcrx.us.auth0.com"
echo "    Backend URL  : https://api.pdffillr.ai/"
echo "    Fill PDF URL : 3udsn2n2xcnc7qdcfqncwi3sca0yrdff.lambda-url..."
echo "    Teams webhook: ACTIVE"
echo ""
read -rp "    Type 'prod' to confirm: " CONFIRM
[[ "$CONFIRM" == "prod" ]] || { echo "Aborted."; exit 1; }
echo ""

cd "${ROOT_DIR}"

echo "📦  Init..."
terraform init -upgrade -reconfigure \
  -backend-config="key=chatbot-lambda/prod/terraform.tfstate"
echo ""

echo "📋  Plan..."
PLAN_FILE="/tmp/chatbot-prod.tfplan"
terraform plan -var-file="${TFVARS}" -out="${PLAN_FILE}" -compact-warnings
echo ""

echo "🚀  Applying..."
terraform apply "${PLAN_FILE}"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅  Constructor complete — PROD"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📤  Outputs:"
terraform output -json | jq -r 'to_entries[] | "  \(.key): \(.value.value)"'
echo ""
echo "  Next: ./scripts/build_and_push.sh prod"
echo ""
