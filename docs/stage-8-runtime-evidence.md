# Stage 8 Runtime Evidence

## Deployment baseline

- Source commit: `362c89cd65444eb9ccbbfb8903b3094ec88109fe`
- Branch baseline: local `main`, `origin/main`, and `HEAD` matched that commit
  before the documentation branch was created.
- [CI run 35](https://github.com/Nex-opensourcehorray/secure-cicd-pipeline/actions/runs/38154330026): PASS
- [Security run 35](https://github.com/Nex-opensourcehorray/secure-cicd-pipeline/actions/runs/38154330051): PASS

This evidence describes a validated NonProd runtime. It does not claim
production readiness.

## Terraform state and drift

The authenticated runtime state contained 53 managed resources and 10 data
sources (63 addresses total):

| Area | Managed resources | Data sources | Scope |
| --- | ---: | ---: | --- |
| Network | 29 | 5 | VPC, subnets, routes, security groups/rules, and endpoints |
| ALB | 3 | 0 | Load balancer, target group, and association listener |
| ECS foundation | 5 | 2 | Cluster, execution IAM, and application log group |
| ECS runtime | 2 | 0 | Task definition and service |
| Observability | 14 | 3 | Flow Logs, delivery IAM, alarms, rules/targets, and SNS |
| **Total** | **53** | **10** | |

The final authenticated, refresh-enabled Terraform plan reported:

```text
0 add, 0 change, 0 destroy, 0 replace
```

## ECS runtime

- ECS cluster and service: `ACTIVE`
- Service counts: 1 desired, 1 running, 0 pending
- Launch type: Fargate
- Deployment rollout: `COMPLETED`
- Running-task health: `HEALTHY`
- Registered target: healthy on TCP/8000
- Runtime platform: Linux/X86_64
- Capacity: 0.25 vCPU and 0.5 GiB memory

## Workload security

- Approved image digest:
  `sha256:818e3e445df25cb676535c975fc764af96918507d75b710523c8117706a3e3c3`
- Inspector status for ECR: enabled
- Active findings for the approved digest: 0 HIGH, 0 CRITICAL
- Task ENI: private only; no public IP
- NAT gateways: 0
- Private default routes: 0
- Container user: `10001:10001`
- Read-only root filesystem: enabled
- Privileged mode: disabled
- Linux capabilities: all dropped, none added
- Application task role: none
- Dedicated execution role: present and limited to image pull and log delivery

## Private service connectivity

All four required VPC endpoints were `available`:

- ECR API interface endpoint;
- ECR DKR interface endpoint;
- CloudWatch Logs interface endpoint; and
- S3 gateway endpoint.

The running task and existing application log stream demonstrate successful
private image pull and log delivery without NAT or a private default route.

## Observability

- VPC Flow Log: `ACTIVE`
- CloudWatch Logs delivery: `SUCCESS`
- Flow-log traffic type: `ALL`
- Flow-log streams: 9 at validation time
- Runtime alarms: 4 of 4 in `OK`
- Runtime EventBridge rules: 2 of 2 `ENABLED`, each with its SNS target
- Alert topic: source-restricted policy, zero human subscriptions
- Application log stream: present

Stage 8.7 validation sampled flow records containing both accepted and rejected
traffic and no skipped-log status. Counts from a sample are intentionally not
treated as durable inventory because they change over time.

## Public exposure

- ALB security-group inbound rules: 0
- Public `/health`: blocked/unreachable during validation
- ECS target health behind the ALB: healthy
- Listener posture: `FAIL_CLOSED_HTTP_ASSOCIATION`

This combination proves target association and runtime health without opening
the application to public traffic.

## Engineering Corrections and Lessons

### A. Endpoint readiness ordering

ECS service creation could begin before the private endpoints were usable.
Module output references expressed graph relationships, but they did not prove
that all endpoint resources had reached service readiness. The runtime root now
gives the service explicit dependencies on `module.ecs`, `module.network`, and
`module.alb`.

Lesson: a module-level data dependency is not always a resource-readiness
barrier. Model the operational prerequisite explicitly when a managed service
must consume freshly created endpoints.

### B. Endpoint policy compatibility

Exact-resource ECR and Logs endpoint policies failed endpoint creation with
`InvalidPolicyDocument`. The corrected interface endpoint policies use the
exact ECS execution-role principal, the minimum service actions, and
`Resource = "*"`; the execution-role identity policy independently restricts
ECR pull to the exact repository and log writes to the exact log group.

Lesson: endpoint-policy resource semantics differ by service. Least privilege
can require complementary endpoint and identity-policy layers rather than the
same resource constraint in both places.

### C. Task-definition normalization

The ECS API/provider normalized omitted collections into empty collections,
which produced a perpetual `ForceNew` task-definition difference. The source
now explicitly normalizes `environment`, `mountPoints`, `systemControls`,
`volumesFrom`, and `linuxParameters.capabilities.add` to empty collections and
sets `enable_fault_injection = false`.

Lesson: post-apply drift checks are essential for API-normalized resources;
successful creation does not prove declarative convergence.

### D. Observability hardening

The initial runtime had application logs but lacked alerting and network-flow
evidence. Stage 8.7 added VPC Flow Logs, four runtime alarms, two focused
EventBridge detections, and a source-restricted SNS integration topic.

Lesson: a healthy task is not by itself an operationally defensible runtime.
Availability, security signals, and forensic telemetry need explicit controls.

## Deferred controls

The following controls are **NOT IMPLEMENTED YET** and require separate design,
cost, security, and mutation approval:

| Deferred control | Classification | Reason for deferral |
| --- | --- | --- |
| HTTPS listener and ACM certificate | Public exposure and cryptographic boundary | Requires domain/certificate ownership and a reviewed TLS policy. |
| Public ALB security-group ingress | Exposure boundary | Stage 8 intentionally remains fail-closed. |
| HTTP-to-HTTPS redirect | Public listener behavior | Depends on approved HTTPS listener. |
| WAF and rate limiting | Edge protection | Should be designed against the eventual public traffic and threat model. |
| ALB access logs | Request observability | Storage, access policy, retention, and public-exposure design remain unapproved. |
| Human SNS subscription | Notification integration | Requires an approved destination and ownership/escalation process. |
| Container Insights | Enhanced telemetry and cost | Standard metrics are sufficient for initial NonProd validation; added recurring cost is not yet justified. |
| Autoscaling | Capacity management | No load objective or scaling policy has been approved. |
| Multi-task high availability | Resilience and cost | Desired count remains one for cost-conscious NonProd validation. |

## Cost posture

The deployed NonProd shape contains one ALB, three interface endpoint services
across two Availability Zones (six endpoint ENIs), one 0.25-vCPU/0.5-GiB
Fargate task, application logs, VPC Flow Logs, four CloudWatch alarms, an SNS
topic, two EventBridge rules, and private ECR storage/scanning. It intentionally
avoids NAT gateways, Container Insights, and extra task replicas. This is a
cost-conscious NonProd posture, not a production capacity recommendation.

## Stage 9 handoff

Stage 9 may begin only from this stable boundary: drift-free Terraform, a clean
immutable image, healthy private runtime, operational baseline observability,
an available alert integration point, and a closed public boundary.

Stage 9 owns continuous deployment, including:

- a dedicated deployment IAM role and narrowly scoped GitHub OIDC role chain;
- digest-to-task-definition promotion;
- explicit deployment approval and rollback behavior; and
- deployment-specific threat-model and evidence updates.

Stage 9 must not reuse the ECR publisher role, grant broad `ecs:*`, grant broad
`iam:PassRole`, introduce static AWS credentials, deploy mutable tags, open
public ingress, or bypass CI/security checks. Any `iam:PassRole` permission must
name the exact ECS execution role and, only if one is later introduced, the
exact application task role.
