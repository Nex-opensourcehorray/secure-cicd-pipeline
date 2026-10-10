output "cluster_name" {
  description = "Name of the dedicated ECS cluster."
  value       = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  description = "ARN of the dedicated ECS cluster."
  value       = aws_ecs_cluster.this.arn
}

output "execution_role_name" {
  description = "Name of the dedicated ECS task execution role."
  value       = aws_iam_role.execution.name
}

output "execution_role_arn" {
  description = "ARN of the dedicated ECS task execution role."
  value       = aws_iam_role.execution.arn
}

output "execution_policy_arn" {
  description = "ARN of the custom least-privilege ECS execution policy."
  value       = aws_iam_policy.execution.arn
}

output "log_group_name" {
  description = "Name of the ECS application log group."
  value       = aws_cloudwatch_log_group.this.name
}

output "log_group_arn" {
  description = "ARN of the ECS application log group."
  value       = aws_cloudwatch_log_group.this.arn
}
