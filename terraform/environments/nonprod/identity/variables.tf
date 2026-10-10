variable "aws_region" {
  description = "AWS Region used for NonProd identity operations and ECR ARN validation."
  type        = string
  default     = "ap-southeast-1"

  validation {
    condition     = var.aws_region == "ap-southeast-1"
    error_message = "Stage 7 NonProd identity resources must use ap-southeast-1."
  }
}

variable "project_name" {
  description = "Short project identifier used for names and tags."
  type        = string
  default     = "secure-cicd-pipeline"

  validation {
    condition     = var.project_name == "secure-cicd-pipeline"
    error_message = "This identity root is restricted to secure-cicd-pipeline."
  }
}

variable "environment" {
  description = "Workload environment authorized for publication."
  type        = string
  default     = "nonprod"

  validation {
    condition     = var.environment == "nonprod"
    error_message = "This identity root is restricted to nonprod publication."
  }
}

variable "role_name" {
  description = "Name of the dedicated NonProd ECR publisher role."
  type        = string
  default     = "secure-cicd-pipeline-nonprod-ecr-publisher"

  validation {
    condition     = var.role_name == "secure-cicd-pipeline-nonprod-ecr-publisher"
    error_message = "role_name must match the reviewed NonProd publisher role name."
  }
}

variable "management_broker_role_arn" {
  description = "Exact Management role trusted to assume the NonProd publisher role."
  type        = string

  validation {
    condition     = var.management_broker_role_arn == "arn:aws:iam::191125774822:role/secure-cicd-pipeline-nonprod-github-ecr-publisher"
    error_message = "management_broker_role_arn must match the existing reviewed Management broker role."
  }
}

variable "ecr_repository_arn" {
  description = "Exact NonProd ECR repository the publisher role may access."
  type        = string

  validation {
    condition     = var.ecr_repository_arn == "arn:aws:ecr:ap-southeast-1:119033255630:repository/secure-cicd-demo"
    error_message = "ecr_repository_arn must match the reviewed NonProd secure-cicd-demo repository."
  }
}
