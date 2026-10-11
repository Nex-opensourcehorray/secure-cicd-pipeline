locals {
  github_subject = "repo:${var.github_owner}@${var.github_owner_id}/${var.github_repository}@${var.github_repository_id}:environment:${var.github_environment}"
  github_ref     = "refs/heads/${var.github_branch}"
}

# SECURITY GATE: Do not apply this role until a real OIDC token issued to the
# GitHub Environment named by var.github_environment has been captured and all
# claims below have been verified. A mismatch requires separate review; it must
# not be resolved by weakening this trust policy.
data "aws_iam_policy_document" "github_assume_role" {
  statement {
    sid     = "GitHubEnvironmentAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.github_oidc_provider_arn]
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

resource "aws_iam_role" "this" {
  name                 = var.role_name
  description          = "Allows the approved GitHub nonprod Environment to enter the dedicated ECS deployment role."
  path                 = "/"
  assume_role_policy   = data.aws_iam_policy_document.github_assume_role.json
  max_session_duration = 3600

  tags = merge(var.tags, {
    Name = var.role_name
  })
}

data "aws_iam_policy_document" "assume_nonprod_deployer" {
  statement {
    sid       = "AssumeExactNonProdECSDeployer"
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = [var.nonprod_deployer_role_arn]
  }
}

resource "aws_iam_policy" "this" {
  name        = "${var.role_name}-policy"
  description = "Allows only role chaining to the exact NonProd ECS deployer."
  path        = "/"
  policy      = data.aws_iam_policy_document.assume_nonprod_deployer.json

  tags = merge(var.tags, {
    Name = "${var.role_name}-policy"
  })
}

resource "aws_iam_role_policy_attachment" "this" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.this.arn
}
