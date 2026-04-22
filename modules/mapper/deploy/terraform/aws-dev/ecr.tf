# ---------------------------------------------------------------------------
# ECR — dev container image repository
#
# This repo was created manually as "pdf-autofiller-mapper-lambda-dev".
# Set ecr_repository_name = "pdf-autofiller-mapper-lambda-dev" in terraform.tfvars
# then run: terraform import aws_ecr_repository.mapper pdf-autofiller-mapper-lambda-dev
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "mapper" {
  name                 = local.ecr_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "mapper" {
  repository = aws_ecr_repository.mapper.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 images (dev — fewer than prod)"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}
