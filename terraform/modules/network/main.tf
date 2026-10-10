locals {
  name_prefix       = "${var.project_name}-${var.environment}"
  account_principal = "arn:aws:iam::${var.aws_account_id}:root"
  dns_resolver_cidr = "${cidrhost(var.vpc_cidr, 2)}/32"
  future_log_arn    = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:${var.future_log_group_name}:*"
  s3_layer_arn      = "arn:aws:s3:::prod-${var.aws_region}-starport-layer-bucket/*"

  subnet_layout = {
    for index, availability_zone in var.availability_zones : availability_zone => {
      suffix       = substr(availability_zone, length(availability_zone) - 1, 1)
      public_cidr  = var.public_subnet_cidrs[index]
      private_cidr = var.private_subnet_cidrs[index]
    }
  }
}

resource "aws_vpc" "this" {
  #checkov:skip=CKV2_AWS_11:VPC Flow Logs are explicitly deferred to Stage 8.7 observability hardening.
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  instance_tenancy     = "default"

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

# Restrict the implicit default security group so workloads cannot use it.
resource "aws_default_security_group" "this" {
  vpc_id  = aws_vpc.this.id
  ingress = []
  egress  = []

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-default-sg-restricted"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-igw"
  })
}

resource "aws_subnet" "public" {
  for_each = local.subnet_layout

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = each.value.public_cidr
  map_public_ip_on_launch = false

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-public-${each.value.suffix}"
    Tier = "public-alb"
  })
}

resource "aws_subnet" "private" {
  for_each = local.subnet_layout

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = each.value.private_cidr
  map_public_ip_on_launch = false

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-private-${each.value.suffix}"
    Tier = "private-runtime"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-public-rt"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  for_each = local.subnet_layout

  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-private-${each.value.suffix}-rt"
  })
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_security_group" "alb" {
  #checkov:skip=CKV2_AWS_5:Attached to the ALB through the composed runtime root; Checkov cannot resolve the cross-module variable edge.
  name        = "${local.name_prefix}-alb-sg"
  description = "Fail-closed ALB security group; public ingress is deferred"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-alb-sg"
  })
}

resource "aws_security_group" "task" {
  #checkov:skip=CKV2_AWS_5:Attachment is intentionally deferred until the Stage 8.2 ECS task resource exists.
  name        = "${local.name_prefix}-task-sg"
  description = "Future ECS task traffic restricted to ALB and private AWS endpoints"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-task-sg"
  })
}

resource "aws_security_group" "endpoint" {
  name        = "${local.name_prefix}-endpoint-sg"
  description = "Private interface endpoints reachable only from the task security group"
  vpc_id      = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-endpoint-sg"
  })
}

resource "aws_vpc_security_group_ingress_rule" "task_from_alb" {
  security_group_id            = aws_security_group.task.id
  referenced_security_group_id = aws_security_group.alb.id
  description                  = "Application traffic from the ALB only"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_vpc_security_group_egress_rule" "alb_to_task" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.task.id
  description                  = "Application traffic to future tasks only"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

resource "aws_vpc_security_group_egress_rule" "task_to_endpoints" {
  security_group_id            = aws_security_group.task.id
  referenced_security_group_id = aws_security_group.endpoint.id
  description                  = "TLS to private interface endpoints"
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}

data "aws_ec2_managed_prefix_list" "s3" {
  name = "com.amazonaws.${var.aws_region}.s3"
}

resource "aws_vpc_security_group_egress_rule" "task_to_s3" {
  security_group_id = aws_security_group.task.id
  prefix_list_id    = data.aws_ec2_managed_prefix_list.s3.id
  description       = "TLS to the regional S3 service through the gateway endpoint"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "task_dns_udp" {
  security_group_id = aws_security_group.task.id
  cidr_ipv4         = local.dns_resolver_cidr
  description       = "DNS to the VPC resolver over UDP"
  ip_protocol       = "udp"
  from_port         = 53
  to_port           = 53
}

resource "aws_vpc_security_group_egress_rule" "task_dns_tcp" {
  security_group_id = aws_security_group.task.id
  cidr_ipv4         = local.dns_resolver_cidr
  description       = "DNS to the VPC resolver over TCP"
  ip_protocol       = "tcp"
  from_port         = 53
  to_port           = 53
}

resource "aws_vpc_security_group_ingress_rule" "endpoints_from_task" {
  security_group_id            = aws_security_group.endpoint.id
  referenced_security_group_id = aws_security_group.task.id
  description                  = "TLS from future tasks only"
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}

data "aws_iam_policy_document" "ecr_api_endpoint" {
  statement {
    sid       = "AuthorizationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = [local.account_principal]
    }
  }

  statement {
    sid    = "RepositoryPullMetadata"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [var.ecr_repository_arn]

    principals {
      type        = "AWS"
      identifiers = [local.account_principal]
    }
  }
}

data "aws_iam_policy_document" "ecr_dkr_endpoint" {
  statement {
    sid    = "RepositoryImagePull"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [var.ecr_repository_arn]

    principals {
      type        = "AWS"
      identifiers = [local.account_principal]
    }
  }
}

data "aws_iam_policy_document" "logs_endpoint" {
  statement {
    sid    = "FutureRuntimeLogDelivery"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [local.future_log_arn]

    principals {
      type        = "AWS"
      identifiers = [local.account_principal]
    }
  }
}

data "aws_iam_policy_document" "s3_endpoint" {
  statement {
    sid       = "EcrImageLayerRead"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = [local.s3_layer_arn]

    principals {
      type        = "AWS"
      identifiers = [local.account_principal]
    }
  }
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for az in var.availability_zones : aws_subnet.private[az].id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.endpoint.id]
  policy              = data.aws_iam_policy_document.ecr_api_endpoint.json

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-ecr-api-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for az in var.availability_zones : aws_subnet.private[az].id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.endpoint.id]
  policy              = data.aws_iam_policy_document.ecr_dkr_endpoint.json

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-ecr-dkr-endpoint"
  })
}

resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for az in var.availability_zones : aws_subnet.private[az].id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.endpoint.id]
  policy              = data.aws_iam_policy_document.logs_endpoint.json

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-logs-endpoint"
  })
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [for az in var.availability_zones : aws_route_table.private[az].id]
  policy            = data.aws_iam_policy_document.s3_endpoint.json

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-s3-endpoint"
  })
}
