output "vpc_id" {
  description = "ID of the runtime VPC."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "IPv4 CIDR block of the runtime VPC."
  value       = aws_vpc.this.cidr_block
}

output "availability_zones" {
  description = "Reviewed Availability Zones used by the runtime network."
  value       = var.availability_zones
}

output "public_subnet_ids" {
  description = "Public ALB subnet IDs in availability_zones order."
  value       = [for az in var.availability_zones : aws_subnet.public[az].id]
}

output "private_subnet_ids" {
  description = "Private task and endpoint subnet IDs in availability_zones order."
  value       = [for az in var.availability_zones : aws_subnet.private[az].id]
}

output "private_route_table_ids" {
  description = "Private route table IDs in availability_zones order."
  value       = [for az in var.availability_zones : aws_route_table.private[az].id]
}

output "alb_security_group_id" {
  description = "ID of the fail-closed ALB security group."
  value       = aws_security_group.alb.id
}

output "task_security_group_id" {
  description = "ID of the future ECS task security group."
  value       = aws_security_group.task.id
}

output "endpoint_security_group_id" {
  description = "ID of the private interface endpoint security group."
  value       = aws_security_group.endpoint.id
}

output "ecr_api_endpoint_id" {
  description = "ID of the ECR API interface endpoint."
  value       = aws_vpc_endpoint.ecr_api.id
}

output "ecr_dkr_endpoint_id" {
  description = "ID of the ECR DKR interface endpoint."
  value       = aws_vpc_endpoint.ecr_dkr.id
}

output "logs_endpoint_id" {
  description = "ID of the CloudWatch Logs interface endpoint."
  value       = aws_vpc_endpoint.logs.id
}

output "s3_endpoint_id" {
  description = "ID of the S3 gateway endpoint."
  value       = aws_vpc_endpoint.s3.id
}
