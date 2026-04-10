# ---------------------------------------------------------------------------
# ECR — container image repository for the mapper Lambda
# Same image runs locally (DEPLOY_MODE=fastapi) and on Lambda (DEPLOY_MODE=lambda)
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "mapper" {
  name                 = local.name
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
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
