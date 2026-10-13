# Stage 9 Continuous Deployment Threat Model

> Status: **IMPLEMENTED; LIVE PROMOTION AND LIVE ROLLBACK EXERCISE DEFERRED**.
> This model covers the NonProd ECS deployment boundary and supplements the
> Stage 7 publication and Stage 8 runtime controls. Residual risks and accepted
> portfolio governance limitations remain explicit below.

## Security objective

An explicitly authorized trusted-main workflow may promote one existing,
approved ECR digest to one existing NonProd ECS service. It must not gain image
publication, broad infrastructure, network mutation, public exposure, IAM
administration, or application task authority.

## Threat register

| ID | Asset / trust boundary | Threat and attack path | Impact | Mitigation and control mapping | Residual risk |
| --- | --- | --- | --- | --- | --- |
| A | Deployment workflow source | An attacker changes workflow validation or deployment commands on `main`. | Privileged workflow deploys an unintended artifact or weakens checks. | Active `main-governance` ruleset requires PR flow, all seven CI/Security checks, current-branch freshness, and resolved review threads; it blocks ordinary direct pushes, force pushes, and deletion. Immutable action SHAs, exact-main provenance checks, Environment approval, and workflow-source evidence remain in place. | **MEDIUM** — the solo owner retains PR-only ruleset bypass and the Environment approval path is not independent; compromise of that trusted identity can still authorize malicious source. |
| B | Repository-to-deployment boundary | A feature branch, pull request, or fork invokes deployment. | Unreviewed code receives AWS deployment credentials. | Manual trusted trigger; exact `main` ref claim; full-SHA main-ancestry check; Environment protection; no `pull_request_target`; no OIDC credentials in untrusted jobs. | **LOW** after controls; GitHub configuration drift must be monitored. |
| C | GitHub OIDC-to-Management boundary | A token from another repository or context assumes the broker. | Unauthorized cross-account deployment path. | Existing singleton provider; exact audience and immutable subject; independent numeric owner/repository claims; exact ref; short-lived credentials; allowed-account IDs. | **LOW** after live claim and role-chain validation. |
| D | GitHub Environment boundary | Environment use changes the subject unexpectedly, or a job bypasses required approval. | OIDC trust accepts an unintended context or approval is ineffective. | Exact immutable `environment:nonprod` subject; required reviewer and exact `main` branch policy; real-token claim validation; administrator bypass disabled; fail closed on mismatch. | **MEDIUM** — this portfolio is single-maintainer and self-review is permitted; this is not four-eyes approval. |
| E | Management-to-NonProd boundary | Workflow assumes a role in the wrong AWS account. | Deployment or disclosure in an unintended account. | Dedicated exact role ARNs; `allowed-account-ids` at both credential steps; `GetCallerIdentity` equality check before reads/writes. | **LOW** after implementation. |
| F | Separation of publication and deployment | Existing ECR publisher or publication broker is reused and expanded. | One compromised identity gains both artifact-write and runtime-deploy authority. | Dedicated Management deployment broker and dedicated NonProd deployer; publication policies remain unchanged; distinct workflow/session names and CloudTrail path. | **LOW** after dedicated roles exist. |
| G | NonProd ECS control plane | Broad `ecs:*` or account-wide writes permit unrelated service/task changes. | General ECS administration and wider workload compromise. | Explicit action allowlist; exact service, cluster, task family, and task patterns where supported; reject service/cluster create/delete, RunTask, StopTask, and deregistration. | **MEDIUM** because some required ECS actions have wildcard request scope; workflow validations compensate. |
| H | IAM PassRole boundary | Deployer passes an arbitrary privileged role into a task definition. | Privilege escalation into AWS through a malicious task role/execution role. | `iam:PassRole` on the exact ECS execution-role ARN only, conditioned on `iam:PassedToService = ecs-tasks.amazonaws.com`; task role must be absent; no role-name wildcard. | **LOW** after exact policy review, live role-chain validation, and invariant testing. |
| I | Task-definition registration boundary | Workflow registers arbitrary containers, commands, roles, or resource settings. | Malicious code or weakened runtime controls enters ECS. | Clone exact service revision; validate every invariant; construct allowlisted RegisterTaskDefinition input; IAM Fargate/CPU/memory/privileged conditions; semantic assertion that only image changes. | **MEDIUM** because IAM cannot express every nested container invariant; script correctness is security-critical. |
| J | Artifact identity | Mutable `latest`, branch, or semantic tag is deployed. | Runtime artifact cannot be traced and may change without review. | Full source SHA resolves to one immutable ECR digest; ECS URI uses `@sha256:`; reject tag-addressed registration. | **LOW** with ECR immutability and digest assertion. |
| K | Image security at deployment | An old digest or an image with newly disclosed HIGH/CRITICAL findings is promoted. | Known vulnerable workload is deployed. | Main ancestry; existing commit-tag check; repository-scoped `DescribeImageScanFindings`; require active continuous scan and zero active HIGH/CRITICAL findings; fail closed on missing/stale state. | **MEDIUM** — vulnerability intelligence can change immediately after the check. |
| L | Deployment target | Correct image is deployed to the wrong cluster or service. | Unintended workload impact. | Environment-scoped exact names/ARNs; allowed account/Region; exact service policy resource; compare described cluster, service, target group, and task family before mutation. | **LOW** after controls. |
| M | Deployment serialization | Two promotions update the service concurrently. | Race, ambiguous evidence, or rollback to an unintended revision. | GitHub concurrency group `ecs-deployment-nonprod` with `cancel-in-progress: false`; one manual promotion at a time. | **LOW**; out-of-band human/API updates remain possible and appear as drift/evidence mismatch. |
| N | Runtime invariant integrity | Cloning/remapping removes non-root, read-only, capability, health-check, or logging controls. | Privilege escalation, loss of monitoring, or unhealthy deployment. | Exact pre-registration invariants; allowlisted payload; post-registration revalidation; image-only semantic diff; fail closed on unexpected optional fields. | **MEDIUM** because transformation code remains a high-value component. |
| O | Credential boundary | Static AWS access keys are stored in GitHub, local operator configuration, or logs. | Long-lived credential theft and replay. | GitHub OIDC only for automation; IAM Identity Center for operator access; short-lived chained sessions; no AWS key secrets; token/credential masking; evidence excludes tokens. A discovered legacy local credential was removed after its server-side key was verified inactive, and repository/history scans found no exposure. | **LOW** while the legacy server-side key remains inactive and no secret-based fallback is introduced; optional key deletion is a separate IAM mutation. |
| P | GitHub Actions supply chain | A compromised/floating third-party action executes in an OIDC-capable job. | Theft or misuse of short-lived deployment credentials. | Immutable commit SHAs for all actions; minimal actions; shell/AWS CLI for sensitive transformation; `persist-credentials: false`; job-level minimal permissions. | **MEDIUM** — immutable pinning prevents tag movement but not compromise of the pinned code. |
| Q | ECS service configuration | `UpdateService` changes desired count, network, public IP, load balancer, or deployment settings. | Availability loss or unintended exposure. | Exact-service IAM scope; invocation supplies only cluster, service, and task-definition ARN; post-update comparison of immutable service fields; no network mutation actions. | **LOW** after negative tests. |
| R | Deployment/rollback boundary | New revision fails partially or leaves mixed tasks. | Outage, partial rollout, or uncertain serving version. | Existing ECS circuit breaker and rollback; wait for stability; verify `1/1/0`, completed rollout, digest, and target health; fail workflow and preserve evidence; no repeated force deployment. | **MEDIUM** because one-task NonProd capacity has limited resilience during failures. |
| S | Terraform/CD ownership | CD moves the service pointer while Terraform still owns it exactly. | Persistent drift or later Terraform apply reverts the deployment. | Implemented Option B: service-only `ignore_changes = [task_definition]`; every other Terraform control remains owned; a post-deployment plan is still required after a future live promotion. | **LOW** after the narrow lifecycle change. |
| T | Rollback artifact | Circuit breaker rolls back to a previously safe digest that is now vulnerable. | Service recovers availability onto a known-vulnerable image. | Recheck candidate and current rollback-target digests before update; continuous Inspector; EventBridge HIGH/CRITICAL detection; incident path if current digest fails. | **HIGH** — a finding can appear between the check and automatic rollback, and rollback prioritizes service recovery. |
| U | Public boundary | Deployment opens ALB/task ingress or assigns a public IP. | Unauthorized public exposure. | Deployer has no network or ELB mutation; UpdateService payload excludes network fields; verify no task public IP and zero ALB ingress; subsequent Terraform plan. | **LOW** after verification; independent administrator changes remain outside workflow authority. |
| V | Audit/evidence boundary | Logs, source-to-digest mapping, approval, or deployment result are missing or manipulated. | Deployment cannot be attributed or investigated. | GitHub summary/logs; Environment approval record; canonical sanitized manifest and checksum; 90-day workflow artifact; manual PR-only durable record; CloudTrail role/PassRole/ECS events; ECS events; Flow Logs; runtime alarms; Inspector/Security Hub; confirmed human alert destination. | **MEDIUM** — GitHub evidence is bounded to 90 days, no external immutable archive exists, and durable promotion remains a human review step. |

## Control ownership

- **Implemented baseline:** immutable ECR tags/digest, publication scanning,
  private Fargate runtime, execution-role least privilege, circuit breaker,
  application/flow logging, runtime alarms, and Inspector/EventBridge signals.
- **Implemented Stage 9 controls:** dedicated deploy roles, Environment
  approval, deployment workflow, provenance/invariant gates, narrow Terraform
  ownership seam, deployment verification, serialized execution, and
  fail-closed rollback classification.
- **Organization-owned controls:** CloudTrail, GuardDuty, Security Hub, and
  Inspector service configuration.

## Design conclusions

The selected design has no unresolved source-architecture blocker. OIDC claim
validation, the narrow Terraform ownership seam, dedicated roles, Environment
approval, and task-definition/service-update tests are implemented. The first
live promotion remains deferred until a distinct scan-clean trusted published
candidate exists and the owner approves the mutation.

The remaining HIGH residual risk is rollback to a digest whose vulnerability
state changes during deployment. Human delivery and the evidence-retention
model are now validated, with the bounded-retention limitation recorded as
MEDIUM. Neither condition is a reason to grant broader deployment authority.
See the full [Stage 9 CD design](stage-9-cd-design.md) for the permission matrix
and deployment sequence.
