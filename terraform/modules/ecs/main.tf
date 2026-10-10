locals {
  name_prefix           = "${var.project_name}-${var.environment}"
  cluster_name          = local.name_prefix
  execution_role_name   = "${local.name_prefix}-ecs-execution"
  execution_policy_name = "${local.name_prefix}-ecs-execution-policy"
  log_stream_arn        = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:${var.log_group_name}:*"
}

data "aws_iam_policy_document" "execution_assume_role" {
  statement {
    sid     = "EcsTaskExecutionAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }

    # ECS does not currently support restricting task-role trust to a specific
    # cluster ARN, so AWS recommends the regional/account-wide ECS wildcard.
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:*"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name                 = local.execution_role_name
  description          = "Allows the ECS and Fargate agents to pull the approved ECR image and deliver logs"
  path                 = "/"
  assume_role_policy   = data.aws_iam_policy_document.execution_assume_role.json
  max_session_duration = 3600

  tags = merge(var.tags, {
    Name = local.execution_role_name
  })
}

resource "aws_cloudwatch_log_group" "this" {
  #checkov:skip=CKV_AWS_158:A dedicated CMK is not approved for this NonProd stage; CloudWatch Logs service encryption remains in use.
  #checkov:skip=CKV_AWS_338:Fourteen-day retention is the explicitly approved NonProd cost and observability posture.
  name              = var.log_group_name
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = var.log_group_name
  })
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid       = "EcrAuthorization"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "EcrRepositoryPull"
    effect = "Allow"
    # AWS custom ECS pull guidance requires these repository actions;
    # BatchCheckLayerAvailability is not required for this runtime path.
    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [var.ecr_repository_arn]
  }

  statement {
    sid    = "CloudWatchLogDelivery"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [local.log_stream_arn]
  }
}

resource "aws_iam_policy" "execution" {
  name        = local.execution_policy_name
  description = "Least-privilege ECR pull and CloudWatch Logs delivery for the ECS execution role"
  path        = "/"
  policy      = data.aws_iam_policy_document.execution.json

  tags = merge(var.tags, {
    Name = local.execution_policy_name
  })
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = aws_iam_policy.execution.arn
}

resource "aws_ecs_cluster" "this" {
  #checkov:skip=CKV_AWS_65:Container Insights is explicitly deferred for initial NonProd cost control; standard ECS metrics remain available.
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = merge(var.tags, {
    Name = local.cluster_name
  })
}
