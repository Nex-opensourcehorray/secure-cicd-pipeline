# Secure CI/CD Pipeline — Codex Operating Rules

## Project

This repository implements a secure AWS CI/CD portfolio project focused on:

- application testing
- Docker containerization
- automated security scanning
- Terraform Infrastructure as Code
- GitHub Actions
- GitHub OIDC federation to AWS
- Amazon ECR image publication
- later ECS deployment
- least-privilege IAM
- controlled deployment gates
- traceable software supply-chain practices

The project is intended as a cloud / DevSecOps / cloud-security portfolio.

This repository is not a production environment.

Do not represent any stage as deployed, validated, operational, or production-ready unless supporting evidence exists.

---

# Current project direction

The project is being implemented incrementally.

Known stage direction:

```text
Stage 0–5
Application, testing, Docker, CI/security foundations

Stage 6
Terraform + ECR + GitHub OIDC Foundation

Stage 7
Trusted ECR Image Publication

Later stages
ECS / networking / deployment / runtime validation
```

Closed stages must not be reinterpreted as incomplete unless current evidence shows an actual defect, regression, security issue, or drift.

Do not skip directly into ECS or production-style deployment merely because earlier Terraform or Docker code validates.

---

# Working principle

Work incrementally.

For every mission:

1. Inspect existing repository files first.
2. Understand the current stage and intended scope.
3. Identify dependencies.
4. Identify security implications.
5. Prefer the smallest safe change.
6. Preserve existing working functionality.
7. Run applicable local tests.
8. Run formatting and validation.
9. Review changes before recommending publication or deployment.
10. Stop at explicit approval gates.

Do not silently broaden mission scope.

Do not hide security findings.

Do not make a configuration less secure merely to make a test pass.

---

# Source of truth

For repository work, use this order of authority:

```text
1. Explicit current owner instruction
2. This AGENTS.md
3. Existing stage documentation / mission evidence
4. Existing repository implementation
5. Conservative security best practice
```

If a lower-priority source conflicts with a higher-priority source, follow the higher-priority source and report the inconsistency.

---

# Actions allowed without additional owner approval

Codex may perform the following locally unless a current mission explicitly restricts them:

- read repository files
- inspect Git history
- inspect Git status
- inspect Git diff
- create or modify local source files
- create or modify tests
- create or modify documentation
- create or modify Terraform configuration
- create or modify GitHub Actions workflow files
- create or modify Dockerfiles
- create or modify `.dockerignore`
- create or modify security-scanning configuration
- create or modify scripts
- run local application tests
- run static analysis
- run dependency scans
- run container scans
- run Docker builds
- run containers locally
- run local smoke tests
- run `terraform fmt`
- run `terraform fmt -check`
- run `terraform validate`
- run `terraform init -backend=false`
- run non-mutating Terraform plan commands when allowed by the active mission
- inspect Terraform plans
- run read-only AWS CLI commands when necessary
- run read-only GitHub CLI/API commands
- inspect GitHub Actions results
- inspect Amazon ECR metadata using read-only AWS commands
- recommend remediation

Local file modification is not authorization to publish those changes.

---

# Explicit approval required

Stop and request explicit owner approval before performing any of the following.

## Terraform

- `terraform apply`
- `terraform destroy`
- `terraform import`
- `terraform state rm`
- `terraform state mv`
- `terraform state push`
- any Terraform state mutation
- applying a saved Terraform plan

## AWS

- create AWS resources
- update AWS resources
- delete AWS resources
- push an image to Amazon ECR
- delete an ECR image
- modify an ECR lifecycle policy on a live repository
- create or modify IAM roles
- create or modify IAM policies
- expand IAM privileges
- create or modify an OIDC provider
- modify IAM trust relationships
- create or modify ECS resources
- register/deploy ECS task definitions
- create ECS services
- update ECS services
- create or modify VPCs
- create or modify subnets
- create or modify route tables
- create or modify NAT gateways
- create or modify security groups
- create or modify load balancers
- create or modify DNS
- create or modify KMS keys
- modify security monitoring controls
- modify live AWS logging
- modify live backup settings

