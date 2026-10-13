# Stage 10 Governance and Operational Hardening

> Status: **STAGE 10.0–10.6 COMPLETE; STAGE 10.7 FINAL PR PENDING**. Stage 10.5
> completed one confirmed human subscription and one owner-confirmed controlled
> delivery test. Stage 10.6 revalidated the live governance, AWS alert path,
> dependency and evidence controls, four Terraform roots, and all seven remote
> CI/Security jobs without publishing an image or deploying ECS.

## Purpose

Stage 9 closed the continuous-deployment source and control implementation.
The deployment identity, approval boundary, source and artifact provenance,
digest-pinned promotion, least-privilege AWS roles, runtime validation, and
rollback classification are complete. The first live ECS promotion and live
rollback exercise remain optional, separately gated evidence exercises; they
are not incomplete Stage 9 source work and are not prerequisites for Stage 10.

Stage 10 addresses governance and operational controls that sit around the
technical deployment path:

- enforce the existing pull-request and validation convention on `main`;
- distinguish a visible approval gate from independent separation of duties;
- improve dependency artifact integrity proportionately;
- retain a durable, sanitized deployment evidence record; and
- connect high-value failure/security signals to a human owner without
  creating alert fatigue.

## Trusted baseline

The Stage 10.6 baseline was established from a successful remote fetch, the
local repository, authenticated GitHub administration reads, check runs, and
workflow-run evidence. The continuing Stage 10 branch was clean, matched its
remote, and remained zero commits behind `origin/main`.

| Item | Evidence | Result |
| --- | --- | --- |
| Repository | `Nex-opensourcehorray/secure-cicd-pipeline`, repository ID `1409968457`, owner ID `82328818` | VERIFIED |
| Authenticated GitHub identity | `Nex-opensourcehorray` | VERIFIED |
| Remote default branch | `main` | VERIFIED |
| `origin/main` / remote `main` | `6c35fad916f531863bc82e39d821126f7f0feca9` | MATCH |
| Stage 10.2 closure | PR #22, merge commit `6c35fad916f531863bc82e39d821126f7f0feca9` | MERGED |
| Stage 10.4 feature baseline | `c3dc7395eb507ae573e90f1ffa25daabe1927875`; remote CI #61 and Security #61 | PASS |
| Stage 10.5 feature source | `73a6862dd5c442bc844bfb35442ca228f78cc17c` | PASS — HUMAN ALERT DELIVERY VERIFIED |
| Starting worktree | clean; `git diff --check` returned no findings | PASS |
| Stage 10.6 validation baseline | `stage-10-hardening-completion`; zero behind / three ahead of `origin/main` | VERIFIED |

No reset or history rewrite was used. Ruleset `24978564` was also re-read and
remained active, while branch metadata reported `main` as protected.

## Governance status and remaining gaps

| Gap | Current evidence | Risk |
| --- | --- | --- |
| `main` governance | Ruleset `24978564` is active and live branch metadata reports `protected: true`. | CONTROL ACTIVE — PR flow, seven checks, freshness, review-thread resolution, deletion protection, and non-fast-forward protection are enforced. |
| Independent deployment approval | One owner reviewer remains and self-review is allowed; administrator bypass is disabled. | The Environment is a mandatory human-visible gate, but one maintainer cannot provide four-eyes separation of duties. |
| Python artifact integrity | Application production and development graphs are exact-version and SHA-256 hash locked. Python-installed security tools remain exact-version only by documented proportional decision. | Application installs fail closed on altered or unapproved artifacts; the larger security-tool graphs retain registry-resolution risk. |
| Evidence retention | Repository Actions retention is verified at 90 days. The deployment workflow now creates a canonical sanitized manifest and checksum artifact, with manual PR-only promotion to a durable repository directory. | Operational evidence remains intentionally bounded; durable records require human review and a real deployment. |
| Human notification | Terraform defines one source-restricted SNS topic, four focused alarms, and two focused EventBridge routes. One manual email subscription is confirmed and the owner confirmed receipt of one controlled test. | The endpoint remains private and outside Terraform; the solo owner is not an independent or 24x7 response function. |
| Live promotion/rollback | No distinct scan-clean candidate was available at Stage 9 closure. | Operational evidence is deferred, but source/control completeness is not affected. |

## Threat and governance model

Stage 9 primarily constrained machine authority: what source may request a
deployment, which identities may be assumed, which digest may be selected,
and which exact ECS mutation may occur. Stage 10 constrains the people and
evidence around that authority.

