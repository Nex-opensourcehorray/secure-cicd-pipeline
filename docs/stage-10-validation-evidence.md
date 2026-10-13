# Stage 10 Comprehensive Validation Evidence

> Result: **PASS — STAGE 10 COMPREHENSIVE VALIDATION COMPLETE**
>
> Validation date: 2026-10-13. This record contains sanitized outcomes only.
> It does not contain the human notification endpoint, credentials, tokens, or
> Terraform state.

## Scope

This validation covers the implemented Stage 10.0 architecture and Stages
10.1–10.5 controls: `main` governance, NonProd deployment approval governance,
dependency and artifact integrity, deployment-evidence retention, and
human-owned alert delivery. Stage 10.6 performed local, GitHub, and read-only
AWS validation. It did not publish an image, deploy or roll back ECS, apply
Terraform, change IAM, or change live governance settings.

| Stage | State |
| --- | --- |
| 10.0 | PASS — governance and operational hardening architecture documented |
| 10.1 | PASS — active `main-governance` ruleset applied and verified |
| 10.2 | PASS — NonProd Environment governance revalidated; admin bypass disabled |
| 10.3 | PASS — application dependency graphs reproducibly hash locked |
| 10.4 | PASS — 90-day evidence retention and sanitized manifest controls validated |
| 10.5 | PASS — HUMAN ALERT DELIVERY VERIFIED |
| 10.6 | PASS — comprehensive validation complete |

## Git Baseline

- Default branch baseline: `main` at
  `6c35fad916f531863bc82e39d821126f7f0feca9`.
- Feature branch: `stage-10-hardening-completion`.
- Validated feature-source SHA:
  `73a6862dd5c442bc844bfb35442ca228f78cc17c`.
- At validation start the feature branch matched its remote, was zero commits
  behind and three commits ahead of `origin/main`, and the worktree was clean.
- The source delta contained 18 files with 2,745 additions and 153 deletions;
  no Terraform `.tf` file changed.
- No reset, force push, history rewrite, PR, or merge was performed.
- This evidence document and stale-status corrections are a later
  documentation-only commit; they are not represented as code validated by the
  remote runs below.

## Governance

- Ruleset `24978564` (`main-governance`) is active on `~DEFAULT_BRANCH`, and
  live branch metadata reports `main` protected.
- It enforces pull requests, deletion protection, non-fast-forward protection,
  current-branch status checks, and resolved review threads.
- Required approvals remain `0`; the solo owner has PR-only bypass. This is
  explicit portfolio governance, not independent four-eyes review.
- Exactly seven required GitHub Actions checks retain integration ID `15368`:
  `Python tests`, `Container validation`, `Python SAST`, `Dependency audit`,
  `Secret scan`, `Infrastructure-as-code scan`, and
  `Container vulnerability scan`.
- The `nonprod` Environment has administrator bypass disabled, one owner
  reviewer, self-review allowed, an exact `main` deployment branch policy, six
  expected variables, and zero secrets.
- The live Actions settings page reported repository check, workflow, status,
  artifact, and log retention of 90 days, the public-repository maximum.

## Dependency Integrity

- Production lock: 14 packages, 14 hash-protected package entries, zero
  unhashed package entries; LF-normalized SHA-256
  `53a993ea8802d6f15360877eea368ad3caacb2e4cb46354ae8c1cddd01dce1a0`.
- Development lock: 23 packages, 23 hash-protected package entries, zero
  unhashed package entries; LF-normalized SHA-256
  `c9ee278d053b0ba2d5f3a77a7456ad68e45deb8eff0ca7a6007c12539205adcc`.
- `pip-tools 7.6.2` on Python 3.14 regenerated both locks exactly after newline
  normalization.
- Fresh isolated production and development installs with `--require-hashes`
  passed, and `pip check` reported no broken requirements in either.
- `pip-audit 2.10.1 --strict --require-hashes` found no known vulnerabilities
  in either lock.
- Five application tests passed in the fresh development environment with one
  upstream Starlette deprecation warning.

## Application and Container

- The Docker base image is digest pinned, dependency installation requires
  hashes, and the runtime uses non-root UID/GID `10001:10001`.
- Local Docker and Trivy were unavailable. CI run `38387312620` therefore
  supplied the required build, health, smoke, and non-root runtime evidence;
  Security run `38387318507` supplied the HIGH/CRITICAL Trivy gate. All passed.
- No image was pushed to ECR and no deployment workflow was dispatched.

## Evidence Retention

- The evidence helper has an allowlisted schema and supports success,
  confirmed automatic rollback, pre-mutation failure, and unverified failure
  without overstating the outcome.
- Helper validation passed 80 tests plus 14 focused subtests. The JSON Schema
  parsed as draft 2020-12.
- The deployment workflow creates exactly
  `deployment-evidence.json` and `deployment-evidence.sha256`, verifies the
  checksum, records the manifest and artifact digests separately, and removes
  raw AWS working data.
- `actions/upload-artifact` v7.0.2 is pinned to
  `cf430e030ddbb5b0abf93d22962f4752f3646cd9`, fails on missing files, and uses
  `retention-days: 90`.