## Git / GitHub

- `git push`
- force push
- branch deletion
- history rewriting
- `git reset --hard` when it could discard owner work
- repository creation
- repository deletion
- repository visibility changes
- changing the default branch
- branch protection or ruleset mutation
- creation/modification of GitHub repository secrets
- creation/modification of GitHub environments
- publication of releases
- manual triggering of a deployment workflow that will mutate AWS

Never interpret silence as approval.

Approval applies only to the explicitly described operation.

Do not reuse approval from one stage to authorize a later stage.

---

# Approval-gate format

Before requesting approval for a mutating operation, report:

```text
ACTION GATE — <operation name>

Operation:
<exact action>

Resources affected:
<resources>

Environment:
<environment>

AWS account:
<account if applicable>

Region:
<region if applicable>

Creates:
<list/count>

Updates:
<list/count>

Destroys:
<list/count>

IAM changes:
<summary>

Network changes:
<summary>

Expected external effects:
<summary>

Destructive changes:
YES / NO

Rollback:
<rollback method>

Evidence reviewed:
<tests / plan / scans / validation>
```

Do not execute the operation until explicit approval is given.

---

# Terraform safety rules

Terraform is an implementation mechanism, not permission to change AWS.

Before recommending any `terraform apply`:

1. Run:

```text
terraform fmt -check
terraform validate
```

2. Run an appropriate plan.

3. Inspect the complete proposed change set.

4. Report:

```text
CREATE
UPDATE
DESTROY
REPLACE
```

5. Separately identify:

- IAM changes
- OIDC trust changes
- ECR changes
- ECS changes
- networking changes
- security-group changes
- KMS changes
- logging changes
- state-address changes

Any unexpected destroy or replacement is a blocker until reviewed.

Do not automatically remove `prevent_destroy` protections.

Do not change lifecycle controls merely to make an apply succeed.

---

# Terraform backend rules

Prefer:

```text
terraform init -backend=false
```

for formatting/validation-only work when remote state access is unnecessary.

Do not initialize or access live remote state merely to satisfy a local validation task.

Treat Terraform state as sensitive.

Never commit:

```text
*.tfstate
*.tfstate.*
*.tfplan
terraform.tfvars
*.tfvars
```

unless a file is explicitly a sanitized `.example` template.

---

# AWS execution rules

Classify AWS CLI commands as:

```text
READ-ONLY
```

or:

```text
MUTATING
```

before execution.

Examples of normally read-only operations:

```text
aws sts get-caller-identity
aws ecr describe-repositories
aws ecr describe-images
aws iam get-role
aws iam get-role-policy
aws iam list-attached-role-policies
aws ecs describe-services
aws ecs describe-task-definition
```

Read-only inspection does not authorize later mutation.

An authenticated AWS session is not approval to change resources.

---

# IAM security rules

Use least privilege.

Do not use or recommend broad permissions merely to simplify deployment.

Avoid:

```text
AdministratorAccess
PowerUserAccess
iam:*
ecr:*
ecs:*
*
```

unless an explicit technical justification exists and the owner approves it.

GitHub Actions roles must receive only the permissions required by their stage.

For ECR publication, repository-scoped actions should be restricted to the exact ECR repository ARN whenever supported.

`ecr:GetAuthorizationToken` may require `"Resource": "*"`, but that exception must not be used to broaden unrelated ECR actions.

For the current Stage 7 two-account publication path, the Management broker
role may only call `sts:AssumeRole` against:

```text
arn:aws:iam::119033255630:role/secure-cicd-pipeline-nonprod-ecr-publisher
```

The NonProd publisher role may call `ecr:GetAuthorizationToken` on `*`. Its
repository-scoped permissions must contain only:

```text
ecr:BatchCheckLayerAvailability
ecr:CompleteLayerUpload
ecr:DescribeImages
ecr:InitiateLayerUpload
ecr:PutImage
ecr:UploadLayerPart
```

against exactly:

```text
arn:aws:ecr:ap-southeast-1:119033255630:repository/secure-cicd-demo
```

