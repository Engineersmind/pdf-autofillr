#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# import.sh — Import manually-created dev resources into Terraform state.
#
# Run this ONCE before your first `terraform apply` in this directory.
# After import, Terraform owns the resources and apply will manage them.
#
# Usage:
#   cd modules/mapper/deploy/terraform/aws-dev
#   cp terraform.tfvars.example terraform.tfvars  # fill in secrets
#   terraform init
#   ./import.sh
#   terraform plan                                # verify no unexpected changes
#   terraform apply
# ---------------------------------------------------------------------------

set -euo pipefail

LAMBDA_NAME="pdf-autofiller-mapper-dev"
ECR_REPO="pdf-autofiller-mapper-lambda-dev"
IAM_ROLE="${LAMBDA_NAME}-role"
LOG_GROUP="/aws/lambda/${LAMBDA_NAME}"

echo "==> Importing ECR repository: ${ECR_REPO}"
terraform import aws_ecr_repository.mapper "${ECR_REPO}"

echo "==> Importing Lambda function: ${LAMBDA_NAME}"
terraform import aws_lambda_function.mapper "${LAMBDA_NAME}"

echo "==> Importing CloudWatch log group: ${LOG_GROUP}"
terraform import aws_cloudwatch_log_group.mapper "${LOG_GROUP}" || \
  echo "    (log group not found — Terraform will create it on apply)"

echo ""
echo "==> IAM role import (only if role '${IAM_ROLE}' already exists):"
echo "    If the Lambda was created manually, the role name may differ."
echo "    Check the Lambda's role in the AWS console, then run:"
echo ""
echo "    terraform import aws_iam_role.lambda <actual-role-name>"
echo "    terraform import aws_iam_role_policy.lambda_permissions <actual-role-name>:<policy-name>"
echo ""
echo "    If the role does NOT exist yet, skip this — Terraform will create it on apply."
echo ""
echo "==> Import complete. Run: terraform plan"
