output "ecr_publisher_role_arn" {
  description = "ARN of the dedicated NonProd ECR publisher role."
  value       = aws_iam_role.ecr_publisher.arn
}

output "ecr_publisher_policy_arn" {
  description = "ARN of the least-privilege NonProd ECR publisher policy."
  value       = aws_iam_policy.ecr_publish.arn
}

output "trusted_management_broker_role_arn" {
  description = "Exact Management broker role trusted by the publisher role."
  value       = var.management_broker_role_arn
}
