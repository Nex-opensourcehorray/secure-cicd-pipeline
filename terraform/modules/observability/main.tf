locals {
  name_prefix         = "${var.project_name}-${var.environment}"
  flow_log_group_name = "/aws/vpc/flowlogs/${var.project_name}/${var.environment}"
  flow_log_role_name  = "${local.name_prefix}-vpc-flow-logs"
  alert_topic_name    = "${local.name_prefix}-runtime-alerts"

  unhealthy_target_alarm_name = "${local.name_prefix}-alb-unhealthy-targets"
  target_5xx_alarm_name       = "${local.name_prefix}-target-5xx"
  cpu_alarm_name              = "${local.name_prefix}-ecs-cpu-high"
  memory_alarm_name           = "${local.name_prefix}-ecs-memory-high"
  ecs_failure_rule_name       = "${local.name_prefix}-ecs-task-failure"
  inspector_rule_name         = "${local.name_prefix}-inspector-high-critical"

  alarm_arns = [
    "arn:aws:cloudwatch:${var.aws_region}:${var.aws_account_id}:alarm:${local.unhealthy_target_alarm_name}",
    "arn:aws:cloudwatch:${var.aws_region}:${var.aws_account_id}:alarm:${local.target_5xx_alarm_name}",
    "arn:aws:cloudwatch:${var.aws_region}:${var.aws_account_id}:alarm:${local.cpu_alarm_name}",
    "arn:aws:cloudwatch:${var.aws_region}:${var.aws_account_id}:alarm:${local.memory_alarm_name}",
  ]

  flow_log_format = join(" ", [
    "$${version}",
    "$${account-id}",
    "$${interface-id}",
    "$${srcaddr}",
    "$${dstaddr}",
    "$${srcport}",
    "$${dstport}",
    "$${protocol}",
    "$${packets}",
    "$${bytes}",
    "$${start}",
    "$${end}",
    "$${action}",
    "$${log-status}",
    "$${vpc-id}",
    "$${subnet-id}",
    "$${instance-id}",
    "$${tcp-flags}",
    "$${flow-direction}",
    "$${pkt-srcaddr}",
    "$${pkt-dstaddr}",
  ])
}

resource "aws_cloudwatch_log_group" "vpc_flow" {
  #checkov:skip=CKV_AWS_158:A dedicated CMK is not approved for this NonProd stage; CloudWatch Logs service encryption remains in use.
  #checkov:skip=CKV_AWS_338:Fourteen-day retention matches the approved NonProd application-log retention and cost posture.
  name              = local.flow_log_group_name
  retention_in_days = var.flow_log_retention_days

  tags = merge(var.tags, {
    Name = local.flow_log_group_name
  })
}

data "aws_iam_policy_document" "flow_log_assume_role" {
  statement {
    sid     = "VpcFlowLogsAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:ec2:${var.aws_region}:${var.aws_account_id}:vpc-flow-log/*"]
    }
  }
}

resource "aws_iam_role" "flow_log_delivery" {
  name                 = local.flow_log_role_name
  description          = "Allows VPC Flow Logs to publish Stage 8 network metadata to the dedicated log group"
  path                 = "/"
  assume_role_policy   = data.aws_iam_policy_document.flow_log_assume_role.json
  max_session_duration = 3600

  tags = merge(var.tags, {
    Name = local.flow_log_role_name
  })
}

data "aws_iam_policy_document" "flow_log_delivery" {
  statement {
    sid    = "WriteDedicatedFlowLogGroup"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.vpc_flow.arn}:*"]
  }

  # DescribeLogGroups does not support resource-level permissions. Keeping it
  # in a separate read-only statement preserves exact scoping for all writes.
  statement {
    sid       = "DiscoverFlowLogGroup"
    effect    = "Allow"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "flow_log_delivery" {
  #checkov:skip=CKV_AWS_356:logs:DescribeLogGroups requires Resource "*"; all log-write actions are restricted to the dedicated Flow Logs log group ARN.
  name   = "${local.flow_log_role_name}-policy"
  role   = aws_iam_role.flow_log_delivery.id
  policy = data.aws_iam_policy_document.flow_log_delivery.json
}

resource "aws_flow_log" "this" {
  iam_role_arn             = aws_iam_role.flow_log_delivery.arn
  log_destination          = aws_cloudwatch_log_group.vpc_flow.arn
  log_destination_type     = "cloud-watch-logs"
  traffic_type             = "ALL"
  vpc_id                   = var.vpc_id
  max_aggregation_interval = 60
  log_format               = local.flow_log_format

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc-flow-log"
  })

  depends_on = [aws_iam_role_policy.flow_log_delivery]
}

