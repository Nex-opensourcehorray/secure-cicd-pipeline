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

variable "vpc_id" {
  description = "ID of the VPC containing the ALB and target group."
  type        = string

  validation {
    condition     = startswith(var.vpc_id, "vpc-")
    error_message = "vpc_id must begin with vpc-."
  }
}

variable "public_subnet_ids" {
  description = "Exactly two public subnet IDs for the internet-facing ALB."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_ids) == 2 && alltrue([for id in var.public_subnet_ids : startswith(id, "subnet-")])
    error_message = "public_subnet_ids must contain exactly two subnet IDs."
  }
}

variable "alb_security_group_id" {
  description = "ID of the fail-closed ALB security group."
  type        = string

  validation {
    condition     = startswith(var.alb_security_group_id, "sg-")
    error_message = "alb_security_group_id must begin with sg-."
  }
}

variable "tags" {
  description = "Additional tags applied to ALB resources."
  type        = map(string)
  default     = {}
}
