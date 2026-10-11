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

output "listener_arn" {
  description = "ARN of the fail-closed HTTP target-group association listener."
  value       = aws_lb_listener.fail_closed_association.arn
}

output "listener_port" {
  description = "Port of the fail-closed target-group association listener."
  value       = aws_lb_listener.fail_closed_association.port
}

output "listener_status" {
  description = "Current listener posture; public ALB security-group ingress remains disabled."
  value       = "FAIL_CLOSED_HTTP_ASSOCIATION"
}
