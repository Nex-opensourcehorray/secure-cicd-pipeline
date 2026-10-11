output "role_arn" {
  description = "ARN of the dedicated Management deployment broker role."
  value       = aws_iam_role.this.arn
}

output "policy_arn" {
  description = "ARN of the broker's exact cross-account AssumeRole policy."
  value       = aws_iam_policy.this.arn
}

output "trusted_subject" {
  description = "Exact planned GitHub Environment OIDC subject trusted by the broker."
  value       = local.github_subject
}
