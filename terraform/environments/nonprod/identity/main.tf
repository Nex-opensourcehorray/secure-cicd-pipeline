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

module "ecs_deployer" {
  source = "../../../modules/ecs-deployer"

  role_name                             = var.ecs_deployer_role_name
  management_deployment_broker_role_arn = var.management_deployment_broker_role_arn
  ecr_repository_arn                    = var.ecr_repository_arn
  ecs_cluster_arn                       = var.ecs_cluster_arn
  ecs_service_arn                       = var.ecs_service_arn
  ecs_task_definition_arn_pattern       = var.ecs_task_definition_arn_pattern
  ecs_task_arn_pattern                  = var.ecs_task_arn_pattern
  ecs_execution_role_arn                = var.ecs_execution_role_arn
  tags                                  = local.common_tags
}