```text
Stage 9 technical controls
  trusted source -> validated digest -> narrow identity -> exact mutation

Stage 10 governance controls
  enforced PR -> required checks -> explicit approval -> durable evidence
       -> actionable human notification -> reviewed exception/recovery path
```

The remaining risks cannot be solved by granting broader AWS access. The
principal governance threats are bypass of review/check convention, approval
by the same person who initiated the deployment, evidence expiry, registry
resolution without artifact hashes, and signals that reach an integration
topic but not a human owner.

## Current `main` governance

| Control | Current state | Evidence boundary |
| --- | --- | --- |
| Classic branch protection | NONE | The classic-protection endpoint remains separate from the active repository ruleset; branch metadata now reports `protected: true` because the ruleset governs `main`. |
| Repository rulesets | `main-governance` / ID `24978564` / active | Exact-ID read-back and four effective rules on `main`. |
| Pull request required | YES | Active pull-request rule; normal required approvals remain `0`. |
| Required status checks | SEVEN | All approved contexts are pinned to GitHub Actions integration ID `15368`; strict freshness is enabled. |
| Direct push to `main` | BLOCKED | The owner bypass applies only while completing a pull request, not to direct pushes. |
| Force-push restriction | ENFORCED | Active `non_fast_forward` rule. |
| Deletion restriction | ENFORCED | Active `deletion` rule. |
| Administrator enforcement/bypass | OWNER PR-ONLY | Exact user ID `82328818`; no direct-push or always-bypass mode. |

### Pull-request convention

All 20 closed pull requests visible at discovery were merged into `main` from
feature branches. The latest three merge commits each have two parents, so
merge commits are the demonstrated recent convention. PR #20 was merged by
`Nex-opensourcehorray` and contains one feature-branch commit.

The connected repository API did not expose definitive repository-level
enablement flags for squash and rebase merging. Stage 10 therefore does not
claim that those two methods are currently enabled or disabled. The proposed
ruleset preserves all repository-enabled merge methods and does not require a
linear history, which preserves the demonstrated merge-commit workflow.

## Required status-check identities

GitHub Actions creates a check run for each job; the top-level workflow titles
`CI` and `Security` are not the check contexts emitted for branch protection.
The post-merge commit has exactly these seven successful GitHub Actions check
runs, all produced by GitHub Actions integration ID `15368`:

| Workflow | Required check context | Runs on PRs to `main` |
| --- | --- | ---: |
| CI | `Python tests` | YES |
| CI | `Container validation` | YES |
| Security | `Python SAST` | YES |
| Security | `Dependency audit` | YES |
| Security | `Secret scan` | YES |
| Security | `Infrastructure-as-code scan` | YES |
| Security | `Container vulnerability scan` | YES |

Both workflows use an unconditional `pull_request` trigger for `main` with no
path filters. Requiring every job-level context therefore does not create a
known missing-check deadlock. Pinning each context to integration ID `15368`
also prevents an unrelated integration from satisfying a same-named check.
Renaming, removing, path-filtering, or conditionally skipping one of these jobs
must be coordinated with the ruleset before merge.

## Applied `main` ruleset

A repository ruleset was selected over a new classic branch-protection rule
because it exposes the policy as one named rule collection, supports an
explicit narrow bypass actor, and has rule-insight/audit semantics. The exact
payload below was owner-approved, applied, and verified in Stage 10.1.

