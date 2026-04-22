#!/usr/bin/env bash
# destroy.sh — Tear down mapper infrastructure for a given cloud and environment.
#
# Usage:
#   ./deploy/destroy.sh --env dev               # AWS dev   (default)
#   ./deploy/destroy.sh --env prod              # AWS prod
#   ./deploy/destroy.sh --cloud azure
#   ./deploy/destroy.sh --cloud gcp
#   ./deploy/destroy.sh --cloud local

set -euo pipefail

MODULE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── Argument parsing ──────────────────────────────────────────────────────────

ENV="dev"
CLOUD="aws"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)   ENV="$2";   shift 2 ;;
    --cloud) CLOUD="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; echo "Usage: $0 [--env dev|prod] [--cloud aws|azure|gcp|local]"; exit 1 ;;
  esac
done

echo "==> Cloud: $CLOUD | Env: $ENV"

# ── Helpers ───────────────────────────────────────────────────────────────────

confirm() {
  local prompt="$1"
  local reply
  printf "\n%s [y/N] " "$prompt"
  read -r reply </dev/tty
  [[ "${reply,,}" == "y" || "${reply,,}" == "yes" ]]
}

abort() {
  echo ""
  echo "Aborted. No changes made."
  exit 0
}

_tfvar() {
  local key="$1" dir="$2"
  awk -F'"' "/^${key}[[:space:]]*=/{print \$2; exit}" "${dir}/terraform.tfvars" 2>/dev/null || true
}

# ── AWS ───────────────────────────────────────────────────────────────────────

destroy_aws() {
  local tf_dir
  [[ "$ENV" == "prod" ]] && tf_dir="$MODULE_DIR/deploy/terraform/aws" \
                         || tf_dir="$MODULE_DIR/deploy/terraform/aws-dev"

  if [[ ! -f "${tf_dir}/terraform.tfvars" ]]; then
    echo "ERROR: ${tf_dir}/terraform.tfvars not found."
    echo "       cp ${tf_dir}/terraform.tfvars.example ${tf_dir}/terraform.tfvars  # then fill in values"
    exit 1
  fi

  local region project env ecr_repo lambda_name
  region=$(aws configure get region 2>/dev/null || true)
  [[ -z "$region" ]] && region=$(_tfvar region "$tf_dir")
  [[ -z "$region" ]] && region="us-east-1"
  project=$(_tfvar project "$tf_dir")
  env=$(_tfvar env "$tf_dir")
  ecr_repo=$(_tfvar ecr_repository_name "$tf_dir")
  [[ -z "$ecr_repo" ]] && ecr_repo="${project}-${env}"
  lambda_name="${project}-${env}"

  echo ""
  echo "================================================================"
  echo "  DESTROY — pdf-autofiller mapper [${env}]"
  echo "  Dir:     ${tf_dir}"
  echo "  Region:  ${region}"
  echo "  Lambda:  ${lambda_name}"
  echo "  ECR:     ${ecr_repo}"
  echo "================================================================"
  echo ""
  echo "  Will permanently delete:"
  echo "    • Lambda function + Function URL"
  echo "    • IAM role + policies"
  echo "    • CloudWatch log group (all logs lost)"
  echo "    • ECR repository + all images"
  echo ""
  echo "  NOT affected: S3 buckets and their data (shared resources)"
  echo ""

  confirm "Continue and show destroy plan?" || abort

  cd "$tf_dir"
  echo ""
  echo "==> terraform plan -destroy"
  echo "------------------------------------------------------------"
  terraform plan -destroy -out=destroy.tfplan
  echo "------------------------------------------------------------"

  confirm "Apply the destroy plan above?" || { rm -f destroy.tfplan; abort; }

  # Purge ECR images first (terraform destroy fails if repo is non-empty).
  echo ""
  echo "==> Checking ECR for images in: ${ecr_repo}"

  IMAGE_JSON=$(aws ecr list-images \
    --repository-name "${ecr_repo}" \
    --region "${region}" \
    --query 'imageIds[*]' \
    --output json 2>/dev/null || echo "[]")

  IMAGE_COUNT=$(python3 -c "import json; print(len(json.loads(r'''${IMAGE_JSON}''')))" 2>/dev/null || echo "0")

  if [[ "$IMAGE_COUNT" == "0" ]]; then
    echo "   ECR repo is empty — no images to delete."
  else
    echo "   Found ${IMAGE_COUNT} image(s) in ECR."
    confirm "   Delete all ${IMAGE_COUNT} ECR image(s)? (required to remove the repo)" || {
      rm -f destroy.tfplan
      echo "Cannot destroy ECR repo while it has images. Re-run ./destroy.sh after deleting them manually."
      exit 1
    }
    aws ecr batch-delete-image \
      --repository-name "${ecr_repo}" \
      --region "${region}" \
      --image-ids "$(python3 -c "import json; print(json.dumps(json.loads(r'''${IMAGE_JSON}''')))")" \
      --output json \
    | python3 -c "
import sys,json; r=json.load(sys.stdin)
print(f'   Deleted {len(r.get(\"imageIds\",[]))} image(s).')
if r.get('failures'): print('   Failures:', r['failures'])
" 2>/dev/null || echo "   Done."
  fi

  echo ""
  echo "==> terraform apply destroy.tfplan"
  terraform apply destroy.tfplan
  rm -f destroy.tfplan

  echo ""
  echo "================================================================"
  echo "  DONE — [${env}] infrastructure destroyed."
  echo "  To recreate: cd ${tf_dir} && terraform init && terraform apply"
  echo "================================================================"
}

# ── Azure ─────────────────────────────────────────────────────────────────────

destroy_azure() {
  local tf_dir="$MODULE_DIR/deploy/terraform/azure"
  confirm "Destroy Azure [${ENV}] infrastructure?" || abort
  cd "$tf_dir"
  terraform plan -destroy -out=destroy.tfplan
  confirm "Apply the destroy plan above?" || { rm -f destroy.tfplan; abort; }
  terraform apply destroy.tfplan
  rm -f destroy.tfplan
  echo "==> Azure [${ENV}] infrastructure destroyed."
}

# ── GCP ───────────────────────────────────────────────────────────────────────

destroy_gcp() {
  local tf_dir="$MODULE_DIR/deploy/terraform/gcp"
  confirm "Destroy GCP [${ENV}] infrastructure?" || abort
  cd "$tf_dir"
  terraform plan -destroy -out=destroy.tfplan
  confirm "Apply the destroy plan above?" || { rm -f destroy.tfplan; abort; }
  terraform apply destroy.tfplan
  rm -f destroy.tfplan
  echo "==> GCP [${ENV}] infrastructure destroyed."
}

# ── Local ─────────────────────────────────────────────────────────────────────

destroy_local() {
  confirm "Stop and remove local containers + volumes?" || abort
  docker compose -f "$MODULE_DIR/docker/docker-compose.yml" down -v
  echo "==> Local containers removed."
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

case "$CLOUD" in
  aws)   destroy_aws   ;;
  azure) destroy_azure ;;
  gcp)   destroy_gcp   ;;
  local) destroy_local ;;
  *) echo "Unknown --cloud: $CLOUD (aws|azure|gcp|local)"; exit 1 ;;
esac
