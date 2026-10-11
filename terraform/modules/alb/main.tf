locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

resource "aws_lb" "this" {
  #checkov:skip=CKV_AWS_91:Access-log bucket and delivery policy are deferred to Stage 8.7 observability hardening.
  #checkov:skip=CKV_AWS_150:Deletion protection is disabled for approved NonProd cleanup and fixed-cost control.
  #checkov:skip=CKV2_AWS_28:WAF is deferred until the public TLS listener and ingress strategy are approved.
  #checkov:skip=CKV2_AWS_20:Accepted temporary fail-closed control; the association-only HTTP listener has no ALB SG ingress, and HTTPS/domain work is explicitly deferred.
  name                       = "${local.name_prefix}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [var.alb_security_group_id]
  subnets                    = var.public_subnet_ids
  ip_address_type            = "ipv4"
  drop_invalid_header_fields = true
  enable_http2               = true
  enable_deletion_protection = false

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-alb"
  })
}

resource "aws_lb_target_group" "this" {
  #checkov:skip=CKV_AWS_378:HTTP is the approved private ALB-to-task hop, restricted SG-to-SG on TCP 8000; public TLS is deferred.
  name        = "${local.name_prefix}-tg"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    protocol            = "HTTP"
    path                = "/health"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-tg"
  })
}

# This HTTP listener exists only to associate the target group with the ALB
# before ECS creates the service. The ALB security group intentionally has no
# ingress rules, so the listener remains unreachable from public networks.
# Public TLS, HTTP-to-HTTPS redirection, and ingress remain separately gated.
resource "aws_lb_listener" "fail_closed_association" {
  #checkov:skip=CKV_AWS_2:Accepted temporary fail-closed control; zero ALB SG ingress makes this association-only HTTP listener unreachable, and HTTPS/domain work is deferred.
  #checkov:skip=CKV_AWS_103:Accepted temporary fail-closed control; this unreachable HTTP association listener has no TLS policy until separately approved HTTPS/domain work.
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}