| Option | Stage 10.0 baseline | Applied | Security benefit | Solo-maintainer effect |
| --- | --- | --- | --- | --- |
| Target | None | Default branch (`~DEFAULT_BRANCH`, currently `main`) | Follows the repository's governed default branch. | No effect on feature branches. |
| Enforcement | None | `active` | Makes governance preventive rather than advisory. | Merges must satisfy or explicitly bypass the rule. |
| Require pull request | No | Yes | Stops ordinary direct pushes to `main`. | Owner works through PRs, matching existing convention. |
| Required approvals | 0 | 0 | Preserves PR evidence without pretending one person provides separation of duties. | Avoids an unusable self-approval requirement. |
| Dismiss stale approvals | N/A | No | No value while zero approvals are required. | No effect. Revisit if a second maintainer joins. |
| Require last-push approval | N/A | No | Cannot provide independent review in the current one-person model. | Avoids deadlock. Revisit with a second maintainer. |
| Require code-owner review | N/A | No | A sole owner approving their own work is not independent review. | Avoids ceremony without a security gain. |
| Resolve review threads | No | Yes | Prevents acknowledged review findings from being left unresolved. | Owner must resolve open conversations before merge. |
| Required checks | None | All seven job contexts above, GitHub Actions integration `15368` | Enforces the complete existing CI and Security suites. | A broken or renamed check blocks merge until repaired or explicitly bypassed. |
| Strict/up-to-date checks | No | Yes | Tests the PR against the current protected base. | PRs may need an update after another merge. |
| Block force pushes | No rule | Yes (`non_fast_forward`) | Protects reviewed history and evidence. | History repair requires an explicit ruleset change or bypass decision. |
| Block deletion | No rule | Yes (`deletion`) | Prevents accidental/default-branch deletion. | Default-branch recovery may require ruleset administration. |
| Linear history | No rule | No | No material gain that outweighs changing the demonstrated merge convention. | Existing merge commits remain available. |
| Allowed merge methods | Unknown repository flags | Preserve `merge`, `squash`, and `rebase`; repository settings still decide availability | Avoids imposing an unrelated history policy. | Keeps owner flexibility. |
| Bypass | No rule | Exact owner user ID `82328818`, PR-only bypass | Retains an audited recovery route without permitting bypass by direct push. | Owner can recover from check/ruleset failure only through a PR. |

### Applied request payload

This is the approved repository ruleset request body submitted in Stage 10.1.

```json
{
  "name": "main-governance",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    {
      "actor_id": 82328818,
      "actor_type": "User",
      "bypass_mode": "pull_request"
    }
  ],
  "conditions": {
    "ref_name": {
      "include": ["~DEFAULT_BRANCH"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "allowed_merge_methods": ["merge", "squash", "rebase"],
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "do_not_enforce_on_create": false,
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "Python tests", "integration_id": 15368 },
          { "context": "Container validation", "integration_id": 15368 },
          { "context": "Python SAST", "integration_id": 15368 },
          { "context": "Dependency audit", "integration_id": 15368 },
          { "context": "Secret scan", "integration_id": 15368 },
          { "context": "Infrastructure-as-code scan", "integration_id": 15368 },
          { "context": "Container vulnerability scan", "integration_id": 15368 }
        ]
      }
    }
  ]
}
```

Stage 10.1 completed with ruleset ID `24978564`, name `main-governance`, target
`branch`, and enforcement `active`. Exact-ID and effective-rule reads confirm
that `~DEFAULT_BRANCH` governs `main`, all seven checks are required, and the
owner bypass is PR-only. GitHub normalized two optional response fields:

```text
required_reviewers: []
require_extra_approval_for_unattributed_changes: true
```

The first is empty. The second is a server default with no current practical
approval effect while `required_approving_review_count` is `0`. Neither field
changes the approved Stage 10.1 policy. A future normal Stage 10 pull request
will provide functional evidence without destructive ruleset testing.

## Environment governance

After the owner completed the separately gated GitHub UI change, Stage 10.2
re-read the live `nonprod` Environment with the authenticated owner session.
The Environment ID is `24058843649`. The read-back verified the intended
single-field hardening and no drift in the remaining Stage 9 configuration.

| Setting | Live state | Classification |
| --- | --- | --- |
| Required reviewer | `Nex-opensourcehorray` / user ID `82328818` | One human-visible gate |
| Prevent self-review | `false` | Required for the current solo-maintainer workflow |
| Administrator bypass | disabled (`can_admins_bypass: false`) | The configured reviewer gate cannot be skipped through the administrator bypass option |
| Wait timer | `0` (no wait-timer rule returned) | No security benefit from delay alone |
| Deployment branch mode | custom policies enabled; protected-branch mode disabled | Exact allowlist mode |
| Deployment branch policies | one: `main` / type `branch` | Tags, feature branches, and wildcard branches are not authorized |
| Environment variables | six; exact names and values match Stage 9 | No drift |
| Environment secrets | zero | No unexpected secret metadata |

The six variables remain:

```text
AWS_MANAGEMENT_DEPLOY_ROLE_ARN
AWS_NONPROD_ECS_DEPLOY_ROLE_ARN
ECS_CLUSTER_NAME
ECS_SERVICE_NAME
ECS_CONTAINER_NAME
ECS_EXECUTION_ROLE_ARN
```

### Approval classification

```text
HUMAN-VISIBLE APPROVAL: YES
SELF-REVIEW POSSIBLE:    YES
INDEPENDENT APPROVAL:   NO
FOUR-EYES CONTROL:      NO
ADMIN BYPASS:           DISABLED
```

