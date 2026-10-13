# Secure CI/CD Pipeline on AWS

A portfolio implementation of a security-focused CI/CD platform for a Python
API running on private Amazon ECS Fargate infrastructure. The project combines
GitHub Actions, Docker, Terraform, GitHub OIDC federation, cross-account AWS
role chaining, Amazon ECR, deployment approval, immutable artifact promotion,
and fail-closed validation.

This is a validated NonProd portfolio environment, not a production service.
The continuous-deployment capability is implemented, but the first mutating
ECS promotion and a live failed-deployment rollback exercise are intentionally
deferred.

## Project Overview

The repository demonstrates a complete path from source validation to an
approved, digest-pinned ECS deployment:

```text
trusted main source
  -> CI and security validation
  -> manual image publication
  -> immutable ECR digest
  -> manual deployment request
  -> GitHub Environment approval
  -> GitHub OIDC and cross-account role chaining
  -> time-of-deploy vulnerability check
  -> allowlisted ECS task-definition revision
  -> exact service pointer update
  -> runtime and rollback-outcome verification
```

## Architecture

- A Management AWS account owns the GitHub OIDC provider and separate broker
  roles for publication and deployment.
- A NonProd AWS account owns the private ECR repository, dedicated ECR
  publisher, dedicated ECS deployer, and private Fargate runtime.
- ECS tasks run in private subnets without public IPs or NAT-based internet
  egress. Private endpoints provide ECR, CloudWatch Logs, and S3 connectivity.
- An internet-facing Application Load Balancer exists in a fail-closed state:
  its security group has no public inbound rule.

See [architecture](docs/architecture.md) and the
[Stage 9 CD design](docs/stage-9-cd-design.md).

## Security Controls

- GitHub Actions permissions default to `contents: read`.
- Only AWS-authenticating jobs receive `id-token: write`.
- All reusable actions are pinned to full immutable commit SHAs.
- No static AWS access keys are stored in GitHub.
- OIDC trust binds audience, immutable repository subject, numeric owner and
  repository IDs, exact `main` ref, and the `nonprod` Environment.
- Publication and deployment use separate Management and NonProd identities.
- HIGH and CRITICAL vulnerability findings block publication and deployment.
- ECS task definitions use immutable ECR digest references.
- The application container runs non-root with a read-only root filesystem,
  no task role, no privileged mode, and all Linux capabilities dropped.
- Terraform, workflow, secret, dependency, SAST, and container checks run in
  the GitHub security pipeline.
- The active `main-governance` ruleset requires pull requests, seven successful
  CI/Security checks, current-branch freshness, and resolved review threads;
  it also blocks deletion, force pushes, and ordinary direct pushes to `main`.
- Application production and development dependencies are generated from
  small exact-version input files into complete SHA-256 hash locks. Docker,
  CI, and publication validation install them with `--require-hashes`.
- Future ECS deployment runs produce a canonical sanitized evidence manifest
  and checksum as a 90-day GitHub artifact. Durable deployment records require
  separate human review and a normal governed pull request.
- Runtime and HIGH/CRITICAL image signals converge on one source-restricted SNS
  topic. Human subscription ownership is separated from Terraform so private
  endpoint data does not enter state or source.

## CI Pipeline

Pull requests and pushes to `main` run Python tests and container validation.
The Security workflow runs Bandit, pip-audit, Gitleaks, Checkov, and Trivy.
Container validation checks readiness, API behavior, Docker health, and the
non-root runtime identity.

## Image Publication

Image publication is a manual trusted-main workflow. It builds the checked-out
commit, blocks HIGH/CRITICAL findings, authenticates through the dedicated
publication role chain, pushes a commit-SHA tag to the immutable private ECR
repository, and records the returned digest. Publication authority has no ECS
deployment permission.

## Continuous Deployment

The deployment workflow accepts only a lowercase 40-character source SHA. It
proves trusted-main ancestry and successful CI, Security, and publication
evidence before entering the protected `nonprod` Environment. It resolves the
commit tag to one ECR digest internally and never accepts an arbitrary digest
as deployment authority.

After approval, the workflow rechecks the candidate and rollback digest for
active HIGH/CRITICAL findings, clones the current task definition through an
allowlist, changes only the image URI, registers one revision, and updates only
the exact ECS service task-definition pointer.

At a terminal result it builds an allowlisted evidence manifest for success,
confirmed automatic rollback, pre-mutation failure, or unverified failure. The
workflow uploads only the manifest and checksum, records both manifest and
artifact digests, and deletes raw AWS working data afterward. It has no source
write authority; durable records under `docs/evidence/deployments/` require a
separate reviewed PR.

## AWS IAM / OIDC Model

