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
  description = "AWS Region used to construct regional service endpoint and resource ARNs."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS Region name."
  }
}

variable "aws_account_id" {
  description = "AWS account ID allowed by the least-privilege VPC endpoint policies."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block for the runtime VPC."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "Exactly two reviewed Availability Zones for the runtime network."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "availability_zones must contain exactly two distinct values."
  }
}

variable "public_subnet_cidrs" {
  description = "Exactly two public ALB subnet CIDR blocks, ordered to match availability_zones."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) == 2 && alltrue([for cidr in var.public_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "public_subnet_cidrs must contain exactly two valid IPv4 CIDR blocks."
  }
}

variable "private_subnet_cidrs" {
  description = "Exactly two private task and endpoint subnet CIDR blocks, ordered to match availability_zones."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_cidrs) == 2 && alltrue([for cidr in var.private_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "private_subnet_cidrs must contain exactly two valid IPv4 CIDR blocks."
  }
}

variable "ecr_repository_arn" {
  description = "Exact ECR repository ARN allowed by the interface endpoint policies."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:ecr:[a-z0-9-]+:[0-9]{12}:repository/[A-Za-z0-9._/-]+$", var.ecr_repository_arn))
    error_message = "ecr_repository_arn must be a valid ECR repository ARN."
  }
}

variable "future_log_group_name" {
  description = "Exact future CloudWatch log group name allowed by the Logs endpoint policy."
  type        = string

  validation {
    condition     = startswith(var.future_log_group_name, "/") && length(var.future_log_group_name) <= 512
    error_message = "future_log_group_name must begin with / and contain no more than 512 characters."
  }
}

variable "tags" {
  description = "Additional tags applied to network resources."
  type        = map(string)
  default     = {}
}
