locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    AccountRole = "NonProdIdentity"
  }
}

data "aws_iam_policy_document" "management_broker_assume_role" {
  statement {
    sid     = "AllowExactManagementBroker"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.management_broker_role_arn]
    }
  }
}

resource "aws_iam_role" "ecr_publisher" {
  name                 = var.role_name
  description          = "Allows the exact Management broker role to publish to one NonProd ECR repository."
  assume_role_policy   = data.aws_iam_policy_document.management_broker_assume_role.json
  max_session_duration = 3600

  tags = local.common_tags
}

data "aws_iam_policy_document" "ecr_publish" {
  statement {
    sid       = "GetECRAuthorizationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "PublishToExactRepository"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [var.ecr_repository_arn]
  }
}

resource "aws_iam_policy" "ecr_publish" {
  name        = "${var.role_name}-policy"
  description = "Least-privilege same-account publishing permissions for secure-cicd-demo."
  policy      = data.aws_iam_policy_document.ecr_publish.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecr_publish" {
  role       = aws_iam_role.ecr_publisher.name
  policy_arn = aws_iam_policy.ecr_publish.arn
}
