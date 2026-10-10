locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Stage       = "8"
  }

  ecr_repository_arn = "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.ecr_repository_name}"
}

module "ecs" {
  source = "../../../modules/ecs"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  aws_account_id     = var.aws_account_id
  ecr_repository_arn = local.ecr_repository_arn
  log_group_name     = var.log_group_name
  log_retention_days = 14
  tags               = local.common_tags
}

module "network" {
  source = "../../../modules/network"

  project_name               = var.project_name
  environment                = var.environment
  aws_region                 = var.aws_region
  aws_account_id             = var.aws_account_id
  vpc_cidr                   = var.vpc_cidr
  availability_zones         = var.availability_zones
  public_subnet_cidrs        = var.public_subnet_cidrs
  private_subnet_cidrs       = var.private_subnet_cidrs
  ecr_repository_arn         = local.ecr_repository_arn
  log_group_name             = var.log_group_name
  runtime_execution_role_arn = module.ecs.execution_role_arn
  tags                       = local.common_tags
}

module "alb" {
  source = "../../../modules/alb"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = module.network.public_subnet_ids
  alb_security_group_id = module.network.alb_security_group_id
  tags                  = local.common_tags
}