The repository collaborator read returned only `Nex-opensourcehorray`, with
administrator permission. No real second eligible reviewer is currently
available, so `prevent_self_review=true` is not feasible without risking an
approval deadlock. This is an accepted organizational limitation, not a
technical defect. No alternate identity will be fabricated.

### Administrator-bypass closure

Self-review and administrator bypass remain distinct controls. Keeping
`prevent_self_review=false` lets the sole maintainer complete the configured
review path. Disabling administrator bypass removes the separate path that
could release a waiting deployment without that review. The owner made that
single UI change under the Stage 10.2 gate; authenticated read-back then
reported `can_admins_bypass: false`.

```text
OWNER-COMPLETED AND VERIFIED
  administrator bypass: enabled -> disabled

UNCHANGED
  reviewer: Nex-opensourcehorray / 82328818
  prevent_self_review: false
  wait timer: 0
  deployment branch: main / branch
  variables: 6
  secrets: 0
```

This closes the avoidable administrator bypass without claiming independent
review. A real second trusted maintainer is still required before self-review
can be disabled safely and the control can be classified as four-eyes.

## Dependency and artifact integrity

| Mechanism | Current pin/constraint | Classification | Assessment |
| --- | --- | --- | --- |
| Docker runtime/builder base | `python:3.14.7-alpine3.24@sha256:9e9fde...` | IMMUTABLE DIGEST | Strong identity for both stages. Periodic deliberate refresh is still required. |
| Alpine `zlib` | `zlib>=1.3.2-r1` | VERSION FLOOR / OS-REPOSITORY-MANAGED | The patched floor remains explicit while Alpine can deliver later security revisions. Exact APK pinning would make historical rebuilds brittle as repository contents age. |
| Application production graph | `requirements.in` intent compiled to `requirements.txt` | EXACT VERSION + SHA-256 HASH | All 14 installable requirements, including 12 transitives, are exact and hashed. Production installation requires hashes. |
| Application development graph | `requirements-dev.in` intent compiled to `requirements-dev.txt` | EXACT VERSION + SHA-256 HASH | The complete 23-package development graph is independently installable; all requirements are exact and hashed. CI and publication validation require hashes. |
| Python security tools | `bandit==1.9.4`, `pip-audit==2.10.1`, `checkov==3.3.19` | EXACT VERSION / HASH LOCK DEFERRED | Dry-run resolution produced 8, 28, and 97 total packages respectively. Separate hash locks would add disproportionate review/update burden to three independently updated tools. |
| Trivy action | action at full SHA; pinned action default Trivy `v0.70.0` | FULL COMMIT SHA + EXACT VERSION | Action and scanner version are fixed. Vulnerability DB updates are intentionally current data, not a build dependency lock. |
| Gitleaks action | `gitleaks-action@e0c47f...` with bundled Node implementation | FULL COMMIT SHA | Scanner action implementation is immutable at that commit. |
| Other GitHub Actions | checkout, setup-python, AWS credentials, ECR login all use 40-character SHAs | FULL COMMIT SHA | Strong action source identity. Continue reviewing transitive action use on upgrades. |
| Terraform AWS provider | root constraint `~> 6.0`; lockfiles select `6.68.0` with `h1` and `zh` hashes | HASH LOCKED | Strong resolved artifact integrity across all four roots; configuration intentionally permits reviewed lock updates. |

### Stage 10.3 implemented model

The human-edited inputs retain the existing top-level versions:

```text
DIRECT PRODUCTION (2)
  fastapi==0.142.2
  uvicorn==0.53.0

DIRECT DEVELOPMENT (4 total; 2 development-specific)
  production inputs
  pytest==9.1.1
  httpx==0.28.1
```

`pip-compile` resolves and hashes every installable package into two standalone
locks. The production graph contains 14 packages: 2 direct and 12 transitive.
The development graph contains 23 packages: 4 direct and 19 transitive. There
are 14/14 hashed exact production requirements and 23/23 hashed exact
development requirements; neither lock has an unhashed installable
requirement. Review found no duplicate or conflicting versions. `colorama` is
the only notable platform-specific resolution: it is selected for Windows by
Pytest and is a harmless extra when the complete lock is installed on Linux.

The compiler environment used Python `3.14.7`, pip `26.2.1`, and
`pip-tools==7.6.2`. The generated headers record Python 3.14 and the commands:

