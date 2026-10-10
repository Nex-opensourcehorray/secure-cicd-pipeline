output "load_balancer_arn" {
  description = "ARN of the internet-facing application load balancer."
  value       = aws_lb.this.arn
}

output "load_balancer_dns_name" {
  description = "AWS-assigned DNS name of the application load balancer."
  value       = aws_lb.this.dns_name
}

output "load_balancer_zone_id" {
  description = "Route 53 hosted zone ID of the application load balancer."
  value       = aws_lb.this.zone_id
}

output "target_group_arn" {
  description = "ARN of the future ECS service target group."
  value       = aws_lb_target_group.this.arn
}

output "listener_status" {
  description = "Stage 8.1 listener posture."
  value       = "DEFERRED"
}
