locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

module "ecr" {
  source = "../../../modules/ecr"

  repository_name               = var.ecr_repository_name
  max_tagged_images             = 20
  untagged_image_retention_days = 14
  tags                          = local.common_tags
}