```text
python -m piptools compile --generate-hashes --strip-extras \
  --no-emit-index-url --no-emit-trusted-host \
  --output-file requirements.txt requirements.in

python -m piptools compile --generate-hashes --strip-extras \
  --no-emit-index-url --no-emit-trusted-host \
  --output-file requirements-dev.txt requirements-dev.in
```

Clean production and development installs require `--require-hashes`. The
Dockerfile, CI test job, and publication validation job enforce that mode.
Tampered-hash and missing-hash negative tests both failed closed. Regeneration
from a second clean compiler environment produced byte-identical locks.

### Lock refresh procedure

Do not hand-edit a generated lock or its hashes.

1. Edit `application/requirements.in` or
   `application/requirements-dev.in`, retaining deliberate exact top-level
   versions.
2. Create a clean disposable Python 3.14 environment.
3. Install the approved compiler version, currently `pip-tools==7.6.2`, and
   record the Python and pip versions used.
4. From `application/`, regenerate both locks with the commands above.
5. Review the full graph and lock diff for unexpected, duplicate,
   platform-specific, or conflicting packages and for unintended version
   changes.
6. In separate clean Python 3.14 environments, install each lock with
   `python -m pip install --disable-pip-version-check --require-hashes -r ...`.
7. Run `python -m pip check` in both environments.
8. Run the application test suite from the clean development environment.
9. Run the pinned `pip-audit==2.10.1` against both lock files without
   suppressing findings.
10. Build the application image, run its health/non-root checks, and scan it
    for HIGH and CRITICAL vulnerabilities wherever Docker and Trivy are
    available.
11. Regenerate once more from a clean equivalent compiler environment, verify
    byte identity, and review the lock change through the normal PR/check
    process.

### Proportional residual decisions

Bandit, pip-audit, and Checkov retain exact top-level versions and normal
trusted HTTPS package resolution. Their measured graphs contain 7, 27, and 96
transitive packages respectively, compared with 12 production and 19
development transitives for the application. Maintaining three additional
large locks would increase CI complexity and update burden substantially,
especially for Checkov, while these tools do not enter the runtime artifact.
Full tool hash locking is therefore explicitly deferred, not overlooked.

The Alpine line remains `zlib>=1.3.2-r1`. This is intentionally classified as
`VERSION FLOOR / OS-REPOSITORY-MANAGED`: it guarantees the patched minimum and
permits later repository security updates. Exact APK version pinning is not
adopted because Alpine repository lifecycle can remove historical revisions
and make rebuilds brittle. The floor was not weakened.

## Evidence retention

### Live repository setting

The documented repository Actions artifact-and-log retention endpoint was
read with authenticated administration access on 2026-10-13.

```text
repository visibility: public
repository retention: 90 days
public-repository maximum: 90 days
desired Stage 10 value: 90 days
mutation required: NO
classification: NO-OP — REPOSITORY RETENTION ALREADY AT DESIRED MAXIMUM
```

The value controls bounded GitHub operational evidence. It does not promise
that external AWS records share that retention and does not make old or
expired evidence reappear.

### Three evidence layers

