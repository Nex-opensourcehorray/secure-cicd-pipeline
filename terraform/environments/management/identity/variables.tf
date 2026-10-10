variable "aws_region" {
  description = "Project workload Region used for provider operations and ECR ARN validation."
  type        = string
  default     = "ap-southeast-1"

  validation {
    condition     = var.aws_region == "ap-southeast-1"
    error_message = "Stage 7 uses ap-southeast-1; the IAM Identity Center SSO Region is separate."
  }
}

variable "project_name" {
  description = "Short project identifier used for names and tags."
  type        = string
  default     = "secure-cicd-pipeline"

  validation {
    condition     = length(trimspace(var.project_name)) > 0 && length(var.project_name) <= 24
    error_message = "project_name must contain between 1 and 24 characters."
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

variable "nonprod_publisher_role_arn" {
  description = "Reviewed ARN of the only NonProd ECR publisher role the broker may assume."
  type        = string

  validation {
    condition     = var.nonprod_publisher_role_arn == "arn:aws:iam::119033255630:role/secure-cicd-pipeline-nonprod-ecr-publisher"
    error_message = "nonprod_publisher_role_arn must identify the reviewed NonProd ECR publisher role."
  }
}

variable "github_owner" {
  description = "GitHub repository owner name."
  type        = string
  default     = "Nex-opensourcehorray"

  validation {
    condition     = var.github_owner == "Nex-opensourcehorray"
    error_message = "This identity root trusts only Nex-opensourcehorray."
  }
}

variable "github_owner_id" {
  description = "Immutable numeric GitHub repository owner ID."
  type        = string
  default     = "82328818"

  validation {
    condition     = var.github_owner_id == "82328818"
    error_message = "github_owner_id must match the verified owner metadata."
  }
}

variable "github_repository" {
  description = "GitHub repository name."
  type        = string
  default     = "secure-cicd-pipeline"

  validation {
    condition     = var.github_repository == "secure-cicd-pipeline"
    error_message = "This identity root trusts only secure-cicd-pipeline."
  }
}

variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID."
  type        = string
  default     = "1409968457"

  validation {
    condition     = var.github_repository_id == "1409968457"
    error_message = "github_repository_id must match the verified repository metadata."
  }
}

variable "github_branch" {
  description = "Only this GitHub branch may assume the publishing role."
  type        = string
  default     = "main"

  validation {
    condition     = var.github_branch == "main"
    error_message = "This identity root trusts only the main branch."
  }
}
