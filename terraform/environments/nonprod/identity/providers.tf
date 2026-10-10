provider "aws" {
  region              = var.aws_region
  allowed_account_ids = ["119033255630"]

  default_tags {
    tags = local.common_tags
  }
}