resource "aws_sns_topic" "alerts" {
  #checkov:skip=CKV_AWS_26:The topic carries non-sensitive runtime alert metadata, has no subscriptions, and uses a least-privilege source-restricted policy; a customer-managed KMS key is outside this NonProd scope.
  name = local.alert_topic_name

  tags = merge(var.tags, {
    Name = local.alert_topic_name
  })
}

resource "aws_cloudwatch_event_rule" "ecs_failure" {
  name        = local.ecs_failure_rule_name
  description = "Reports failure-oriented stopped tasks for the Stage 8 ECS service"
  state       = "ENABLED"

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      clusterArn = [var.ecs_cluster_arn]
      group      = ["service:${var.ecs_service_name}"]
      lastStatus = ["STOPPED"]
      stopCode = [
        "EssentialContainerExited",
        "TaskFailedToStart",
      ]
    }
  })

  tags = merge(var.tags, {
    Name = local.ecs_failure_rule_name
  })
}

resource "aws_cloudwatch_event_rule" "inspector_findings" {
  name        = local.inspector_rule_name
  description = "Reports active HIGH and CRITICAL Inspector findings for the project ECR repository"
  state       = "ENABLED"

  event_pattern = jsonencode({
    source      = ["aws.inspector2"]
    detail-type = ["Inspector2 Finding"]
    detail = {
      severity = ["HIGH", "CRITICAL"]
      status   = ["ACTIVE"]
      resources = {
        type = ["AWS_ECR_CONTAINER_IMAGE"]
        details = {
          awsEcrContainerImage = {
            repositoryName = [var.ecr_repository_name]
          }
        }
      }
    }
  })

  tags = merge(var.tags, {
    Name = local.inspector_rule_name
  })
}

data "aws_iam_policy_document" "alerts_topic" {
  statement {
    sid     = "CloudWatchAlarmPublish"
    effect  = "Allow"
    actions = ["sns:Publish"]
    resources = [
      aws_sns_topic.alerts.arn,
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = local.alarm_arns
    }
  }

  statement {
    sid     = "EventBridgeRulePublish"
    effect  = "Allow"
    actions = ["sns:Publish"]
    resources = [
      aws_sns_topic.alerts.arn,
    ]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values = [
        aws_cloudwatch_event_rule.ecs_failure.arn,
        aws_cloudwatch_event_rule.inspector_findings.arn,
      ]
    }
  }
}

resource "aws_sns_topic_policy" "alerts" {
  arn    = aws_sns_topic.alerts.arn
  policy = data.aws_iam_policy_document.alerts_topic.json
}

resource "aws_cloudwatch_event_target" "ecs_failure" {
  rule      = aws_cloudwatch_event_rule.ecs_failure.name
  target_id = "RuntimeAlertsTopic"
  arn       = aws_sns_topic.alerts.arn

  depends_on = [aws_sns_topic_policy.alerts]
}

resource "aws_cloudwatch_event_target" "inspector_findings" {
  rule      = aws_cloudwatch_event_rule.inspector_findings.name
  target_id = "SecurityAlertsTopic"
  arn       = aws_sns_topic.alerts.arn

  depends_on = [aws_sns_topic_policy.alerts]
}

resource "aws_cloudwatch_metric_alarm" "unhealthy_target" {
  alarm_name          = local.unhealthy_target_alarm_name
  alarm_description   = "Stage 8 ALB has one or more unhealthy ECS targets for two consecutive minutes"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  tags = merge(var.tags, {
    Name = local.unhealthy_target_alarm_name
  })

  depends_on = [aws_sns_topic_policy.alerts]
}

resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name          = local.target_5xx_alarm_name
  alarm_description   = "Stage 8 ECS targets returned at least one HTTP 5XX response in five minutes"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  tags = merge(var.tags, {
    Name = local.target_5xx_alarm_name
  })

  depends_on = [aws_sns_topic_policy.alerts]
}

resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = local.cpu_alarm_name
  alarm_description   = "Stage 8 ECS service CPU utilization is at least 80 percent for ten minutes"
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  tags = merge(var.tags, {
    Name = local.cpu_alarm_name
  })

  depends_on = [aws_sns_topic_policy.alerts]
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = local.memory_alarm_name
  alarm_description   = "Stage 8 ECS service memory utilization is at least 80 percent for ten minutes"
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  tags = merge(var.tags, {
    Name = local.memory_alarm_name
  })

  depends_on = [aws_sns_topic_policy.alerts]
}
