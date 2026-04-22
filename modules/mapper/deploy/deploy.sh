#!/usr/bin/env bash
# deploy.sh — build, push, and deploy the mapper module
#
# Usage:
#   CLOUD_PROVIDER=aws ENV=dev ./deploy/deploy.sh
#   CLOUD_PROVIDER=azure ENV=staging ./deploy/deploy.sh
#   CLOUD_PROVIDER=gcp ENV=prod ./deploy/deploy.sh
#   CLOUD_PROVIDER=local ./deploy/deploy.sh   # docker compose only
#
# Required env vars per cloud:
#   AWS:   AWS_ACCOUNT_ID, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
#   Azure: AZURE_REGISTRY (e.g. myregistry.azurecr.io), az login required
#   GCP:   GCP_PROJECT_ID, GCP_REGION, gcloud auth required

set -euo pipefail

CLOUD_PROVIDER=${CLOUD_PROVIDER:-local}
ENV=${ENV:-dev}
MODULE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_NAME="pdf-autofillr-mapper"
IMAGE_TAG="${ENV}-$(git -C "$MODULE_DIR" rev-parse --short HEAD 2>/dev/null || echo latest)"

echo "==> Cloud: $CLOUD_PROVIDER | Env: $ENV | Tag: $IMAGE_TAG"

# ── Build Docker image ────────────────────────────────────────────────────────
build_image() {
  local full_uri=$1
  echo "==> Building image: $full_uri"
  docker build \
    -f "$MODULE_DIR/docker/Dockerfile" \
    --tag "$full_uri" \
    "$MODULE_DIR"
}

# ── AWS ───────────────────────────────────────────────────────────────────────
deploy_aws() {
  : "${AWS_ACCOUNT_ID:?AWS_ACCOUNT_ID required}"
  : "${AWS_REGION:?AWS_REGION required}"

  local registry="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  local image_uri="${registry}/${IMAGE_NAME}:${IMAGE_TAG}"

  # Create ECR repo if it doesn't exist
  aws ecr describe-repositories --repository-names "$IMAGE_NAME" --region "$AWS_REGION" 2>/dev/null || \
    aws ecr create-repository --repository-name "$IMAGE_NAME" --region "$AWS_REGION"

  # Login, build, push
  aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$registry"

  build_image "$image_uri"
  docker push "$image_uri"

  # Terraform apply
  cd "$MODULE_DIR/deploy/terraform/aws"
  terraform init -reconfigure
  terraform apply \
    -var="env=$ENV" \
    -var="region=$AWS_REGION" \
    -var="image_uri=$image_uri" \
    -var="llm_model=${LLM_MODEL:-gpt-4o}" \
    -var="rag_api_url=${RAG_API_URL:-}" \
    -auto-approve

  echo "==> AWS deploy complete"
  terraform output api_url
}

# ── Azure ─────────────────────────────────────────────────────────────────────
deploy_azure() {
  : "${AZURE_REGISTRY:?AZURE_REGISTRY required (e.g. myregistry.azurecr.io)}"

  local image_uri="${AZURE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

  az acr login --name "${AZURE_REGISTRY%%.*}"
  build_image "$image_uri"
  docker push "$image_uri"

  cd "$MODULE_DIR/deploy/terraform/azure"
  terraform init -reconfigure
  terraform apply \
    -var="env=$ENV" \
    -var="image_uri=$image_uri" \
    -var="llm_model=${LLM_MODEL:-gpt-4o}" \
    -var="rag_api_url=${RAG_API_URL:-}" \
    -auto-approve

  echo "==> Azure deploy complete"
  terraform output app_url
}

# ── GCP ───────────────────────────────────────────────────────────────────────
deploy_gcp() {
  : "${GCP_PROJECT_ID:?GCP_PROJECT_ID required}"
  GCP_REGION=${GCP_REGION:-us-central1}

  local registry="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/mapper"
  local image_uri="${registry}/${IMAGE_NAME}:${IMAGE_TAG}"

  gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet
  build_image "$image_uri"
  docker push "$image_uri"

  cd "$MODULE_DIR/deploy/terraform/gcp"
  terraform init -reconfigure
  terraform apply \
    -var="env=$ENV" \
    -var="project_id=$GCP_PROJECT_ID" \
    -var="region=$GCP_REGION" \
    -var="image_uri=$image_uri" \
    -var="llm_model=${LLM_MODEL:-gpt-4o}" \
    -var="rag_api_url=${RAG_API_URL:-}" \
    -auto-approve

  echo "==> GCP deploy complete"
  terraform output service_url
}

# ── Local (docker compose) ────────────────────────────────────────────────────
deploy_local() {
  echo "==> Starting local docker compose"
  docker compose -f "$MODULE_DIR/docker/docker-compose.yml" up --build -d
  echo "==> Running at http://localhost:8000"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
case "$CLOUD_PROVIDER" in
  aws)   deploy_aws   ;;
  azure) deploy_azure ;;
  gcp)   deploy_gcp   ;;
  local) deploy_local ;;
  *)     echo "Unknown CLOUD_PROVIDER: $CLOUD_PROVIDER (use aws|azure|gcp|local)"; exit 1 ;;
esac
