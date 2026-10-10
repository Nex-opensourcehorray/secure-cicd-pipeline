variable "project_name" {
  description = "Project identifier used in resource names and tags."
  type        = string

  validation {
    condition     = length(trimspace(var.project_name)) > 0 && length(var.project_name) <= 24
    error_message = "project_name must contain between 1 and 24 characters."
  }
}

variable "environment" {
  description = "Deployment environment identifier used in resource names and tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.environment))
    error_message = "environment must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "aws_region" {
  description = "AWS Region used by the ECS trust policy and resource ARNs."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS Region name."
  }
}

variable "aws_account_id" {
  description = "AWS account ID used by the execution-role trust and resource policies."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "ecr_repository_arn" {
  description = "Exact ECR repository ARN from which the execution role may pull images."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:ecr:[a-z0-9-]+:[0-9]{12}:repository/[A-Za-z0-9._/-]+$", var.ecr_repository_arn))
    error_message = "ecr_repository_arn must be a valid ECR repository ARN."
  }
}

variable "log_group_name" {
  description = "Exact CloudWatch Logs log group name owned by this module."
  type        = string

  validation {
    condition     = startswith(var.log_group_name, "/") && length(var.log_group_name) <= 512
    error_message = "log_group_name must begin with / and contain no more than 512 characters."
  }
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days."
  type        = number
  default     = 14

  validation {
    condition     = var.log_retention_days == 14
    error_message = "Stage 8.2 log retention must remain at the approved 14 days."
  }
}

variable "tags" {
  description = "Additional tags applied to ECS foundation resources."
  type        = map(string)
  default     = {}
}