---

# GitHub OIDC rules

GitHub OIDC is the preferred AWS authentication method.

Do not introduce long-lived AWS access keys into GitHub Actions unless the owner explicitly chooses that architecture.

Normal GitHub Actions AWS authentication should not require repository secrets containing:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
```

OIDC trust must be narrowly scoped.

Expected identity provider:

```text
token.actions.githubusercontent.com
```

Expected audience:

```text
sts.amazonaws.com
```

Restrict trust to the intended repository.

For this project:

```text
Nex-opensourcehorray/secure-cicd-pipeline
```

This repository uses GitHub's immutable default subject form. Its exact subject
for `main` is:

```text
repo:Nex-opensourcehorray@82328818/secure-cicd-pipeline@1409968457:ref:refs/heads/main
```

The trust policy must also check these claims independently:

```text
aud = sts.amazonaws.com
repository_owner_id = 82328818
repository_id = 1409968457
ref = refs/heads/main
```

The numeric owner and repository IDs are part of the subject and prevent name
reuse from reproducing the trusted identity. Do not restore the legacy
name-only subject.

Do not broaden trust to patterns such as:

```text
repo:Nex-opensourcehorray/*
repo:*/*
*
```

merely to fix authentication.

If GitHub Environments are later introduced, review the expected OIDC subject
before changing AWS trust.

---

# GitHub Actions security rules

Default workflow permissions should be minimal.

Prefer:

```yaml
permissions:
  contents: read
```

Only workflows requiring OIDC should receive:

```yaml
permissions:
  contents: read
  id-token: write
