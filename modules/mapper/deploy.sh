#!/bin/bash
# =============================================================================
# deploy.sh — build + deploy pdf-autofiller-mapper to AWS Lambda
#
# Usage:
#   ./deploy.sh            — full deploy (Terraform + image push + Lambda update)
#   ./deploy.sh --update   — image push + Lambda update only (skip Terraform)
# =============================================================================

set -euo pipefail

TERRAFORM_VERSION="1.9.8"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="${SCRIPT_DIR}/deploy/terraform/aws"
UPDATE_ONLY=false

for arg in "$@"; do
    [ "$arg" = "--update" ] && UPDATE_ONLY=true
done

log() { echo ""; echo ">>> $1"; }

# =============================================================================
# 1. Verify AWS identity
# =============================================================================
log "Verifying AWS identity..."
aws sts get-caller-identity

# =============================================================================
# 2. Resolve REGION, FUNCTION_NAME, ECR_URI
# =============================================================================
if [ "$UPDATE_ONLY" = true ]; then
    log "Update-only mode — skipping Terraform"

    REGION=$(grep 'region' "${TERRAFORM_DIR}/terraform.tfvars" | awk -F'"' '{print $2}')
    PROJECT=$(grep '^project' "${TERRAFORM_DIR}/terraform.tfvars" | awk -F'"' '{print $2}')
    ENV=$(grep '^env' "${TERRAFORM_DIR}/terraform.tfvars" | awk -F'"' '{print $2}')
    FUNCTION_NAME="${PROJECT}-${ENV}"

    ECR_URI=$(aws ecr describe-repositories --region "${REGION}" \
        --query "repositories[?repositoryName=='${FUNCTION_NAME}'].repositoryUri | [0]" \
        --output text)
    log "ECR: ${ECR_URI}"
    log "Function: ${FUNCTION_NAME}"
else
    # Install Terraform if needed
    if ! command -v terraform &>/dev/null; then
        log "Installing Terraform ${TERRAFORM_VERSION}..."
        wget -q "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
        unzip -q "terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
        sudo mv terraform /usr/local/bin/
        rm "terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
    else
        log "Terraform already installed: $(terraform version -json | python3 -c 'import sys,json; print(json.load(sys.stdin)["terraform_version"])')"
    fi

    log "Checking terraform.tfvars..."
    if [ ! -f "${TERRAFORM_DIR}/terraform.tfvars" ]; then
        echo "ERROR: terraform.tfvars not found at ${TERRAFORM_DIR}/terraform.tfvars"
        echo ""
        echo "  cd ${TERRAFORM_DIR}"
        echo "  cp terraform.tfvars.example terraform.tfvars"
        echo "  # Fill in your API keys and secrets, then re-run ./deploy.sh"
        exit 1
    fi

    REGION=$(grep 'region' "${TERRAFORM_DIR}/terraform.tfvars" | awk -F'"' '{print $2}')

    log "Phase 1: Terraform init + apply ECR repo..."
    cd "${TERRAFORM_DIR}"
    terraform init -upgrade
    PROJECT=$(grep '^project' "${TERRAFORM_DIR}/terraform.tfvars" | awk -F'"' '{print $2}')
    ENV=$(grep '^env' "${TERRAFORM_DIR}/terraform.tfvars" | awk -F'"' '{print $2}')
    FUNCTION_NAME="${PROJECT}-${ENV}"

    terraform apply \
        -target=aws_ecr_repository.mapper \
        -target=aws_ecr_lifecycle_policy.mapper \
        -auto-approve
    ECR_URI=$(terraform output -raw ecr_repository_url)
    log "ECR: ${ECR_URI}"
    log "Function: ${FUNCTION_NAME}"
fi

# =============================================================================
# 3. Build + push Docker image
# =============================================================================
log "Authenticating with ECR..."
aws ecr get-login-password --region "${REGION}" \
    | docker login --username AWS --password-stdin "${ECR_URI}"

log "Building Docker image (linux/amd64)..."
cd "${SCRIPT_DIR}"
docker build \
    --platform linux/amd64 \
    --provenance=false \
    -t "${FUNCTION_NAME}:latest" \
    -f docker/Dockerfile \
    .

docker tag "${FUNCTION_NAME}:latest" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"
log "Image pushed: ${ECR_URI}:latest"

# =============================================================================
# 4. Terraform full apply (full deploy only)
# =============================================================================
if [ "$UPDATE_ONLY" = false ]; then
    log "Terraform full apply..."
    cd "${TERRAFORM_DIR}"
    terraform apply -auto-approve
fi

# =============================================================================
# 5. Update Lambda with new image
# =============================================================================
log "Updating Lambda function with new image..."
aws lambda update-function-code \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --image-uri "${ECR_URI}:latest" \
    --output text --query 'FunctionName'

aws lambda wait function-updated \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}"
log "✓ ${FUNCTION_NAME} updated"

# =============================================================================
# 6. Done
# =============================================================================
log "Deploy complete!"
echo ""
echo "  ECR image   : ${ECR_URI}:latest"
echo "  Lambda      : ${FUNCTION_NAME}"
echo ""
echo "  Invoke (test):"
echo "    aws lambda invoke \\"
echo "      --function-name ${FUNCTION_NAME} \\"
echo "      --region ${REGION} \\"
echo "      --payload '{\"operation\":\"check_embed_file\",\"user_id\":1,\"pdf_doc_id\":1,\"session_id\":\"test\",\"env\":\"prod_user\"}' \\"
echo "      /tmp/mapper-out.json && cat /tmp/mapper-out.json"
echo ""
echo "  Function URL: run 'terraform output function_url' in ${TERRAFORM_DIR}"
echo ""
