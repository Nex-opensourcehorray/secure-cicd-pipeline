variable "project_name" {
  description = "Project identifier used in ECS task and service names."
  type        = string

  validation {
    condition     = length(trimspace(var.project_name)) > 0 && length(var.project_name) <= 24
    error_message = "project_name must contain between 1 and 24 characters."
  }
}

variable "environment" {
  description = "Deployment environment identifier used in ECS task and service names."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.environment))
    error_message = "environment must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "aws_region" {
  description = "AWS Region used by the awslogs driver."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS Region name."
  }
}

variable "cluster_arn" {
  description = "ARN of the existing ECS cluster that owns the service."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:ecs:[a-z0-9-]+:[0-9]{12}:cluster/[A-Za-z0-9_-]+$", var.cluster_arn))
    error_message = "cluster_arn must be a valid ECS cluster ARN."
  }
}

variable "execution_role_arn" {
  description = "ARN of the existing pull-and-log-only ECS task execution role."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$", var.execution_role_arn))
    error_message = "execution_role_arn must be a valid IAM role ARN."
  }
}

variable "container_image_uri" {
  description = "Immutable ECR image URI pinned by sha256 digest."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$", var.container_image_uri))
    error_message = "container_image_uri must be an ECR URI pinned by a sha256 digest."
  }
}

variable "log_group_name" {
  description = "Existing CloudWatch Logs log group used by the awslogs driver."
  type        = string

  validation {
    condition     = startswith(var.log_group_name, "/") && length(var.log_group_name) <= 512
    error_message = "log_group_name must begin with / and contain no more than 512 characters."
  }
}

variable "private_subnet_ids" {
  description = "Exactly two private subnet IDs used by Fargate task ENIs."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) == 2 && alltrue([for id in var.private_subnet_ids : startswith(id, "subnet-")])
    error_message = "private_subnet_ids must contain exactly two subnet IDs."
  }
}

variable "task_security_group_id" {
  description = "Existing task security group restricted to ALB ingress and private endpoint egress."
  type        = string

  validation {
    condition     = startswith(var.task_security_group_id, "sg-")
    error_message = "task_security_group_id must begin with sg-."
  }
}

variable "target_group_arn" {
  description = "ARN of the existing IP target group used by the ECS service."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:elasticloadbalancing:[a-z0-9-]+:[0-9]{12}:targetgroup/[A-Za-z0-9-]+/[0-9a-f]+$", var.target_group_arn))
    error_message = "target_group_arn must be a valid ALB target group ARN."
  }
}

variable "tags" {
  description = "Additional tags applied to ECS task definition and service resources."
  type        = map(string)
  default     = {}
}
