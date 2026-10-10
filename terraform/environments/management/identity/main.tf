locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    AccountRole = "ManagementIdentity"
  }
}

module "iam" {
  source = "../../../modules/iam"

  role_name                  = "${var.project_name}-${var.environment}-github-ecr-publisher"
  nonprod_publisher_role_arn = var.nonprod_publisher_role_arn
  github_owner               = var.github_owner
  github_owner_id            = var.github_owner_id
  github_repository          = var.github_repository
  github_repository_id       = var.github_repository_id
  github_branch              = var.github_branch
  tags                       = local.common_tags
}