| Layer | Evidence | Retention and governance |
| --- | --- | --- |
| 1 — GitHub native | Workflow run, seven check results where applicable, job logs, summary, and Environment deployment approval record | Repository-configured 90 days; operational rather than permanent evidence |
| 2 — Workflow artifact | `deployment-evidence.json` and `deployment-evidence.sha256` only | Uploaded for 90 days as `nonprod-deployment-evidence-<run_id>` by official `actions/upload-artifact` v7.0.2 pinned to commit `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| 3 — Durable portfolio record | A reviewed manifest under `docs/evidence/deployments/` | Repository lifetime until governed removal; manual feature branch and PR only |

The deployment workflow retains `contents: read`, `actions: read` only where
source provenance needs it, and `id-token: write` only in the deployment job.
It receives no `contents: write`, `actions: write`, package, issue, or pull
request write permission. It cannot commit evidence, push a branch, or call a
repository file-write API. Durable evidence therefore remains independent of
the deployment credential path.

### Manifest and checksum

Schema version `1` correlates the GitHub run and workflow-source SHA with the
candidate source SHA, digest and vulnerability counts, safe rollback baseline,
revision integers, terminal outcome, and validated runtime booleans. Approved
outcomes are:

```text
SUCCESS
AUTOMATIC_ROLLBACK_CONFIRMED
FAIL_CLOSED_UNVERIFIED
PRE_MUTATION_FAILURE
```

Unavailable optional values are omitted. A pre-mutation failure does not
invent an attempted revision. Confirmed rollback explicitly records
`succeeded: false` and `runtime_recovery_verified: true`; it is never presented
as a successful promotion. Successful and rollback evidence require zero
candidate/rollback HIGH and CRITICAL findings and verified stable, healthy,
private runtime state with zero ALB ingress rules.

The standard-library generator accepts only named allowlisted arguments,
rejects unknown keys and malformed SHAs/digests/counts/revisions/outcomes,
does not read the process environment wholesale, and writes sorted,
newline-terminated UTF-8 JSON. It scans allowed values for credential, JWT,
private-address, authorization, and local-path patterns. The output directory
must contain exactly the manifest and checksum—never raw AWS responses,
temporary directories, AWS errors, task IDs, ENI IDs, or private addresses.

`deployment-evidence.sha256` uses:

```text
<sha256>  deployment-evidence.json
```

The helper independently verifies the checksum and canonical serialization
before upload. The checksum is an integrity and correlation aid, not a digital
signature. GitHub's separate artifact digest is recorded in the workflow
summary when upload succeeds.

### Terminal behavior and cleanup

Evidence generation, upload, summary, and cleanup are the only finalization
steps allowed to run after an earlier deployment-step failure. They execute
after outcome classification and before deletion of raw ephemeral working
data. Upload paths name the two evidence files explicitly and use
`if-no-files-found: error`; the raw deployment directory is never uploaded.

Evidence generation or upload failure makes the workflow fail. It cannot
trigger `RegisterTaskDefinition`, rerun `UpdateService`, issue a rollback, or
otherwise mutate AWS. A failed deployment stays failed even when its evidence
artifact uploads successfully.

### Durable promotion

No live deployment record is created in Stage 10.4. After a meaningful future
deployment, a maintainer downloads the artifact, verifies its checksum and
schema, reviews sanitization and run correlation, then copies only the JSON
manifest under the documented `YYYY-MM-DD-run-<github_run_id>.json` convention.
The record enters through a normal feature branch, required-check PR, review,
and merge. Stage 9.3-R1 remains preflight validation—not retrospective
deployment evidence.

This model intentionally avoids a new S3 evidence bucket, KMS key, or paid
long-retention service. CloudTrail and Security Hub retention remain
organization-owned and are not claimed without verification. Existing
CloudWatch application and VPC Flow Log retention remains the validated
14-day value.

## Human alerting readiness

### Authentication recovery and live validation

The initial Stage 10.5 read was blocked by an expired AWS session. IAM Identity
Center access was recovered for Management account `191125774822` and NonProd
account `119033255630`; Stage 10.6 revalidated both identities while isolating
the CLI from static shared credentials. A legacy local static credential was
discovered during recovery, its server-side key was verified inactive, no
repository or Git-history exposure was found, and the local credential material
was removed. IAM Identity Center remains the project access mechanism.

Authenticated reads in Region `ap-southeast-1` then verified the exact SNS
topic, source-restricted policy, one confirmed subscription, all four expected
alarms in `OK`, both EventBridge rules `ENABLED` with the exact SNS target, and
a refresh-enabled runtime Terraform plan with no changes. The private endpoint
was never written to repository evidence.

### Source-verified signal path

The existing Terraform path is:

```text
CloudWatch alarms / focused EventBridge security and ECS signals
  -> source-restricted NonProd SNS topic
  -> manually governed human subscription seam
