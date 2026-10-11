# NonProd runtime apply sequence

This root defines the Stage 8 Option C runtime. Its port 80 ALB listener is a
fail-closed target-group association mechanism, not public application ingress.
The ALB security group has no inbound rules. Public TLS, HTTP-to-HTTPS
redirection, ACM, DNS, and public ingress require a separate reviewed change.

Do not apply this root until the following independently approved gates have
completed.

## Stage 8.5A — service-linked IAM prerequisites

Read-only check for both account-scoped roles:

- `AWSServiceRoleForECS`
- `AWSServiceRoleForElasticLoadBalancing`

If either role is absent, create it only under an explicit IAM mutation gate,
then verify the resulting role. These shared service-linked roles are not owned
by this Terraform state.

Separately gated command templates:

```powershell
aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com --profile secure-cicd-nonprod
aws iam create-service-linked-role --aws-service-name elasticloadbalancing.amazonaws.com --profile secure-cicd-nonprod
```

Do not run either command without explicit owner approval for Stage 8.5A.

Stop after verification.

## Stage 8.5B — final runtime plan

Run a new authenticated, refresh-enabled plan against the NonProd account.
Review the complete resource inventory and require zero updates, destroys, and
replacements. Save the reviewed plan only for the subsequent apply gate.

Stop before apply.

## Stage 8.5C — exact-plan apply

Apply only the saved plan approved at Stage 8.5B. Afterwards verify the VPC,
private routes, endpoints, ALB and listener, target-group association, ECS
cluster/task/service, private task ENI, digest-pinned image, logs, and target
health.

Public endpoint reachability must remain absent while the ALB security group
has no ingress rules.

## Stage 8.7-R1 — runtime observability hardening

The runtime root composes a dedicated observability module that adds VPC Flow
Logs to CloudWatch Logs, service and target alarms, and narrowly scoped ECS and
Inspector EventBridge rules. All alarms and rules publish to one project SNS
topic. Terraform intentionally creates no email, SMS, or other human
subscription; notification delivery remains incomplete until a separately
approved subscription is configured.

The observability resources do not change the task definition, ECS service,
ALB listener, security groups, routes, endpoints, task role, or execution-role
permissions. Public ingress, HTTPS, WAF, ALB access logging, and Container
Insights remain outside this change and require separate review.
