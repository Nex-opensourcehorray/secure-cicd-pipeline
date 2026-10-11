output "task_definition_arn" {
  description = "Full ARN of the registered task-definition revision."
  value       = aws_ecs_task_definition.this.arn
}

output "task_definition_family" {
  description = "Family of the digest-pinned task definition."
  value       = aws_ecs_task_definition.this.family
}

output "service_name" {
  description = "Name of the Fargate ECS service."
  value       = aws_ecs_service.this.name
}

output "service_id" {
  description = "Terraform provider ID of the Fargate ECS service."
  value       = aws_ecs_service.this.id
}