```

Source review found no duplicate topic and no `aws_sns_topic_subscription`
resource. Terraform owns the topic, topic policy, four alarms, two rules, and
their SNS targets. The policy grants `sns:Publish` only to
`cloudwatch.amazonaws.com` for the four exact alarm ARNs and to
`events.amazonaws.com` for the two exact rule ARNs, with
`aws:SourceAccount = 119033255630` in both statements. Source contains no
anonymous or wildcard principal.

| Signal | Source configuration | Stage 10.5 result |
| --- | --- | --- |
| ALB unhealthy targets | `UnHealthyHostCount`, maximum >= 1, 60-second period, 2/2 datapoints | LIVE VERIFIED; `OK` |
| Target HTTP 5XX | `HTTPCode_Target_5XX_Count`, sum >= 1, one five-minute period | LIVE VERIFIED; `OK` |
| ECS CPU | average `CPUUtilization` >= 80%, two five-minute periods | LIVE VERIFIED; `OK` |
| ECS memory | average `MemoryUtilization` >= 80%, two five-minute periods | LIVE VERIFIED; `OK` |
| ECS task failure | exact cluster/service, `STOPPED`, only `EssentialContainerExited` and `TaskFailedToStart` | LIVE VERIFIED; rule enabled and exact SNS target |
| Inspector finding | ACTIVE HIGH/CRITICAL `AWS_ECR_CONTAINER_IMAGE` findings for `secure-cicd-demo` | LIVE VERIFIED; rule enabled and exact SNS target |

The topic's service-default encryption posture remains an accepted NonProd
design decision: alert payloads are operational metadata and a dedicated CMK
is outside this portfolio scope. This does not permit secrets or sensitive
application data in alert messages.

### Human integration and ownership seam

The implemented integration is exactly one confirmed human-owned email
destination for the Portfolio / NonProd service owner, currently
`Nex-opensourcehorray`. The endpoint is supplied only at execution time and
must not enter source, Terraform state, GitHub variables/secrets, workflow
evidence, or public reports.

The human subscription remains a manual operational integration. Managing it
with Terraform would retain private endpoint data in state without improving
the security of this solo-portfolio workflow. Neither the deployment workflow
nor its AWS roles need `sns:Subscribe` or `sns:Publish`; a separately
authenticated owner/operator performs the approved lifecycle on the exact
topic.

Subscription and delivery have three distinct states:

```text
SUBSCRIPTION REQUESTED
  -> SUBSCRIPTION CONFIRMED
  -> END-TO-END DELIVERY VERIFIED
