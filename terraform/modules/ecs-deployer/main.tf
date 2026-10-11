data "aws_iam_policy_document" "management_broker_assume_role" {
  statement {
    sid     = "AllowExactManagementDeploymentBroker"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.management_deployment_broker_role_arn]
    }
  }
}

resource "aws_iam_role" "this" {
  name                 = var.role_name
  description          = "Allows the exact Management deployment broker to promote one approved digest to one NonProd ECS service."
  path                 = "/"
  assume_role_policy   = data.aws_iam_policy_document.management_broker_assume_role.json
  max_session_duration = 3600

  tags = merge(var.tags, {
    Name = var.role_name
  })
}

data "aws_iam_policy_document" "deployment" {
  statement {
    sid    = "ReadExactECRRepositoryMetadata"
    effect = "Allow"
    actions = [
      "ecr:DescribeImages",
      "ecr:DescribeImageScanFindings",
    ]
    resources = [var.ecr_repository_arn]
  }

  statement {
    sid       = "DescribeExactECSService"
    effect    = "Allow"
    actions   = ["ecs:DescribeServices"]
    resources = [var.ecs_service_arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.ecs_cluster_arn]
    }
  }

  # DescribeTaskDefinition does not support resource-level permissions. The
  # Stage 9 workflow must validate the exact family and all runtime invariants.
  statement {
    sid       = "DescribeTaskDefinitionForValidation"
    effect    = "Allow"
    actions   = ["ecs:DescribeTaskDefinition"]
    resources = ["*"]
  }

  statement {
    sid       = "RegisterGuardedTaskDefinitionRevision"
    effect    = "Allow"
    actions   = ["ecs:RegisterTaskDefinition"]
    resources = [var.ecs_task_definition_arn_pattern]

    # This is an ArrayOfString condition key. Requiring the key and applying
    # ForAllValues prevents any compatibility other than FARGATE.
    condition {
      test     = "ForAllValues:StringEquals"
      variable = "ecs:compute-compatibility"
      values   = ["FARGATE"]
    }

    condition {
      test     = "Null"
      variable = "ecs:compute-compatibility"
      values   = ["false"]
    }

    # AWS defines ecs:privileged as String, despite the ECS API field being a
    # boolean. The workflow separately validates every container definition.
    condition {
      test     = "StringEquals"
      variable = "ecs:privileged"
      values   = ["false"]
    }

    condition {
      test     = "NumericEquals"
      variable = "ecs:task-cpu"
      values   = ["256"]
    }

    condition {
      test     = "NumericEquals"
      variable = "ecs:task-memory"
      values   = ["512"]
    }
  }

  statement {
    sid       = "PassExactExecutionRoleToECSTasks"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [var.ecs_execution_role_arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid       = "UpdateExactECSServiceRevision"
    effect    = "Allow"
    actions   = ["ecs:UpdateService"]
    resources = [var.ecs_service_arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.ecs_cluster_arn]
    }

    condition {
      test     = "ArnLike"
      variable = "ecs:task-definition"
      values   = [var.ecs_task_definition_arn_pattern]
    }
  }

  # ListTasks cannot be scoped to Fargate task resources. The exact cluster is
  # required in the request context and the workflow supplies the exact service.
  statement {
    sid       = "ListTasksInExactCluster"
    effect    = "Allow"
    actions   = ["ecs:ListTasks"]
    resources = ["*"]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.ecs_cluster_arn]
    }
  }

  statement {
    sid       = "DescribeTasksInExactCluster"
    effect    = "Allow"
    actions   = ["ecs:DescribeTasks"]
    resources = [var.ecs_task_arn_pattern]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.ecs_cluster_arn]
    }
  }

  # DescribeTargetHealth does not support resource-level permissions. The
  # workflow must derive and validate the exact approved target group.
  statement {
    sid       = "DescribeValidatedTargetHealth"
    effect    = "Allow"
    actions   = ["elasticloadbalancing:DescribeTargetHealth"]
    resources = ["*"]
  }

  # DescribeSecurityGroups does not support resource-level permissions. The
  # workflow must request only and validate the approved ALB security group.
  statement {
    sid       = "DescribeValidatedALBSecurityGroup"
    effect    = "Allow"
    actions   = ["ec2:DescribeSecurityGroups"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "this" {
  name        = "${var.role_name}-policy"
  description = "Least-privilege metadata read and deployment permissions for one NonProd ECS service."
  path        = "/"
  policy      = data.aws_iam_policy_document.deployment.json

  tags = merge(var.tags, {
    Name = "${var.role_name}-policy"
  })
}

resource "aws_iam_role_policy_attachment" "this" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.this.arn
}
