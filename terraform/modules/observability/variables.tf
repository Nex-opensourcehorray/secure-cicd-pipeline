variable "project_name" {
  description = "Project identifier used for observability resource names."
  type        = string
}

variable "environment" {
  description = "Environment label used for observability resource names."
  type        = string
}

variable "aws_region" {
  description = "AWS Region containing the runtime resources."
  type        = string
}

variable "aws_account_id" {
  description = "AWS account that owns the runtime and observability resources."
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC whose accepted and rejected flows are logged."
  type        = string
}

variable "alb_arn_suffix" {
  description = "Application Load Balancer ARN suffix used as a CloudWatch metric dimension."
  type        = string
}

variable "target_group_arn_suffix" {
  description = "Target group ARN suffix used as a CloudWatch metric dimension."
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name used for metric and event scoping."
  type        = string
}

variable "ecs_cluster_arn" {
  description = "ECS cluster ARN used to scope task-state events."
  type        = string
}

variable "ecs_service_name" {
  description = "ECS service name used for metric and event scoping."
  type        = string
}

variable "ecr_repository_name" {
  description = "ECR repository whose HIGH and CRITICAL Inspector findings are reported."
  type        = string
}

variable "flow_log_retention_days" {
  description = "Retention period for VPC Flow Logs in CloudWatch Logs."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags applied to observability resources that support tagging."
  type        = map(string)
  default     = {}
}
