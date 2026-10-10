output "github_actions_role_arn" {
  description = "ARN of the Management broker role used by GitHub Actions OIDC."
  value       = module.iam.github_actions_role_arn
}

output "github_oidc_provider_arn" {
  description = "ARN of the account-level GitHub OIDC provider."
  value       = module.iam.github_oidc_provider_arn
}

output "github_oidc_subject" {
  description = "Exact GitHub branch subject accepted by the role trust policy."
  value       = module.iam.trusted_subject
}