- The workflow has no source-write authority. Durable promotion under
  `docs/evidence/deployments/` remains a manual review and normal PR action.

## Alerting

- The exact NonProd SNS topic and its policy were read successfully in account
  `119033255630`, Region `ap-southeast-1`.
- The policy contains only the intended CloudWatch and EventBridge publishers,
  exact source ARNs, exact SourceAccount, and no wildcard principal.
- Confirmed human subscriptions: `1`.
- Endpoint: **REDACTED**.
- CloudWatch alarms: `4/4` configuration matches; all were `OK`.
- EventBridge rules: `2/2` enabled, filters matched, and each had the exact SNS
  target.
- Controlled test notifications: `1` total under the Stage 10.5 approval gate.
- Owner receipt: **CONFIRMED**.
- Stage 10.6 sent no additional notification and performed no AWS mutation.

## AWS Identity Hygiene

- Management IAM Identity Center session: PASS, account `191125774822`.
- NonProd IAM Identity Center session: PASS, account `119033255630`.
- AWS access-key environment variables were unset, the static shared
  credentials file was absent, and validation isolated the CLI with an empty
  shared-credentials file.
- A legacy static local credential discovered during authentication recovery
  was verified inactive server-side. Its local material was removed.
- Repository working-tree and complete Git-history scans found no exposure.
- IAM Identity Center remains the project access mechanism. No key identifier,
  secret, token, username, or private email endpoint is recorded here.

## Terraform

`terraform fmt -check -recursive terraform` passed. After documented
initialization, all four established roots validated and returned refresh-plan
detailed exit code `0`:

| Root | Validate | Refresh plan |
| --- | --- | --- |
| `terraform/environments/management/identity` | PASS | NO CHANGES |
| `terraform/environments/nonprod/ecr` | PASS | NO CHANGES |
| `terraform/environments/nonprod/identity` | PASS | NO CHANGES |
| `terraform/environments/nonprod/runtime` | PASS | NO CHANGES |

The mission document names the Management parent directory; the established
Terraform root is its `identity` child. No state mutation, apply, saved-plan
apply, replacement, or destruction occurred. Checkov `3.3.19` reported 303
passed, 0 failed, and 20 pre-existing documented skips.

## CI / Security

All external Actions references use full 40-character commit SHAs (30 uses,
zero unpinned). Workflow YAML parsing and checksum-verified actionlint `1.7.12`
passed across all seven workflows. No `pull_request_target`, broad write
permission, publication dispatch, or deployment dispatch was present in this
validation.

Both authorized `workflow_dispatch` runs used the same validated source SHA
`73a6862dd5c442bc844bfb35442ca228f78cc17c`:

| Run | ID | Governed jobs | Result |
| --- | --- | --- | --- |
| CI | `38387312620` | Python tests; Container validation | 2/2 PASS |
| Security | `38387318507` | Python SAST; Dependency audit; Secret scan; Infrastructure-as-code scan; Container vulnerability scan | 5/5 PASS |

Total governed checks: **7/7 PASS**. The only annotations announced the planned
`ubuntu-latest` runner migration; they were informational and did not affect a
job result.

## Secret and Privacy Validation

- Gitleaks `8.30.1` scanned all 42 commits and found no leaks.
- A separate Stage 10 range scan covered all three feature commits and found no
  leaks.
- High-signal working-tree scans found zero AWS access keys, GitHub tokens,
  private keys, JWTs, or email-like identifiers.
- The repository retains no fake deployment manifest and no private alert
  endpoint. Evidence examples remain schema-only and sanitized.

## Residual Risks

- **MEDIUM — Independent approval:** the Environment gate is human-visible and
  administrator bypass is disabled, but one maintainer and allowed self-review
  do not provide four-eyes separation.
- **LOW — Security-tool dependency integrity:** Python-installed security tools
  use exact top-level versions but their larger transitive graphs are not fully
  hash locked. This remains an accepted proportional limitation.
- **LOW — Alpine artifact resolution:** `zlib>=1.3.2-r1` is a security floor,
  not a complete repository-artifact lock.
- **LOW — Legacy IAM hygiene:** the legacy server-side key remains inactive and
  its local secret is removed. Optional server-side deletion is a separate IAM
  mutation decision.
- **MEDIUM — Evidence durability:** native logs and artifacts are bounded to 90
  days and no external immutable archive exists.
- **HIGH — Rollback vulnerability timing:** vulnerability intelligence can
  change after the rollback digest check and before automatic rollback.
- **MEDIUM — Human operations:** one owner receives alerts; there is no formal
  independent on-call rotation or 24x7 SLA.
- The first live ECS promotion and live failure/rollback exercise remain
  deferred, separately approved operational evidence exercises.

## Mutation Record

- AWS mutations during Stage 10.6: **NONE**.
- Terraform state mutations during Stage 10.6: **NONE**.
- GitHub settings/governance mutations during Stage 10.6: **NONE**.
- GitHub workflow mutations: normal CI run `38387312620` and Security run
  `38387318507` were dispatched on the feature branch as explicitly authorized.
- ECR publication, ECS deployment, rollback, PR creation, and merge: **NONE**.
