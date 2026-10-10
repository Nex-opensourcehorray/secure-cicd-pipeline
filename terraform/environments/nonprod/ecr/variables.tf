variable "aws_region" {
  description = "AWS Region containing the non-production ECR repository."
  type        = string
  default     = "ap-southeast-1"

  validation {
    condition     = var.aws_region == "ap-southeast-1"
    error_message = "Stage 7 ECR resources must use ap-southeast-1."
  }
}

variable "project_name" {
  description = "Short project identifier used for tags."
  type        = string
  default     = "secure-cicd-pipeline"

  validation {
    condition     = length(trimspace(var.project_name)) > 0 && length(var.project_name) <= 24
    error_message = "project_name must contain between 1 and 24 characters."
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

variable "ecr_repository_name" {
  description = "Name of the private ECR repository."
  type        = string
  default     = "secure-cicd-demo"

  validation {
    condition     = var.ecr_repository_name == "secure-cicd-demo"
    error_message = "Stage 7 is scoped to the secure-cicd-demo repository."
  }
}

variable "publisher_role_arn" {
  description = "Verified Management-account IAM role authorized by the NonProd ECR repository policy."
  type        = string

  validation {
    condition     = var.publisher_role_arn == "arn:aws:iam::191125774822:role/secure-cicd-pipeline-nonprod-github-ecr-publisher"
    error_message = "publisher_role_arn must be the verified Management GitHub ECR publisher role ARN."
  }
}
