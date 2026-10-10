resource "aws_ecr_repository" "this" {
  name                 = var.repository_name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  # Keep scanning repository-scoped so this module does not change shared
  # registry-wide scanning rules in an existing AWS account.
  image_scanning_configuration {
    scan_on_push = true
  }

  # AWS-managed KMS encryption avoids introducing a customer-managed key.
  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after ${var.untagged_image_retention_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_image_retention_days
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Retain the ${var.max_tagged_images} most recent tagged images"
        selection = {
          tagStatus      = "tagged"
          tagPatternList = ["*"]
          countType      = "imageCountMoreThan"
          countNumber    = var.max_tagged_images
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

data "aws_iam_policy_document" "cross_account_publish" {
  #checkov:skip=CKV_AWS_109:ECR anti-lockout requires same-account Get/Set/DeleteRepositoryPolicy; this attached policy grants no image, repository, or lifecycle administration.
  #checkov:skip=CKV_AWS_111:ECR repository policies require Resource "*" and are scoped by the attached repository.
  #checkov:skip=CKV_AWS_356:ECR repository policies require Resource "*" and are scoped by the attached repository.
  statement {
    sid    = "AllowManagementPublisherPush"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    # ECR repository policies are attached to one repository and use Resource
    # "*"; the Management identity policy separately scopes the exact ARN.
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::191125774822:root"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:PrincipalArn"
      values   = [var.publisher_role_arn]
    }
  }

  statement {
    sid       = "AllowManagementPublisherDescribe"
    effect    = "Allow"
    actions   = ["ecr:DescribeImages"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::191125774822:root"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:PrincipalArn"
      values   = [var.publisher_role_arn]
    }
  }

  statement {
    sid    = "AllowNonProdRepositoryPolicyAdministration"
    effect = "Allow"
    actions = [
      "ecr:DeleteRepositoryPolicy",
      "ecr:GetRepositoryPolicy",
      "ecr:SetRepositoryPolicy",
    ]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::119033255630:root"]
    }
  }
}

resource "aws_ecr_repository_policy" "publisher" {
  repository = aws_ecr_repository.this.name
  policy     = data.aws_iam_policy_document.cross_account_publish.json
}
