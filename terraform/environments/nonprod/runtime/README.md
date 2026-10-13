# NonProd ECS runtime

## Purpose

This Terraform root composes the Stage 8 private ECS runtime: network, ALB, ECS
foundation, digest-pinned task/service, and runtime observability. It manages
the NonProd runtime only; it does not manage the Stage 7 ECR repository,
organization-owned security services, GitHub OIDC, or future Stage 9 deployment
automation.

## Architecture

- VPC `10.42.0.0/16` across two Availability Zones
- two public subnets for an internet-facing but fail-closed ALB
- two private subnets for one Fargate task and interface endpoints
- no NAT gateway and no private default route
- private ECR API, ECR DKR, CloudWatch Logs, and S3 connectivity
- digest-pinned Linux/X86_64 task with 0.25 vCPU and 0.5 GiB memory
- application logs, VPC Flow Logs, four alarms, two EventBridge rules, and one
  SNS integration topic

See the repository [architecture](../../../../docs/architecture.md),
[security-control register](../../../../docs/runtime-security-controls.md), and
[Stage 8 evidence](../../../../docs/stage-8-runtime-evidence.md).

## Prerequisites

- Terraform and AWS CLI are installed.
- The operator has an authenticated NonProd AWS profile.
- The configured account and Region match the reviewed NonProd target.
- The Stage 7 ECR repository and approved digest already exist.
- Account-scoped ECS and Elastic Load Balancing service-linked roles exist.
- Backend access is available for the runtime state.
- Any plan or apply uses a sanitized, uncommitted variable file.

Creation of service-linked roles, Terraform apply, state mutation, and resource
destruction each require separate owner approval under `AGENTS.md`.

## Current validated state

At Stage 8 closure, the service was active with 1 desired, 1 running, and 0
pending tasks; the deployment and target were healthy. The task had no public
IP, all four endpoints were available, ALB ingress was zero, and the final
Terraform plan was drift-free. This is a validated NonProd architecture, not a
public or production-ready service.

## Expected state inventory

The current state contains 53 managed resources and 10 data sources:

| Area | Managed | Data |
| --- | ---: | ---: |
| Network | 29 | 5 |
| ALB | 3 | 0 |
| ECS foundation | 5 | 2 |
| ECS runtime | 2 | 0 |
| Observability | 14 | 3 |

If these counts change, inspect and document the actual plan rather than
assuming this inventory remains authoritative.

## Security invariants

- `container_image_uri` uses an ECR digest, never `latest` or another mutable
  deployment identity.
- The task remains in private subnets with `assign_public_ip = false`.
- Private route tables have no default internet route and the VPC has no NAT.
- The ALB security group has no ingress until a separate public-exposure gate.
- ALB-to-task traffic is TCP/8000 by security-group reference.
- Task egress is limited to private endpoints, the regional S3 prefix list, and
  the VPC DNS resolver.
- The container runs as `10001:10001`, read-only, non-privileged, with all
  Linux capabilities dropped.
- The task has no application task role.
- The execution role remains limited to ECR pull and CloudWatch Logs delivery.
- The service keeps its deployment circuit breaker and rollback enabled.

## Observability

Application logs and ALL-traffic VPC Flow Logs use dedicated CloudWatch log
groups with 14-day retention. Four alarms cover unhealthy targets, target 5XX,
CPU, and memory. Two EventBridge rules route failure-oriented ECS stops and
active HIGH/CRITICAL project ECR findings to the source-restricted SNS topic.

This Terraform root intentionally owns no human subscription. A private human
endpoint is a manually governed operational integration so it does not enter
Terraform state. Stage 10.5 completed one approved subscription, AWS reports it
confirmed, and the owner confirmed receipt of one controlled test message. The
endpoint remains redacted and future subscription changes or test messages
remain separately gated.
CloudTrail, GuardDuty, Security Hub, and Inspector are organization-owned and
are not configured by this root.

## Plan and apply workflow

From this directory, initialize and validate source before requesting any
mutation approval:

```powershell
terraform init -reconfigure
terraform fmt -check -recursive ..\..\..
terraform validate
terraform plan -var-file=<SANITIZED_UNCOMMITTED_TFVARS>
```

Review the complete plan and separately report creates, updates, destroys,
replacements, IAM, networking, ECS, logging, and security-control changes. An
apply is permitted only after an explicit action gate and must use the exact
reviewed plan. A successful apply must be followed by a fresh refresh-enabled
plan.

## Validation commands

The following read-only checks are representative; replace placeholders with
reviewed names or Terraform outputs and use the intended AWS profile:

```powershell
terraform state list
terraform plan -var-file=<SANITIZED_UNCOMMITTED_TFVARS>

aws ecs describe-services --cluster <CLUSTER> --services <SERVICE> --profile <NONPROD_PROFILE> --region <REGION>
aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN> --profile <NONPROD_PROFILE> --region <REGION>
aws elbv2 describe-target-health --target-group-arn <TARGET_GROUP_ARN> --profile <NONPROD_PROFILE> --region <REGION>
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<VPC_ID> --profile <NONPROD_PROFILE> --region <REGION>
aws ec2 describe-flow-logs --filter Name=resource-id,Values=<VPC_ID> --profile <NONPROD_PROFILE> --region <REGION>
aws cloudwatch describe-alarms --alarm-name-prefix <PROJECT_PREFIX> --profile <NONPROD_PROFILE> --region <REGION>
```

Do not place state, saved plans, real variable files, AWS identifiers, or local
machine paths in documentation or commits.

## Destruction caution

This root owns running ECS, ALB, endpoint, network, IAM, logging, and alerting
resources. Destruction can interrupt the service and remove operational
evidence. Do not run `terraform destroy`, remove state, or weaken lifecycle
controls without a separately reviewed destruction plan and explicit owner
approval. No automatic destruction procedure is provided here.

## Deferred exposure controls

HTTPS/ACM, public ALB ingress, HTTP-to-HTTPS redirect, WAF/rate limiting, ALB
access logs, Terraform-managed human SNS subscriptions, Container Insights,
autoscaling, and
multi-task high availability are not implemented. They remain separate design
and approval gates; Stage 8 closure does not authorize them.
