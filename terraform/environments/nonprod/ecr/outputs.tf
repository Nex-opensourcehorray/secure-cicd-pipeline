output "repository_name" {
  description = "Name of the private ECR repository."
  value       = module.ecr.repository_name
}

output "repository_arn" {
  description = "ARN supplied to the Management identity root after review."
  value       = module.ecr.repository_arn
}

output "repository_url" {
  description = "URL used to tag and push container images."
  value       = module.ecr.repository_url
}
