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

variable "ecs_deployer_role_name" {
  description = "Name of the dedicated NonProd ECS deployment role."
  type        = string
  default     = "secure-cicd-pipeline-nonprod-ecs-deployer"

  validation {
    condition     = var.ecs_deployer_role_name == "secure-cicd-pipeline-nonprod-ecs-deployer"
    error_message = "ecs_deployer_role_name must match the reviewed NonProd deployer role name."
  }
}

variable "management_deployment_broker_role_arn" {
  description = "Exact Management deployment broker trusted by the NonProd ECS deployer."
  type        = string

  validation {
    condition     = var.management_deployment_broker_role_arn == "arn:aws:iam::191125774822:role/secure-cicd-pipeline-nonprod-github-ecs-deployer"
    error_message = "management_deployment_broker_role_arn must match the reviewed Management deployment broker."
  }
}

variable "ecs_cluster_arn" {
  description = "Exact NonProd ECS cluster containing the deployment target."
  type        = string
  default     = "arn:aws:ecs:ap-southeast-1:119033255630:cluster/secure-cicd-pipeline-nonprod"

  validation {
    condition     = var.ecs_cluster_arn == "arn:aws:ecs:ap-southeast-1:119033255630:cluster/secure-cicd-pipeline-nonprod"
    error_message = "ecs_cluster_arn must match the reviewed Stage 8 NonProd cluster."
  }
}

variable "ecs_service_arn" {
  description = "Exact NonProd ECS service that may be described and updated."
  type        = string
  default     = "arn:aws:ecs:ap-southeast-1:119033255630:service/secure-cicd-pipeline-nonprod/secure-cicd-pipeline-nonprod"

  validation {
    condition     = var.ecs_service_arn == "arn:aws:ecs:ap-southeast-1:119033255630:service/secure-cicd-pipeline-nonprod/secure-cicd-pipeline-nonprod"
    error_message = "ecs_service_arn must match the reviewed Stage 8 NonProd service."
  }
}

variable "ecs_task_definition_arn_pattern" {
  description = "Exact task-definition family ARN with only its revision wildcarded."
  type        = string
  default     = "arn:aws:ecs:ap-southeast-1:119033255630:task-definition/secure-cicd-pipeline-nonprod:*"

  validation {
    condition     = var.ecs_task_definition_arn_pattern == "arn:aws:ecs:ap-southeast-1:119033255630:task-definition/secure-cicd-pipeline-nonprod:*"
    error_message = "ecs_task_definition_arn_pattern must match the reviewed Stage 8 task-definition family."
  }
}

variable "ecs_task_arn_pattern" {
  description = "Task ARN pattern restricted to the exact NonProd ECS cluster."
  type        = string
  default     = "arn:aws:ecs:ap-southeast-1:119033255630:task/secure-cicd-pipeline-nonprod/*"

  validation {
    condition     = var.ecs_task_arn_pattern == "arn:aws:ecs:ap-southeast-1:119033255630:task/secure-cicd-pipeline-nonprod/*"
    error_message = "ecs_task_arn_pattern must match the reviewed Stage 8 cluster task pattern."
  }
}

variable "ecs_execution_role_arn" {
  description = "Exact existing ECS execution role that the deployer may pass to ECS tasks."
  type        = string
  default     = "arn:aws:iam::119033255630:role/secure-cicd-pipeline-nonprod-ecs-execution"

  validation {
    condition     = var.ecs_execution_role_arn == "arn:aws:iam::119033255630:role/secure-cicd-pipeline-nonprod-ecs-execution"
    error_message = "ecs_execution_role_arn must match the reviewed Stage 8 execution role."
  }
}
