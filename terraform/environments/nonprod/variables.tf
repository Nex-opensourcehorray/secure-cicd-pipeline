variable "aws_region" {
  description = "AWS Region in which the non-production resources will be managed."
  type        = string

  validation {
    condition     = length(trimspace(var.aws_region)) > 0
    error_message = "aws_region must not be empty."
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
  description = "Deployment environment label."
  type        = string
  default     = "nonprod"

  validation {
    condition     = length(trimspace(var.environment)) > 0 && length(var.environment) <= 12
    error_message = "environment must contain between 1 and 12 characters."
  }
}

variable "ecr_repository_name" {
  description = "Name of the private ECR repository."
  type        = string
  default     = "secure-cicd-demo"
}

variable "github_owner" {
  description = "GitHub repository owner name."
  type        = string

  validation {
    condition     = length(trimspace(var.github_owner)) > 0
    error_message = "github_owner must not be empty."
  }
}

variable "github_owner_id" {
  description = "Immutable numeric GitHub repository owner ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_owner_id))
    error_message = "github_owner_id must be supplied after the GitHub repository is created."
  }
}

variable "github_repository" {
  description = "GitHub repository name."
  type        = string
  default     = "secure-cicd-pipeline"
}

variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must be supplied after the GitHub repository is created."
  }
}

variable "github_branch" {
  description = "Only this GitHub branch may assume the publishing role."
  type        = string
  default     = "main"

  validation {
    condition     = length(trimspace(var.github_branch)) > 0 && !can(regex("[?*]", var.github_branch))
    error_message = "github_branch must be an exact non-empty branch name without wildcards."
  }
}
