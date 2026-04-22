#!/usr/bin/env bash
# deploy.sh — build, push, and deploy the mapper module
#
# Usage:
#   ./deploy/deploy.sh --env dev               # full deploy (build + push + terraform apply)
#   ./deploy/deploy.sh --env prod              # prod full deploy
#   ./deploy/deploy.sh --env dev  --update     # code-only: rebuild image + update Lambda (skip terraform)
#   ./deploy/deploy.sh --env prod --update
#   ./deploy/deploy.sh --cloud azure
#   ./deploy/deploy.sh --cloud gcp
#   ./deploy/deploy.sh --cloud local
#
# --update is faster when only Python code changed (no infra/env-var changes).

set -euo pipefail

MODULE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── Argument parsing ──────────────────────────────────────────────────────────

ENV="dev"
CLOUD="aws"
UPDATE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)    ENV="$2";   shift 2 ;;
    --cloud)  CLOUD="$2"; shift 2 ;;
    --update) UPDATE=true; shift  ;;
    *) echo "Unknown option: $1"; echo "Usage: $0 [--env dev|prod] [--cloud aws|azure|gcp|local] [--update]"; exit 1 ;;
  esac
done

IMAGE_TAG="${ENV}-$(git -C "$MODULE_DIR" rev-parse --short HEAD 2>/dev/null || echo latest)"
echo "==> Cloud: $CLOUD | Env: $ENV | Tag: $IMAGE_TAG | Update-only: $UPDATE"

# ── Helpers ───────────────────────────────────────────────────────────────────

build_image() {
  local uri="$1"
  echo "==> Building: $uri"
  docker build -f "$MODULE_DIR/docker/Dockerfile" --tag "$uri" "$MODULE_DIR"
}

_tfvar() {
  local key="$1" dir="$2"
  awk -F'"' "/^${key}[[:space:]]*=/{print \$2; exit}" "${dir}/terraform.tfvars" 2>/dev/null || true
}

# ── AWS ───────────────────────────────────────────────────────────────────────

deploy_aws() {
  local tf_dir
  [[ "$ENV" == "prod" ]] && tf_dir="$MODULE_DIR/deploy/terraform/aws" \
                         || tf_dir="$MODULE_DIR/deploy/terraform/aws-dev"

  echo "==> Terraform dir: ${tf_dir}"

  if [[ ! -f "${tf_dir}/terraform.tfvars" ]]; then
    echo "ERROR: ${tf_dir}/terraform.tfvars not found."
    echo "       cp ${tf_dir}/terraform.tfvars.example ${tf_dir}/terraform.tfvars  # then fill in values"
    exit 1
  fi

  echo "==> Resolving AWS identity..."
  local region ecr_repo account_id
  account_id=$(aws sts get-caller-identity --query Account --output text) \
    || { echo "ERROR: aws sts get-caller-identity failed — is your AWS profile active?"; exit 1; }
  region=$(aws configure get region 2>/dev/null || true)
  [[ -z "$region" ]] && region=$(_tfvar region "$tf_dir")
  [[ -z "$region" ]] && region="us-east-1"
  ecr_repo=$(_tfvar ecr_repository_name "$tf_dir")
  [[ -z "$ecr_repo" ]] && ecr_repo="pdf-autofiller-mapper-${ENV}"

  local registry="${account_id}.dkr.ecr.${region}.amazonaws.com"
  local image_uri="${registry}/${ecr_repo}:${IMAGE_TAG}"
  local lambda_name
  lambda_name="$(_tfvar project "$tf_dir")-${ENV}"

  echo "==> Account: ${account_id} | Region: ${region} | ECR: ${ecr_repo}"

  aws ecr get-login-password --region "$region" | \
    docker login --username AWS --password-stdin "$registry"

  local latest_uri="${registry}/${ecr_repo}:latest"

  build_image "$image_uri"
  docker push "$image_uri"
  docker tag "$image_uri" "$latest_uri"
  docker push "$latest_uri"

  if $UPDATE; then
    echo "==> --update: skipping terraform, updating Lambda image directly"
    aws lambda update-function-code \
      --function-name "$lambda_name" \
      --image-uri     "$latest_uri" \
      --region        "$region" \
      --output text --query 'FunctionArn'
    echo "==> Waiting for update to complete..."
    aws lambda wait function-updated \
      --function-name "$lambda_name" \
      --region        "$region"
  else
    cd "$tf_dir"
    terraform init -reconfigure
    terraform apply -auto-approve
    echo ""
    terraform output function_url
  fi

  echo "==> AWS [${ENV}] deploy complete"
}

# ── Azure ─────────────────────────────────────────────────────────────────────

deploy_azure() {
  : "${AZURE_REGISTRY:?--cloud azure requires AZURE_REGISTRY env var}"
  local image_uri="${AZURE_REGISTRY}/pdf-autofillr-mapper:${IMAGE_TAG}"
  az acr login --name "${AZURE_REGISTRY%%.*}"
  build_image "$image_uri"
  docker push "$image_uri"
  cd "$MODULE_DIR/deploy/terraform/azure"
  terraform init -reconfigure
  terraform apply -var="env=$ENV" -auto-approve
  terraform output app_url
  echo "==> Azure [${ENV}] deploy complete"
}

# ── GCP ───────────────────────────────────────────────────────────────────────

deploy_gcp() {
  : "${GCP_PROJECT_ID:?--cloud gcp requires GCP_PROJECT_ID env var}"
  local region="${GCP_REGION:-us-central1}"
  local registry="${region}-docker.pkg.dev/${GCP_PROJECT_ID}/mapper"
  local image_uri="${registry}/pdf-autofillr-mapper:${IMAGE_TAG}"
  gcloud auth configure-docker "${region}-docker.pkg.dev" --quiet
  build_image "$image_uri"
  docker push "$image_uri"
  cd "$MODULE_DIR/deploy/terraform/gcp"
  terraform init -reconfigure
  terraform apply -var="env=$ENV" -var="project_id=$GCP_PROJECT_ID" -var="region=$region" -auto-approve
  terraform output service_url
  echo "==> GCP [${ENV}] deploy complete"
}

# ── Local ─────────────────────────────────────────────────────────────────────

deploy_local() {
  docker compose -f "$MODULE_DIR/docker/docker-compose.yml" up --build -d
  echo "==> Running at http://localhost:8000"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

case "$CLOUD" in
  aws)   deploy_aws   ;;
  azure) deploy_azure ;;
  gcp)   deploy_gcp   ;;
  local) deploy_local ;;
  *) echo "Unknown --cloud: $CLOUD (aws|azure|gcp|local)"; exit 1 ;;
esac
