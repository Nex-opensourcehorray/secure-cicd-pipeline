output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions broker role."
  value       = aws_iam_role.github_ecr_publisher.arn
}

output "github_oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider."
  value       = aws_iam_openid_connect_provider.github.arn
}

output "trusted_subject" {
  description = "Exact immutable GitHub OIDC subject trusted by the role."
  value       = local.github_subject
}
