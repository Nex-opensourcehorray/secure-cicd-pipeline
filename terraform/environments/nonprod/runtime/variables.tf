variable "aws_region" {
  description = "AWS Region containing the non-production runtime foundation."
  type        = string
  default     = "ap-southeast-1"

  validation {
    condition     = var.aws_region == "ap-southeast-1"
    error_message = "Stage 8 runtime resources must use ap-southeast-1."
  }
}

variable "aws_account_id" {
  description = "NonProd AWS account ID allowed by the provider and endpoint policies."
  type        = string
  default     = "119033255630"

  validation {
    condition     = var.aws_account_id == "119033255630"
    error_message = "This root is restricted to the reviewed NonProd AWS account."
  }
}

variable "project_name" {
  description = "Project identifier used for names and tags."
  type        = string
  default     = "secure-cicd-pipeline"

  validation {
    condition     = var.project_name == "secure-cicd-pipeline"
    error_message = "Stage 8 is scoped to secure-cicd-pipeline."
  }
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "nonprod"

  validation {
    condition     = var.environment == "nonprod"
    error_message = "This root is restricted to the nonprod environment."
  }
}

variable "vpc_cidr" {
  description = "Reviewed non-overlapping CIDR block for the runtime VPC."
  type        = string
  default     = "10.42.0.0/16"

  validation {
    condition     = var.vpc_cidr == "10.42.0.0/16"
    error_message = "Stage 8.1 is scoped to VPC CIDR 10.42.0.0/16."
  }
}

variable "availability_zones" {
  description = "Reviewed standard Availability Zones for the runtime network."
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]

  validation {
    condition     = length(var.availability_zones) == 2 && var.availability_zones[0] == "ap-southeast-1a" && var.availability_zones[1] == "ap-southeast-1b"
    error_message = "Stage 8.1 must use the reviewed ap-southeast-1a and ap-southeast-1b zones."
  }
}

variable "public_subnet_cidrs" {
  description = "Reviewed CIDRs for the two public ALB subnets."
  type        = list(string)
  default     = ["10.42.0.0/24", "10.42.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2 && var.public_subnet_cidrs[0] == "10.42.0.0/24" && var.public_subnet_cidrs[1] == "10.42.1.0/24"
    error_message = "Stage 8.1 public subnets must use the reviewed CIDR layout."
  }
}

variable "private_subnet_cidrs" {
  description = "Reviewed CIDRs for the two private task and endpoint subnets."
  type        = list(string)
  default     = ["10.42.10.0/24", "10.42.11.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2 && var.private_subnet_cidrs[0] == "10.42.10.0/24" && var.private_subnet_cidrs[1] == "10.42.11.0/24"
    error_message = "Stage 8.1 private subnets must use the reviewed CIDR layout."
  }
}

variable "ecr_repository_name" {
  description = "Existing Stage 7 ECR repository referenced by endpoint policies only."
  type        = string
  default     = "secure-cicd-demo"

  validation {
    condition     = var.ecr_repository_name == "secure-cicd-demo"
    error_message = "Stage 8 runtime image pulls are scoped to secure-cicd-demo."
  }
}

variable "future_log_group_name" {
  description = "Future Stage 8.2 CloudWatch log group referenced by endpoint policy only."
  type        = string
  default     = "/ecs/secure-cicd-pipeline/nonprod"

  validation {
    condition     = var.future_log_group_name == "/ecs/secure-cicd-pipeline/nonprod"
    error_message = "Stage 8 runtime logging is scoped to /ecs/secure-cicd-pipeline/nonprod."
  }
}
