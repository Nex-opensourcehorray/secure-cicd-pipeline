# Stage 10 Closure Evidence

> Result: **STAGE 10 IMPLEMENTATION COMPLETE; COMPREHENSIVE VALIDATION PASS;
> FINAL PR PENDING; FINAL MERGE PENDING**
>
> Closure review date: 2026-10-13. This record is sanitized and contains no
> credentials, tokens, private notification endpoint, or Terraform state.

## Scope and evidence boundary

Stage 10 implemented and validated repository governance, NonProd approval
governance, application dependency integrity, deployment-evidence retention,
and human-owned alerting. Detailed commands, counts, remote run IDs, and live
read-only findings are recorded in the
[Stage 10 comprehensive validation evidence](stage-10-validation-evidence.md).

The validated feature-source SHA is
`73a6862dd5c442bc844bfb35442ca228f78cc17c`. The later validation-evidence SHA
is `40512cd88a882b34c5564534b7f0b57623406a84`. This closure change is
documentation-only; its exact commit SHA is reported at the final PR gate so
the document does not make a circular claim about its own commit.

| Stage | Closure state |
| --- | --- |
| 10.0 | PASS — governance and operational hardening architecture documented |
| 10.1 | PASS — active `main-governance` ruleset applied and verified |
| 10.2 | PASS — NonProd Environment governance revalidated; administrator bypass disabled |
| 10.3 | PASS — application production and development dependency graphs hash locked |
| 10.4 | PASS — 90-day sanitized deployment-evidence controls validated |
| 10.5 | PASS — one confirmed human subscription and controlled delivery verified |
| 10.6 | PASS — comprehensive local, GitHub, Terraform, and read-only AWS validation complete |
| 10.7 | READY FOR FINAL PR — PR creation and merge remain separately gated |

## Full Stage 10 diff review

The reviewed feature delta contains 21 files and no Terraform `.tf` change.
Every changed path is classified below; the same file can support more than
one control, but it is listed once here.

| Category | Files |
| --- | --- |
| Dependency integrity | `application/Dockerfile`; `application/requirements.in`; `application/requirements.txt`; `application/requirements-dev.in`; `application/requirements-dev.txt` |
| Workflow enforcement | `.github/workflows/ci.yml`; `.github/workflows/deploy.yml`; `.github/workflows/deploy-ecs.yml` |
| Deployment evidence | `.github/scripts/build_deployment_evidence.py`; `.github/scripts/tests/test_build_deployment_evidence.py`; `docs/evidence/deployments/README.md`; `docs/evidence/deployments/deployment-evidence.schema.json` |
| Alerting and response | `docs/runbooks/nonprod-alert-response.md`; `docs/runtime-security-controls.md`; `terraform/environments/nonprod/runtime/README.md` |
| Governance and security documentation | `docs/architecture.md`; `docs/stage-10-governance-hardening.md`; `docs/stage-10-validation-evidence.md`; `docs/stage-10-closure-evidence.md`; `docs/threat-model.md` |
| Portfolio documentation | `README.md` |

The workflow names and the seven required job names remain stable. All 30
external Action references use full 40-character commit SHAs. The privileged
deployment job alone receives `id-token: write`; the provenance job alone
receives `actions: read`; default source access remains read-only.

## Governance and approval controls

- Ruleset `24978564`, `main-governance`, is active for the default branch.
- It requires pull-request flow, resolved review threads, and seven strict,
  current-branch GitHub Actions checks; deletion and non-fast-forward updates
  are blocked.
- Required approving reviews remain `0`. The solo owner has PR-only ruleset
  bypass, not direct-push bypass. This is not independent four-eyes approval.
- The `nonprod` Environment has administrator bypass disabled, one owner
  reviewer with self-review allowed, an exact `main` deployment branch policy,
  six expected variables, and zero secrets.
- PR creation, PR approval, merge, deployment, and publication are not implied
  by this evidence.

Expected governed checks:

1. Python tests
2. Container validation
3. Python SAST
4. Dependency audit
5. Secret scan
6. Infrastructure-as-code scan
7. Container vulnerability scan

## Dependency and supply-chain integrity

