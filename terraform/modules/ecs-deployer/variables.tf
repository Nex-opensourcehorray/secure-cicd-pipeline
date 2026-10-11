variable "role_name" {
  description = "Name of the dedicated NonProd ECS deployment role."
  type        = string

  validation {
    condition     = length(trimspace(var.role_name)) > 0 && length(var.role_name) <= 64
    error_message = "role_name must contain between 1 and 64 characters."
  }
}

variable "management_deployment_broker_role_arn" {
  description = "Exact Management deployment broker role trusted to assume this role."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$", var.management_deployment_broker_role_arn))
    error_message = "management_deployment_broker_role_arn must be a valid IAM role ARN."
  }
}

variable "ecr_repository_arn" {
  description = "Exact ECR repository whose image and scan metadata may be read."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:ecr:[^:]+:[0-9]{12}:repository/[A-Za-z0-9._/-]+$", var.ecr_repository_arn))
    error_message = "ecr_repository_arn must be a valid ECR repository ARN."
  }
}

variable "ecs_cluster_arn" {
  description = "Exact ECS cluster containing the deployment target."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:cluster/[A-Za-z0-9_-]+$", var.ecs_cluster_arn))
    error_message = "ecs_cluster_arn must be a valid ECS cluster ARN."
  }
}

variable "ecs_service_arn" {
  description = "Exact ECS service the deployment role may describe and update."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:service/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+$", var.ecs_service_arn))
    error_message = "ecs_service_arn must be a valid long-format ECS service ARN."
  }
}

variable "ecs_task_definition_arn_pattern" {
  description = "Exact ECS task-definition family ARN with only the revision wildcarded."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:task-definition/[A-Za-z0-9_-]+:\\*$", var.ecs_task_definition_arn_pattern))
    error_message = "ecs_task_definition_arn_pattern must wildcard only the task-definition revision."
  }
}

variable "ecs_task_arn_pattern" {
  description = "Task ARN pattern restricted to the exact ECS cluster."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:task/[A-Za-z0-9_-]+/\\*$", var.ecs_task_arn_pattern))
    error_message = "ecs_task_arn_pattern must wildcard only task IDs in one exact cluster."
  }
}

variable "ecs_execution_role_arn" {
  description = "Exact existing ECS execution role that may be passed to ECS tasks."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$", var.ecs_execution_role_arn))
    error_message = "ecs_execution_role_arn must be a valid IAM role ARN."
  }
}

variable "tags" {
  description = "Tags applied to supported IAM resources."
  type        = map(string)
  default     = {}
}
