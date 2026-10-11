output "role_arn" {
  description = "ARN of the dedicated NonProd ECS deployment role."
  value       = aws_iam_role.this.arn
}

output "policy_arn" {
  description = "ARN of the least-privilege NonProd ECS deployment policy."
  value       = aws_iam_policy.this.arn
}

output "trusted_management_broker_arn" {
  description = "Exact Management deployment broker trusted by the role."
  value       = var.management_deployment_broker_role_arn
}
