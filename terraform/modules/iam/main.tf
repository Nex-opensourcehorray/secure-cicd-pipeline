locals {
  github_subject = "repo:${var.github_owner}@${var.github_owner_id}/${var.github_repository}@${var.github_repository_id}:ref:refs/heads/${var.github_branch}"
  github_ref     = "refs/heads/${var.github_branch}"
}

# IAM OIDC providers are account-level singletons by URL. If this provider
# already exists in the target account, import it into this resource before
# applying rather than attempting to create a duplicate.
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  tags = var.tags
}

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    sid     = "GitHubActionsAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.github_subject]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:repository_owner_id"
      values   = [var.github_owner_id]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:repository_id"
      values   = [var.github_repository_id]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:ref"
      values   = [local.github_ref]
    }
  }
}

# The legacy Terraform address, AWS name, and description are intentionally
# retained so the deployed role is not replaced during the broker conversion.
resource "aws_iam_role" "github_ecr_publisher" {
  name                 = var.role_name
  description          = "Allows trusted GitHub Actions runs to publish images to one ECR repository."
  assume_role_policy   = data.aws_iam_policy_document.github_assume_role.json
  max_session_duration = 3600

  tags = var.tags
}

data "aws_iam_policy_document" "ecr_publish" {
  statement {
    sid    = "AssumeNonProdECRPublisher"
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]
    resources = [var.nonprod_publisher_role_arn]
  }
}

# This legacy resource address, name, and description are also retained so the
# existing managed policy is updated in place instead of replaced.
resource "aws_iam_policy" "ecr_publish" {
  name        = "${var.role_name}-policy"
  description = "Least-privilege permissions to publish images to one ECR repository."
  policy      = data.aws_iam_policy_document.ecr_publish.json

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecr_publish" {
  role       = aws_iam_role.github_ecr_publisher.name
  policy_arn = aws_iam_policy.ecr_publish.arn
}