```

An API request is not confirmation. Confirmation requires a real subscription
ARN from `ListSubscriptionsByTopic`; delivery additionally requires the owner
to confirm receipt of exactly one controlled test message. The approved design
does not trigger a CloudWatch alarm, vulnerability, task crash, 5XX response,
or resource exhaustion merely to test delivery.

### Alert categories and response expectations

| Category | High-value conditions | Proposed path | Noise control |
| --- | --- | --- | --- |
| SECURITY CRITICAL | Active HIGH/CRITICAL Inspector finding for the project ECR repository | Existing EventBridge rule -> SNS -> confirmed human destination | Repository, status, and severity filters already narrow the rule. |
| DEPLOYMENT FAILED | Deployment workflow failure or confirmed automatic rollback | GitHub Actions failure notification; later consider one sanitized SNS bridge only if native notifications prove insufficient | Notify failures/rollback, not successful promotions. One serialized deployment at a time. |
| RUNTIME DEGRADED | Unhealthy target, target 5XX, sustained CPU/memory alarm, failure-oriented ECS stop | Existing CloudWatch/EventBridge -> SNS -> confirmed human destination | Alarm evaluation windows and failure-only ECS stop codes; avoid all task state changes. |
| ACTION REQUIRED | Repeated CI/Security failure on a PR intended for merge | GitHub-native Actions notification and PR status | No notification for every successful or draft run. Owner triages at the PR. |

These are portfolio expectations rather than a production SLA: SECURITY
CRITICAL is acknowledged in the same working session or as soon as practical;
DEPLOYMENT FAILED in the same deployment session; RUNTIME DEGRADED within a
reasonable NonProd response window; and ACTION REQUIRED before PR merge.

No human alert is required for successful CI/Security/deployment, normal ECS
task transitions, normal CPU/memory, or LOW/MEDIUM Inspector findings. GitHub
remains the native path for repository and deployment workflow failures; no
duplicate CI-to-SNS bridge is introduced.

The complete triage, evidence, acknowledgement, rotation, data-handling, and
controlled test procedures are in the
[NonProd alert response runbook](runbooks/nonprod-alert-response.md).

### Stage 10.5 controlled mutation outcome

After the required read-only checks passed, the owner separately approved one
manual subscription request and one direct safe SNS test publication. Final
sanitized facts are:

```text
confirmed human subscription: 1
endpoint: REDACTED
controlled test notifications: 1
owner receipt: CONFIRMED
```

Stage 10.6 sent no additional message and made no AWS change. Any subscription
rotation, replacement, unsubscribe, or later test requires a new explicit
approval gate.

## Optional deployment evidence

Stage 10 does not depend on a first live ECS promotion, failure injection, or
automatic rollback exercise. If no distinct, trusted-main, published candidate
exists with zero active HIGH/CRITICAL findings, the correct result remains:

```text
LIVE DEPLOYMENT REMAINS DEFERRED
```

No vulnerability gate, task health check, network control, IAM boundary, or
rollback invariant may be weakened to manufacture evidence.

## Risk prioritization

Scores use 1 (low) to 5 (high). For complexity, break risk, and recurring cost,
a higher score is a greater burden.

| Work | Security benefit | Portfolio value | Operational realism | Complexity | Break risk | Recurring cost | Priority conclusion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `main` ruleset | 5 | 5 | 5 | 2 | 3 | 1 | **Priority 1**; closes the clearest governance gap. |
| Evidence retention | 4 | 5 | 5 | 2 | 1 | 1 | **Priority 2**; use small sanitized records and existing platforms. |
| Human alert destination | 5 | 4 | 5 | 2 | 1 | 1 | **Priority 2**; existing SNS path makes this high value and low complexity. |
| Python hash locking | 4 | 4 | 4 | 4 | 3 | 1 | **Priority 3**; pilot narrowly to control maintenance burden. |
| Independent Environment reviewer | 5 | 5 | 5 | 1 technical / 5 organizational | 4 | 1 | **Conditional**; not honestly achievable with one maintainer. |
| Live promotion/rollback exercises | 3 | 5 | 5 | 5 | 5 | 2 | **Optional**; useful evidence but not a governance prerequisite. |

The evidence supports the expected ranking, with human alerting elevated beside
evidence retention because the topic and focused signals already exist.

## Stage 10 roadmap

| Stage | Objective | Exit evidence | Mutation boundary |
| --- | --- | --- | --- |
| 10.0 | Governance architecture and gap plan | This reviewed design, trusted baseline, exact ruleset draft | Documentation and feature-branch publication only |
| 10.1 | `main` protection/ruleset readiness and apply | Revalidated checks/schema, owner-approved ruleset, test PR proving enforcement and recovery | Repository settings gate |
| 10.2 | Deployment approval governance | Owner-disabled administrator bypass with authenticated read-back; self-review remains allowed and no independent reviewer is claimed | COMPLETE |
| 10.3 | Dependency/artifact integrity | PASS — reproducible application production/development hash locks and maintenance procedure; security-tool locks proportionately deferred | Source changes only; no publication/deployment |
| 10.4 | Deployment evidence retention | PASS — live 90-day repository setting, canonical sanitized manifest/checksum artifact, and manual PR-only durable record | Source changes only; retention setting already at target |
| 10.5 | Human-owned alerting readiness | PASS — one confirmed human subscription, one controlled test, owner receipt confirmed; endpoint redacted | Completed under the separate AWS/SNS subscription and notification gate |
| 10.6 | Comprehensive governance/security validation | PASS — full Stage 10 diff, workflow, dependency, secret, documentation, live-settings, four drift-free plans, and 7/7 remote checks | Read-only validation plus authorized CI/Security dispatch and documentation publication |
| 10.7 | Stage 10 closure | CLOSURE REVIEW COMPLETE — one major PR, governed checks, honest residual risks, and deferred live exercises remain at the final gate | PR-creation and merge-to-`main` gates |

Related completion changes should accumulate on `stage-10-hardening-completion`; a PR is
not required after each substage.

The concise [Stage 10 closure evidence](stage-10-closure-evidence.md) maps the
complete feature delta to its controls and records the final residual risks,
deferred evidence, and explicit non-claims.

## Approval boundaries

This design grants no permission to perform any of the following:

- create, update, disable, or delete repository rulesets/branch protection;
- change GitHub Environment reviewers, self-review, bypass, branch policy, or
  wait timer;
- create or change GitHub variables, secrets, Actions retention, or other
  repository settings;
- create or confirm an SNS subscription or send a real test notification;
- run Terraform apply or mutate Terraform state;
- mutate AWS IAM, ECS, ECR, networking, monitoring, logging, backup, or KMS;
- publish an image or deploy/roll back ECS;
- merge to `main`, force push, rewrite history, or perform destructive work.

## Stage 10.1 applied action record

The separately approved Stage 10.1 operation created exactly one repository
ruleset:

```text
ID:          24978564
Name:        main-governance
Target:      branch
Enforcement: active
main:        protected / governed
```

Read-back verified the approved PR rule, seven required checks, strict branch
freshness, review-thread resolution, deletion protection, non-fast-forward
protection, and owner PR-only bypass. No direct-push bypass exists. Any future
update, disablement, or deletion must target ruleset ID `24978564` and requires
separate owner approval.