```

Do not grant write permissions unless the workflow genuinely requires them.

Pay attention to:

- untrusted pull-request execution
- `pull_request_target`
- script injection through branch names or PR metadata
- secrets exposed to forked PRs
- dependency/action pinning
- artifact integrity
- cache poisoning
- excessive token permissions

Never expose privileged AWS OIDC credentials to untrusted pull-request code.

Deployment or image-publication workflows should be restricted to trusted triggers.

---

# GitHub Actions third-party actions

Prefer well-maintained trusted actions.

Where practical, pin third-party actions to immutable commit SHAs.

If using a major-version tag such as:

```text
actions/checkout@v4
```

document the choice.

Do not introduce obscure or unnecessary third-party Actions when an official or simple local alternative exists.

---

# Docker security rules

Docker images must not contain credentials or sensitive local files.

Review:

```text
Dockerfile
.dockerignore
build context
image history
image environment
image labels
```

Never copy:

```text
.env
.git/
AWS credentials
private keys
terraform.tfstate
terraform.tfvars
secret files
developer home directories
```

into an image.

Prefer:

- small runtime image
- multi-stage build where useful
- non-root runtime user
- explicit working directory
- minimum runtime packages
- deterministic dependency installation
- no unnecessary package-manager cache
- no development tooling in runtime image unless required

Do not run containers as root without documented technical justification.

---

# Container image publication rules

Stage 7 concerns trusted image publication.

Before the first ECR push, require evidence for:

```text
application tests
Docker build
container smoke test
container vulnerability scan
ECR configuration
OIDC trust
IAM permissions
source Git commit
image tag
```

The first ECR push is a separate AWS mutation gate.

Do not interpret approval for Terraform ECR/IAM creation as approval to push an image.

---

# Container tagging rules

Do not use `latest` as the authoritative deployment identity.

Prefer an immutable tag based on the Git commit.

Example:

```text
<git-commit-sha>
```

The authoritative deployed artifact should ultimately be identified by an ECR digest:

```text
sha256:<digest>
```

If convenient tags such as:

```text
dev
nonprod
candidate
```

are later added, the commit SHA and image digest remain the traceability source.

---

# ECR security rules

Amazon ECR repositories should normally use:

- private visibility
- tag immutability
- vulnerability scanning
- encryption
- lifecycle controls
- least-privilege push permissions

Do not create a public ECR repository for this project unless explicitly instructed.

Prefer:

```text
image_tag_mutability = "IMMUTABLE"
```

Do not weaken immutability merely because a workflow attempts to reuse an existing tag.

If a duplicate immutable tag exists, treat that as a workflow/versioning issue.

---

# Vulnerability scanning rules

Do not suppress vulnerabilities automatically.

Classify findings.

At minimum distinguish:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

A CRITICAL finding should normally block publication until reviewed.

HIGH findings should also be reviewed and should not be silently ignored.

Any exception must document:

- CVE/finding
- affected package
- exploitability/context
- compensating control
- reason for acceptance
- remediation plan

Never fabricate scan success.

---

# Application testing rules

Tests must reflect the actual application behavior.

Do not modify tests solely to hide a real application defect.

If a test fails:

1. determine whether the application or the test is wrong;
2. repair the correct component;
3. re-run the relevant suite;
4. report the actual result.

Do not report:

```text
PASS
```

unless the command actually succeeded.

---

# Secret-management rules

Never commit:

- passwords
- access keys
- secret keys
- tokens
- private certificates
- private keys
- registry passwords
- GitHub tokens
- AWS credentials
- application production secrets

Use placeholders in examples.

Example:

```text
<ROLE_ARN>
<ECR_REPOSITORY_ARN>
<AWS_ACCOUNT_ID>
```

A Secrets Manager ARN is metadata, not the secret value, but real operational identifiers should still be minimized in public portfolio material.

---

# Secret-discovery response

If a real credential or secret is discovered:

1. STOP the current task.
2. Do not reproduce the full secret unnecessarily.
3. Report the file and secret type.
4. Recommend revocation/rotation.
5. Explain that deleting the current file does not remove the secret from Git history.
6. Do not proceed with publication until exposure is addressed.

---

# Git rules

Before staging or publishing changes:

```text
git status
git diff
git diff --check
```

Review for:

- accidental secrets
- generated artifacts
- binary build outputs
- Terraform state
- Terraform plans
- `.env`
- local configuration
- unnecessary image archives

Do not run `git push` without explicit owner approval.

Do not perform history rewrite without explicit owner approval.

---

# Repository hygiene

Normally track:

```text
source code
tests
Dockerfile
.dockerignore
Terraform .tf files
.terraform.lock.hcl
GitHub Actions workflows
README.md
AGENTS.md
sanitized examples
documentation
```

Normally ignore:

```text
.env
.env.*
*.tfstate
*.tfstate.*
*.tfplan
terraform.tfvars
*.tfvars
.terraform/
__pycache__/
.pytest_cache/
coverage outputs
virtual environments
local build outputs
temporary archives
Docker image tarballs
credentials
private keys
```

Example files such as:

```text
terraform.tfvars.example
.env.example
```

may be committed only when they contain placeholders and no sensitive values.

---

# Stage-boundary rules

Do not automatically proceed from one stage into another simply because the current stage passes.

In particular:

```text
Stage 6
Terraform + ECR + GitHub OIDC Foundation
```

does not authorize:

```text
Stage 7
ECR image publication
```

and Stage 7 does not authorize:

```text
ECS deployment
network creation
load balancer creation
runtime rollout
```

Each meaningful AWS mutation requires the applicable owner approval gate.

---

# Stage 7 specific rules

Stage 7 objective:

```text
Trusted ECR Image Publication
```

Expected chain:

```text
Git commit
   ↓
tests
   ↓
security validation
   ↓
Docker build
   ↓
container scan
   ↓
GitHub OIDC
   ↓
Management broker role
   ↓
NonProd ECR publisher role
   ↓
private ECR
   ↓
