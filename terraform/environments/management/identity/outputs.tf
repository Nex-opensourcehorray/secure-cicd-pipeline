output "github_actions_role_arn" {
  description = "ARN used by GitHub Actions for OIDC role assumption."
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
