output "flow_log_id" {
  description = "ID of the Stage 8 VPC Flow Log."
  value       = aws_flow_log.this.id
}

output "flow_log_group_name" {
  description = "Name of the dedicated VPC Flow Logs log group."
  value       = aws_cloudwatch_log_group.vpc_flow.name
}

output "flow_log_role_arn" {
  description = "ARN of the dedicated VPC Flow Logs delivery role."
  value       = aws_iam_role.flow_log_delivery.arn
}

output "sns_topic_arn" {
  description = "ARN of the runtime and security alert integration topic."
  value       = aws_sns_topic.alerts.arn
}

output "unhealthy_target_alarm_name" {
  description = "Name of the unhealthy-target CloudWatch alarm."
  value       = aws_cloudwatch_metric_alarm.unhealthy_target.alarm_name
}

output "target_5xx_alarm_name" {
  description = "Name of the target HTTP 5XX CloudWatch alarm."
  value       = aws_cloudwatch_metric_alarm.target_5xx.alarm_name
}

output "cpu_alarm_name" {
  description = "Name of the ECS CPU utilization alarm."
  value       = aws_cloudwatch_metric_alarm.ecs_cpu_high.alarm_name
}

output "memory_alarm_name" {
  description = "Name of the ECS memory utilization alarm."
  value       = aws_cloudwatch_metric_alarm.ecs_memory_high.alarm_name
}

output "ecs_failure_rule_arn" {
  description = "ARN of the failure-oriented ECS stopped-task EventBridge rule."
  value       = aws_cloudwatch_event_rule.ecs_failure.arn
}

output "inspector_rule_arn" {
  description = "ARN of the project ECR HIGH/CRITICAL Inspector finding rule."
  value       = aws_cloudwatch_event_rule.inspector_findings.arn
}