immutable image digest
```

Stage 7 must not deploy ECS.

Before first ECR publication, stop at:

```text
ACTION GATE — FIRST TRUSTED ECR IMAGE PUBLICATION
```

Include:

```text
source commit
image tag
image scan
tests
target ECR repository
AWS account
region
expected image mutation
```

No image push without explicit approval.

---

# Later ECS stage rules

When ECS work begins later, treat it as a separate mission.

Do not assume that ECS/networking modules being present authorizes deployment.

Before ECS apply or deployment, explicitly review:

- VPC architecture
- subnet placement
- internet/NAT requirements
- security groups
- task execution role
- task role
- image digest
- CloudWatch logging
- secrets injection
- health checks
- desired count
- rollback behavior
- load balancer exposure
- autoscaling
- deployment circuit breaker
- container privilege model

Do not deploy an image by mutable tag when a digest-based reference is available.

---

# Network security rules

Private-by-default is preferred.

Do not add:

```text
0.0.0.0/0
```

inbound access without explicit documented justification.

If public ingress is required, restrict it to the intended load-balancer/public boundary rather than directly exposing ECS tasks.

Database or internal service tiers must not be publicly reachable by default.

Avoid NAT Gateway creation unless the workload actually requires it and the owner understands the recurring cost.

---

# Cost awareness

Report meaningful recurring AWS cost drivers before deployment.

Examples:

- NAT Gateway
- Application Load Balancer
- ECS/Fargate runtime
- CloudWatch Logs
- ECR storage
- interface VPC endpoints
- KMS
- data transfer

Do not add expensive fixed-cost infrastructure merely because it is architecturally common.

Use requirements to justify it.

---

# Evidence rules

Evidence must describe what actually occurred.

Use terms carefully:

```text
VALIDATED
```

means a real validation command/test ran successfully.

```text
PLANNED
```

means Terraform produced a reviewed proposal.

```text
DEPLOYED
```

means the resource was actually created/updated.

```text
PUBLISHED
```

means the image actually exists in ECR.

```text
DESIGN ONLY
```

means no live deployment occurred.

Do not equate:

```text
terraform validate
```

with successful AWS deployment.

Do not equate:

```text
docker build
```

with ECR publication.

Do not equate:

```text
ECR publication
```

with ECS deployment.

---

# Validation before stage closure

Run applicable checks such as:

```text
git diff --check
application tests
terraform fmt -check -recursive
terraform validate
Docker build
container smoke test
container vulnerability scan
secret scan
```

Use actual repository commands rather than assumptions.

Record failures honestly.

---

# Security findings

Immediately report:

- leaked secrets
- excessive IAM
- overly broad OIDC trust
- public cloud exposure
- missing encryption
- mutable image risks
- critical vulnerabilities
- missing logging
- unsafe GitHub Actions triggers
- destructive Terraform changes
- insecure Docker configuration
- root container execution without justification
- untrusted PR access to privileged credentials

Classify findings where useful:

```text
BLOCKER
HIGH
MEDIUM
LOW
OBSERVATION
```

Do not silently remediate a meaningful security issue without reporting it.

---

# Stop conditions

Stop immediately when:

- an explicit owner approval gate is reached;
- a credential or secret is exposed;
- Terraform proposes unexpected destruction/replacement;
- IAM/OIDC trust is broader than intended;
- a live AWS mutation would be required;
- the task would cross into a later stage;
- repository history rewrite would be required;
- a security control must be weakened to proceed.

Provide the owner with the blocker, evidence, and safest next action.

---

# Final mission report

At the end of each mission, report:

## Mission

```text
<stage / substage>
```

## Overall Result

Use one of:

```text
PASS
PASS WITH WARNINGS
BLOCKED
BLOCKED AT APPROVAL GATE
```

## Files Changed

List modified/created/deleted files.

## Validation

Report actual results for applicable checks.

## Security Findings

List findings and severity.

## AWS Mutations

List exact mutations.

If none:

```text
NONE
```

## Git/GitHub Mutations

List exact mutations.

If none:

```text
NONE
```

## Approval Gate

State whether further owner approval is required.

## Next Safe Action

Describe only the next stage-appropriate step.

---

# Core principle

This project should demonstrate that secure cloud engineering is not only about making deployment work.

It must demonstrate:

```text
controlled change
least privilege
reproducibility
traceability
security validation
explicit approval
rollback awareness
supply-chain integrity
honest evidence
```

Prefer a blocked deployment with clear evidence over an insecure deployment that merely succeeds.