```text
GitHub nonprod Environment
  -> Management deployment broker
  -> NonProd ECS deployer
  -> exact task family, service, cluster, and execution role
```

The Management broker can only assume the exact NonProd deployment role. The
NonProd deployer has required metadata reads plus controlled
`RegisterTaskDefinition`, exact-service `UpdateService`, and `PassRole` for the
exact ECS execution role. It has no image publication, IAM administration,
network mutation, task execution, task stopping, or Terraform authority.

## Runtime Security

The deployed baseline uses private Fargate networking, service endpoints,
least-privilege execution IAM, digest-pinned images, CloudWatch application
logs, VPC Flow Logs, alarms, EventBridge security signals, and an ECS
deployment circuit breaker. Detailed live Stage 8 evidence is recorded in
[runtime evidence](docs/stage-8-runtime-evidence.md).

## Alerting and Response

The four CloudWatch alarms and two focused EventBridge rules route actionable
runtime and security conditions to the existing NonProd SNS topic. One
human-owned email subscription is confirmed, and the owner confirmed receipt
of one separately approved controlled test. The endpoint is managed as a
manual operational integration, never as repository data or Terraform state.

GitHub remains the native notification path for CI, Security, PR, and
deployment-workflow failures. Successful runs, normal ECS lifecycle events,
normal CPU/memory, and LOW/MEDIUM Inspector findings are intentionally excluded
from human alerting. See the
[NonProd alert response runbook](docs/runbooks/nonprod-alert-response.md) for
triage, acknowledgement, privacy, rotation, and gated delivery-test procedures.

## Rollback Model

The deployment workflow observes ECS automatic circuit-breaker rollback; it
does not issue a manual rollback. The previous revision and digest are captured
before mutation, both candidate and rollback images are scanned, and the
actual serving revision determines the result. Confirmed automatic rollback
still fails the workflow, while ambiguous state fails closed.

Rollback logic has 57 deterministic tests. A live failed deployment and live
automatic rollback have not been executed.

## Validation & Testing

The merged Stage 9 baseline passed:

- application and container tests;
- SAST, dependency, secret, IaC, and container scans;
- workflow linting and immutable-action review;
- all deployment-helper tests;
- Terraform formatting and validation across four roots; and
- read-only OIDC, role-chain, Environment, and runtime preflight checks.

See [Stage 9 closure evidence](docs/stage-9-closure-evidence.md) for the final
status and evidence boundaries.

Stage 10 governance, dependency integrity, evidence retention, and human
alerting controls passed comprehensive validation on the feature-source SHA
recorded in [Stage 10 validation evidence](docs/stage-10-validation-evidence.md).
Operator access was revalidated through IAM Identity Center; a discovered
legacy local credential was removed after its server-side key was confirmed
inactive, with no repository or Git-history exposure found. See the concise
[Stage 10 closure evidence](docs/stage-10-closure-evidence.md) for the complete
control map, residual risks, deferred exercises, and final PR boundary.

## Known Limitations

- The `nonprod` approval boundary is single-maintainer: self-review is allowed,
  so it is not four-eyes approval. Administrator bypass is disabled.
- Python-installed security tools retain exact top-level versions but their
  larger dependency graphs are not cryptographically artifact-hash locked.
- GitHub workflow logs and deployment-evidence artifacts are bounded to the
  verified 90-day repository retention period; no external immutable archive
  is currently configured.
- One manually governed human SNS email subscription is confirmed and the
  owner confirmed receipt of one controlled delivery test. The private endpoint
  remains outside Terraform state and repository evidence; the solo owner is
  not a formal 24x7 on-call function.
- The first live ECS promotion is deferred because no distinct scan-clean,
  trusted published candidate was available at closure.
- The live rollback exercise is deferred and requires a separately approved,
  safe failure-test design.
- Vulnerability state can change after a rollback digest is checked and before
  an automatic rollback occurs.

## Repository Structure

```text
.github/workflows/     CI, security, publication, trust, and deployment flows
.github/scripts/       Fail-closed ECS deployment validation helper and tests
application/           FastAPI application, tests, and hardened Docker image
terraform/environments Management and NonProd Terraform roots
terraform/modules/     Reusable ECR, IAM, network, ECS, ALB, and monitoring code
docs/                  Architecture, threat model, controls, and stage evidence
```

## Skills Demonstrated

GitHub Actions, AWS IAM and OIDC, cross-account role chaining, Terraform,
Docker, Amazon ECR, ECS Fargate, private VPC networking, least privilege,
software-supply-chain validation, immutable artifacts, vulnerability gating,
deployment approvals, observability, rollback analysis, and evidence-driven
cloud-security engineering.
