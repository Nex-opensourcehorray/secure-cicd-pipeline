# Runtime security controls

This register describes the implemented Stage 8 NonProd runtime controls and
their validation status. `VALIDATED` means the stated evidence was checked
against the deployed runtime at Stage 8 closure; it does not mean the system is
production-ready or risk-free.

## Preventive and detective controls

| Control | Implementation | Threat/Risk Addressed | Validation Evidence | Status |
| --- | --- | --- | --- | --- |
| Immutable image identity | ECS references the approved ECR `sha256:` digest rather than a mutable tag. | Tag replacement and artifact ambiguity. | Live task definition matched the approved digest. | VALIDATED |
| Image vulnerability scanning | Amazon Inspector enhanced ECR scanning is enabled; GitHub Security blocks HIGH/CRITICAL findings during publication. | Deployment of a known vulnerable image. | Approved digest had zero active HIGH and zero active CRITICAL findings; Security run 35 passed. | VALIDATED |
| Private task placement | Fargate task runs in private subnets with `assign_public_ip = false`. | Direct internet exposure of the workload. | Running task had no public IPv4 address. | VALIDATED |
| No private internet route | No NAT gateway and no default route in either private route table. | Uncontrolled outbound internet connectivity and unnecessary fixed cost. | Live network inspection reported zero NAT gateways and zero private default routes. | VALIDATED |
| Least-privilege execution IAM | Dedicated execution role permits ECR token/pull and application-log delivery only, with repository/log writes resource-scoped where AWS supports it. | Excessive runtime-agent privileges. | Terraform policy review and successful private image pull/log delivery. | VALIDATED |
| No application task role | Task definition omits `taskRoleArn`. | Unnecessary AWS API credentials inside the container. | Live task definition returned no task role. | VALIDATED |
| Private AWS service access | ECR API, ECR DKR, and Logs interface endpoints plus an S3 gateway endpoint serve image pull and logs without NAT. | Dependency on public service paths. | All four endpoints were `available`; the task was running and application logs existed. | VALIDATED |
| Endpoint policy boundary | Interface endpoint policies name the exact execution-role principal and minimal actions; identity policies constrain ECR/log resources. | Other VPC principals using endpoints for unintended operations. | Terraform policy review and endpoint availability checks. | VALIDATED |
| Hardened container | UID/GID `10001:10001`, read-only root filesystem, `privileged = false`, and all Linux capabilities dropped. | Container privilege escalation and filesystem persistence. | Live task-definition inspection matched every setting. | VALIDATED |
| Security-group segmentation | ALB-to-task TCP/8000 only; task-to-endpoints/S3/DNS only; endpoint ingress from the task SG only; default SG restricted. | Lateral movement and unintended ingress/egress. | Terraform rule review and live zero-ingress ALB check. | VALIDATED |
| Fail-closed ALB | Internet-facing ALB has zero inbound SG rules; HTTP/80 exists only for target association. | Premature public application exposure. | Public `/health` was unreachable while the registered target remained healthy. | VALIDATED |
| Deployment circuit breaker | ECS service enables circuit-breaker rollback. | Failed deployment remaining active. | Live service rollout was `COMPLETED`; Terraform enables rollback. | VALIDATED |
| Application logging | `awslogs` sends container output to a dedicated 14-day CloudWatch Logs group. | Loss of application diagnostics. | Application log stream present. | VALIDATED |
| Network flow logging | ALL VPC flows use a dedicated 14-day log group and narrowly scoped delivery role. | Lack of network-forensics evidence. | Flow Log status `ACTIVE`, delivery `SUCCESS`, with log streams present. | VALIDATED |
| Runtime metric alarms | Four alarms cover unhealthy targets, target 5XX, ECS CPU, and ECS memory. | Silent availability or saturation degradation. | All four alarms existed with SNS actions and state `OK`. | VALIDATED |
| Security event routing | EventBridge selects failure-oriented ECS stops and active HIGH/CRITICAL ECR Inspector findings. | Missed task failures and serious image findings. | Both rules were `ENABLED` with one SNS target each. | VALIDATED |
| Source-restricted alert topic | SNS policy permits publish only from the exact alarms and EventBridge rules in the NonProd account. Terraform owns no human endpoint. | Arbitrary alert injection and private endpoint retention in state. | Stage 10.6 revalidated the policy, one confirmed email subscription with its endpoint redacted, and owner-confirmed receipt of one controlled test message. | VALIDATED |
| Terraform drift check | Runtime source and live state are compared with a refresh-enabled plan. | Undetected manual or provider drift. | The Stage 10.6 runtime plan returned detailed exit code 0 with no changes. | VALIDATED |
| GitHub CI and Security | Tests and security checks run on the immutable source commit. | Regressions or unsafe source entering the baseline. | Stage 10.6 CI run `38387312620` and Security run `38387318507` passed all seven governed jobs for source `73a6862dd5c442bc844bfb35442ca228f78cc17c`. | VALIDATED |

## Detection coverage

| Condition | Telemetry | Detection/alarm | Owner | Current status |
| --- | --- | --- | --- | --- |
| Task start or essential-container failure | ECS task state-change events | Failure-oriented EventBridge rule to SNS | Project | ENABLED |
| Unhealthy target | ApplicationELB `UnHealthyHostCount` | CloudWatch alarm to SNS | Project | OK |
| Target HTTP 5XX | ApplicationELB `HTTPCode_Target_5XX_Count` | CloudWatch alarm to SNS | Project | OK |
| Sustained high CPU | ECS `CPUUtilization` | CloudWatch alarm to SNS | Project | OK |
| Sustained high memory | ECS `MemoryUtilization` | CloudWatch alarm to SNS | Project | OK |
| HIGH/CRITICAL image finding | Inspector2 finding events | Repository-scoped EventBridge rule to SNS | Project rule; organization scanner | ENABLED; zero active HIGH/CRITICAL on approved digest |
| Unexpected network flow | VPC Flow Logs (accepted and rejected traffic) | Log investigation; no metric filter in Stage 8 | Project | TELEMETRY AVAILABLE |
| Unauthorized cloud activity | CloudTrail, GuardDuty, and Security Hub | Organization-managed detections | Organization | EXTERNAL CONTROL; not managed by this state |
| Public request visibility | ALB access logs | No Stage 8 detection | Project | NOT AVAILABLE; deferred with public exposure controls |

At Stage 8 closure the topic was an integration point with no human
subscription. Stage 10.5 retained Terraform ownership of routing and added one
manual email subscription outside state. Stage 10.6 re-read one confirmed
subscription, and the owner confirmed receipt of the one controlled test sent
under the earlier approval gate. Alarm state `OK` still demonstrates metric
state at the time of observation rather than independently testing each signal.

The current [threat model](threat-model.md) now covers deployment identity,
authorization, artifact selection, approval, rollback, workflow compromise,
and the residual risks retained at Stage 9 closure.
