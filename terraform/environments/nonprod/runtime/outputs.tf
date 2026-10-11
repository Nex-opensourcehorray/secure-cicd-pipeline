output "vpc_id" {
  description = "ID of the Stage 8 runtime VPC."
  value       = module.network.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the Stage 8 runtime VPC."
  value       = module.network.vpc_cidr
}

output "availability_zones" {
  description = "Availability Zones used by the runtime network."
  value       = module.network.availability_zones
}

output "public_subnet_ids" {
  description = "IDs of the public ALB subnets."
  value       = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private task and endpoint subnets."
  value       = module.network.private_subnet_ids
}

output "alb_security_group_id" {
  description = "ID of the fail-closed ALB security group."
  value       = module.network.alb_security_group_id
}

output "task_security_group_id" {
  description = "ID of the future ECS task security group."
  value       = module.network.task_security_group_id
}

output "endpoint_security_group_id" {
  description = "ID of the interface endpoint security group."
  value       = module.network.endpoint_security_group_id
}

output "ecr_api_endpoint_id" {
  description = "ID of the ECR API interface endpoint."
  value       = module.network.ecr_api_endpoint_id
}

output "ecr_dkr_endpoint_id" {
  description = "ID of the ECR DKR interface endpoint."
  value       = module.network.ecr_dkr_endpoint_id
}

output "logs_endpoint_id" {
  description = "ID of the CloudWatch Logs interface endpoint."
  value       = module.network.logs_endpoint_id
}

output "s3_endpoint_id" {
  description = "ID of the S3 gateway endpoint."
  value       = module.network.s3_endpoint_id
}

output "load_balancer_arn" {
  description = "ARN of the internet-facing application load balancer."
  value       = module.alb.load_balancer_arn
}

output "load_balancer_dns_name" {
  description = "AWS-assigned DNS name of the application load balancer."
  value       = module.alb.load_balancer_dns_name
}

output "load_balancer_zone_id" {
  description = "Route 53 hosted zone ID of the application load balancer."
  value       = module.alb.load_balancer_zone_id
}

output "target_group_arn" {
  description = "ARN of the future ECS service target group."
  value       = module.alb.target_group_arn
}

output "listener_arn" {
  description = "ARN of the fail-closed HTTP target-group association listener."
  value       = module.alb.listener_arn
}

output "listener_port" {
  description = "Port of the fail-closed target-group association listener."
  value       = module.alb.listener_port
}

output "listener_status" {
  description = "Current listener posture; public ALB security-group ingress remains disabled."
  value       = module.alb.listener_status
}

output "ecs_cluster_name" {
  description = "Name of the dedicated Stage 8 ECS cluster."
  value       = module.ecs.cluster_name
}

output "ecs_cluster_arn" {
  description = "ARN of the dedicated Stage 8 ECS cluster."
  value       = module.ecs.cluster_arn
}

output "ecs_execution_role_arn" {
  description = "ARN of the dedicated ECS task execution role."
  value       = module.ecs.execution_role_arn
}

output "ecs_execution_policy_arn" {
  description = "ARN of the custom ECS task execution policy."
  value       = module.ecs.execution_policy_arn
}

output "ecs_log_group_name" {
  description = "Name of the ECS application log group."
  value       = module.ecs.log_group_name
}

output "task_definition_arn" {
  description = "Full ARN of the digest-pinned ECS task-definition revision."
  value       = module.ecs_service.task_definition_arn
}

output "task_definition_family" {
  description = "Family of the digest-pinned ECS task definition."
  value       = module.ecs_service.task_definition_family
}

output "ecs_service_name" {
  description = "Name of the private Fargate ECS service."
  value       = module.ecs_service.service_name
}

output "ecs_service_id" {
  description = "Terraform provider ID of the private Fargate ECS service."
  value       = module.ecs_service.service_id
}