- Production: 14 of 14 package entries are hash protected; zero are unhashed.
- Development: 23 of 23 package entries are hash protected; zero are unhashed.
- The Docker build, CI install, and publication workflow install with
  `--require-hashes`.
- Fresh isolated installs, `pip check`, strict dependency audit, deterministic
  regeneration, application tests, action pin review, workflow linting, and
  the governed remote checks passed at the validated source SHA.
- The Docker base image is digest pinned and the runtime is non-root.

## Deployment-evidence retention

- Repository workflow, check, artifact, and log retention is 90 days, the
  public-repository maximum reported by the live settings page.
- The allowlisted draft 2020-12 schema and generator retain only sanitized
  deployment facts, a manifest digest, and a separate checksum.
- The workflow fails if the evidence files are absent, uploads them for 90
  days, and deletes raw AWS working material.
- It has no repository write permission. A durable manifest under
  `docs/evidence/deployments/` still requires human review and a normal PR.
- No fabricated live deployment record is stored in the repository.

## Human alerting and credential hygiene

- Four exact CloudWatch alarms were `OK`; two focused EventBridge rules were
  enabled; all six routes targeted the expected NonProd SNS topic.
- The topic policy permits only the intended CloudWatch and EventBridge service
  publishers, with the exact NonProd source account and no wildcard principal.
- Exactly one human email subscription is confirmed. Its endpoint is
  **REDACTED**. The owner confirmed receipt of one separately approved
  controlled test in Stage 10.5; Stage 10.6 and 10.7 sent no message.
- Management and NonProd IAM Identity Center sessions passed read-only identity
  checks. IAM Identity Center remains the operator access mechanism.
- A legacy local static credential was removed after its server-side key was
  verified inactive. Repository and complete-history scans found no exposure.
  Optional deletion of that inactive server-side key remains a separate IAM
  mutation decision.

## Terraform, CI, and security validation

- `terraform fmt -check -recursive terraform` passed.
- All four established Terraform roots validated and produced refresh plans
  with **NO CHANGES**. No apply, state mutation, replacement, or destruction
  occurred.
- Checkov reported 303 passed, 0 failed, and 20 documented skips.
- CI run `38387312620` passed 2 of 2 governed jobs.
- Security run `38387318507` passed 5 of 5 governed jobs.
- Total governed remote checks: **7/7 PASS** at validated source SHA
  `73a6862dd5c442bc844bfb35442ca228f78cc17c`.
- Secret and privacy checks found no repository credential or private alert
  endpoint. No AWS credential value or key identifier is recorded here.

## Residual risks and deferred evidence

- **MEDIUM — Independent approval:** solo-owner self-review does not provide
  four-eyes separation, although Environment administrator bypass is disabled.
- **LOW — Security-tool dependencies:** exact top-level tool versions are used,
  but the larger transitive graphs are not fully artifact-hash locked.
- **LOW — Alpine artifact resolution:** the security floor is not a complete
  repository-artifact lock.
- **LOW — Legacy IAM hygiene:** the remaining server-side key is inactive; its
  optional deletion requires a separate approved IAM mutation.
- **MEDIUM — Evidence durability:** native logs and artifacts are bounded to 90
  days and no external immutable archive is configured.
- **HIGH — Rollback vulnerability timing:** vulnerability intelligence can
  change after a rollback digest is checked and before automatic rollback.
- **MEDIUM — Human operations:** one owner receives alerts; there is no formal
  independent on-call rotation or 24x7 service commitment.

The first live ECS promotion and a live failure/automatic-rollback exercise
remain deferred, separately approved operational evidence exercises. Their
absence does not convert source validation into deployment evidence.

## Explicit non-claims

- This repository is a portfolio NonProd environment, not production.
- Stage 10.7 did not publish an image, deploy or roll back ECS, apply Terraform,
  change IAM, change GitHub governance, or send an alert.
- No pull request has been opened and nothing has been merged to `main` by this
  closure record.
- `terraform validate`, plans, tests, and scans do not mean deployed.
- Stage 10 becomes merged history only after the separately approved final PR
  is opened, its governed checks pass, it is reviewed, and merge is authorized.
