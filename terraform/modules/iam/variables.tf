variable "role_name" {
  description = "Name of the GitHub Actions ECR publishing role."
  type        = string

  validation {
    condition     = length(trimspace(var.role_name)) > 0 && length(var.role_name) <= 64
    error_message = "role_name must contain between 1 and 64 characters."
  }
}

variable "ecr_repository_arn" {
  description = "ARN of the single ECR repository the role may publish to."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:ecr:[^:]+:[0-9]{12}:repository/.+$", var.ecr_repository_arn))
    error_message = "ecr_repository_arn must be a valid ECR repository ARN."
  }
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
    error_message = "github_owner_id must be supplied as a numeric GitHub owner ID."
  }
}

variable "github_repository" {
  description = "GitHub repository name."
  type        = string

  validation {
    condition     = length(trimspace(var.github_repository)) > 0
    error_message = "github_repository must not be empty."
  }
}

variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must be supplied as a numeric GitHub repository ID."
  }
}

variable "github_branch" {
  description = "Only this GitHub branch may assume the publishing role."
  type        = string

  validation {
    condition     = length(trimspace(var.github_branch)) > 0 && !can(regex("[?*]", var.github_branch))
    error_message = "github_branch must be an exact non-empty branch name without wildcards."
  }
}

variable "tags" {
  description = "Tags applied to supported IAM resources."
  type        = map(string)
  default     = {}
}
