# Stage 10 Governance and Operational Hardening

> Status: **STAGE 10.0 DESIGN ONLY — NO GOVERNANCE OR LIVE-SERVICE
> MUTATION**. This document records the 2026-10-13 baseline, the remaining
> governance gaps after Stage 9, and the proposed Stage 10 roadmap. It does not
> claim that the proposed ruleset, Environment changes, evidence retention, or
> human notification path has been applied.

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

The baseline was established from the local repository, the remote branch and
commit APIs, pull-request history, check runs, and workflow-run evidence.
`git fetch --prune origin` was attempted, but the execution environment could
not connect to `github.com:443`. The authenticated GitHub connection was
therefore used to verify that the local `origin/main` reference remained
current before the Stage 10 branch was created.

| Item | Evidence | Result |
| --- | --- | --- |
| Repository | `Nex-opensourcehorray/secure-cicd-pipeline`, repository ID `1409968457`, owner ID `82328818` | VERIFIED |
| Authenticated GitHub identity | `Nex-opensourcehorray` | VERIFIED |
| Remote default branch | `main` | VERIFIED |
| `origin/main` / remote `main` | `9ee8268693b5bd63d9253fd683dfa2ff6fbf3725` | MATCH |
| Stage 9 closure | PR #20, merge commit `9ee8268693b5bd63d9253fd683dfa2ff6fbf3725` | MERGED |
| Post-merge CI | workflow `CI`, run #55, run ID `38354519286` | PASS |
| Post-merge Security | workflow `Security`, run #55, run ID `38354519235` | PASS |
| Starting worktree | clean; `git diff --check` returned no findings | PASS |
| Stage 10 branch | `stage-10-governance-hardening`, created at the verified remote `main` commit | ESTABLISHED |

The local `main` branch was behind the verified remote commit at discovery.
It was not reset or rewritten. The Stage 10 branch was created directly from
the verified `origin/main` reference.

## Current gaps

| Gap | Current evidence | Risk |
| --- | --- | --- |
| `main` governance | Live branch metadata reports `protected: false`; the live repository ruleset collection is empty. | An authorized or compromised maintainer can bypass the normal PR and check convention with a direct push. |
| Independent deployment approval | Stage 9 established one required reviewer, but the project has one maintainer and permits self-review and administrator bypass. | The Environment is a visible approval boundary, not four-eyes separation of duties. |
| Python artifact integrity | Direct packages and Python-installed tools use exact versions, but resolved artifacts and most transitive dependencies are not hash locked. | A registry-side artifact or transitive-resolution change can alter an installation without a source change. |
| Evidence retention | Deployment summaries and logs exist, but no explicit repository retention setting or durable sanitized deployment manifest is recorded. | Evidence can expire or become hard to correlate during review or investigation. |
| Human notification | Runtime alarms and focused EventBridge rules publish to a source-restricted SNS topic with zero subscriptions. | High-value runtime and security signals have no confirmed human recipient. |
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
| Classic branch protection | NONE | Live branch metadata reports unprotected. The detailed protection endpoint returned `403` to the installed integration, consistent with its lack of repository-administration read scope; the unprotected branch flag is public branch metadata. |
| Repository rulesets | NONE | Live repository ruleset list returned an empty collection. |
| Pull request required | NO | No active protection or ruleset enforces it. |
| Required status checks | NONE | Branch metadata reports enforcement `off` with no contexts/checks. |
| Direct push to `main` | TECHNICALLY POSSIBLE | Repository owner has push/admin permission and no live rule blocks updates. |
| Force-push restriction | NONE ENFORCED | No classic protection or ruleset is active. |
| Deletion restriction | NONE ENFORCED | No classic protection or ruleset is active. |
| Administrator enforcement/bypass | NOT APPLICABLE YET | There is no current rule to enforce or bypass. |

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

## Proposed `main` ruleset

A repository ruleset is preferred over a new classic branch-protection rule
because it exposes the intended policy as one named rule collection, supports
an explicit narrow bypass actor, and has rule-insight/audit semantics. The
ruleset must be applied only after a separate owner approval gate.

| Option | Current | Proposed | Security benefit | Solo-maintainer effect |
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

### Exact draft payload

This is the proposed repository ruleset request body. It is a review artifact,
not an instruction to execute during Stage 10.0.

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

Before a future apply, Stage 10.1 must re-read `main`, the ruleset collection,
the latest successful PR check runs, and the current API schema. It must also
confirm that `~DEFAULT_BRANCH` resolves to `main`, the owner can use PR-only
bypass, and a test PR produces all seven contexts.

## Environment governance

Stage 9 last verified the `nonprod` Environment as follows:

| Setting | Last verified state | Classification |
| --- | --- | --- |
| Required reviewer | `Nex-opensourcehorray` | Existing human-visible gate |
| Prevent self-review | `false` | Necessary for the current single-maintainer operating model |
| Administrator bypass | enabled | Recovery path and separation-of-duties limitation |
| Deployment branches | `main` only | Strong source boundary |
| Wait timer | `0` | Appropriate; delay alone does not add independent review |

The Stage 10 GitHub integration can read workflows, runs, branches, checks,
and rulesets but not the Environment administration endpoint. The local `gh`
credential was also invalid. Consequently, Stage 10.0 could verify the prior
successful Environment-gated run `38272473650` but could not independently
re-read the live protection settings. The table above is therefore the Stage 9
live-verified state, not a new Stage 10 live-settings claim. Stage 10.2 must
re-read it with an appropriately scoped owner session before proposing any
mutation.

### Feasible and stronger states

```text
CURRENTLY OPERATIONALLY POSSIBLE
  retain one reviewer
  retain prevent_self_review=false
  retain main-only deployment policy
  document that approval is not independent
  retain a consciously accepted administrator recovery path

TECHNICALLY DESIRABLE WHEN A REAL SECOND MAINTAINER EXISTS
  add the independent reviewer
  set prevent_self_review=true
  restrict administrator bypass after testing the recovery process
  retain main-only deployment policy
```

No second identity will be fabricated. Disabling self-review now would make
the portfolio deployment path unusable without delivering real separation of
duties.

## Dependency and artifact integrity

| Mechanism | Current pin/constraint | Classification | Assessment |
| --- | --- | --- | --- |
| Docker runtime/builder base | `python:3.14.7-alpine3.24@sha256:9e9fde...` | IMMUTABLE DIGEST | Strong identity for both stages. Periodic deliberate refresh is still required. |
| Alpine `zlib` | `zlib>=1.3.2-r1` | VERSION RANGE | Security floor is explicit, but repository resolution may change the installed package. |
| Application direct dependencies | `fastapi==0.142.2`, `uvicorn==0.53.0` | EXACT VERSION | Direct versions are fixed; transitive graph and downloaded artifacts are not fully locked. |
| Development direct dependencies | production include plus `pytest==9.1.1`, `httpx==0.28.1` | EXACT VERSION | Same transitive/artifact limitation. |
| Python security tools | `bandit==1.9.4`, `pip-audit==2.10.1`, `checkov==3.3.19` | EXACT VERSION | Tool versions are fixed; their dependency graphs and artifacts are registry resolved. |
| Trivy action | action at full SHA; pinned action default Trivy `v0.70.0` | FULL COMMIT SHA + EXACT VERSION | Action and scanner version are fixed. Vulnerability DB updates are intentionally current data, not a build dependency lock. |
| Gitleaks action | `gitleaks-action@e0c47f...` with bundled Node implementation | FULL COMMIT SHA | Scanner action implementation is immutable at that commit. |
| Other GitHub Actions | checkout, setup-python, AWS credentials, ECR login all use 40-character SHAs | FULL COMMIT SHA | Strong action source identity. Continue reviewing transitive action use on upgrades. |
| Terraform AWS provider | root constraint `~> 6.0`; lockfiles select `6.68.0` with `h1` and `zh` hashes | HASH LOCKED | Strong resolved artifact integrity across all four roots; configuration intentionally permits reviewed lock updates. |

### Stage 10.3 direction

Pilot generated hash locks for the small application runtime graph first. A
maintainable target is an input/lock split with reproducible generation and
`pip install --require-hashes`; the generated lock must include transitives and
all intentionally supported distributions. Extend the pattern to development
dependencies only after the container and CI install paths remain usable.

Hash-locking Checkov and other large security-tool dependency graphs may have
high update cost. Stage 10.3 should compare a dedicated generated tool lock
against retaining exact top-level tool versions and full-SHA Actions. It must
not add a large lock process that maintainers cannot reliably refresh. No
dependency changes are authorized by this Stage 10.0 design.

## Evidence retention

### Current evidence locations

| Evidence | Current location | Current limitation |
| --- | --- | --- |
| Source/check result | GitHub commits, check runs, workflow runs | Retention setting was not readable with the current integration. |
| Deployment inputs/outcome | GitHub workflow summaries and logs | No live deployment exists; logs/summaries are retention-bound. |
| Approval | GitHub Environment deployment review record | Tied to GitHub retention and account access. |
| AWS control-plane calls | Organization-owned CloudTrail | Exact retention/integrity configuration is externally owned and not claimed here. |
| ECS rollout detail | ECS service events/task-definition revisions | Operational data is not a durable portfolio archive. |
| Application/network evidence | CloudWatch application logs and VPC Flow Logs | Explicit 14-day retention. |
| Vulnerability/security findings | Inspector and organization-owned Security Hub | Service retention and organizational policy are external to this repository. |

### Minimal portfolio-grade model

| What | Where | Retention | Access | Integrity |
| --- | --- | --- | --- | --- |
| Full workflow execution and job logs | GitHub Actions | Set/confirm the public-repository maximum of 90 days | Authenticated repository readers | GitHub run/check identity and immutable source SHA |
| Sanitized deployment manifest plus its SHA-256 checksum | Small GitHub Actions artifact | 90 days | Authenticated repository readers | Pinned upload action, checksum, workflow run identity |
| Durable sanitized deployment index entry | Reviewed file under `docs/evidence/deployments/` added by a later human-reviewed PR, never by the deployment credentialed job | Repository lifetime | Public; therefore deliberately sanitized | Protected `main`, PR/check history, manifest checksum |
| Approval record | GitHub Environment/run metadata | 90-day operational target; retain only a sanitized approval result/timestamp in the durable entry | Authenticated readers; sanitized entry public | Correlation by run ID and source SHA |
| Authoritative AWS mutation trail | Existing organization-owned CloudTrail/Security Hub controls | Record the organization policy when owner evidence is available; do not invent a period | Authorized AWS/security operators | Organization-owned controls; not claimed until verified |
| Runtime logs | Existing CloudWatch log groups | 14 days | Authorized NonProd operators | AWS service controls and least-privilege access |

The sanitized manifest should record only:

- source commit SHA and immutable image digest;
- workflow run ID/attempt and UTC timestamp;
- approval result, without reviewer email or token data;
- vulnerability gate decision and severity counts;
- previous/new task-definition revision numbers, not full account-bearing ARNs;
- deployment result and rollback classification; and
- manifest schema version and checksum.

It must never contain credentials, AWS session output, raw OIDC tokens, secret
values, Environment/repository variables, personal notification endpoints,
private IP addresses, task IDs, local paths, full environment dumps, or
unnecessary account/resource identifiers. Raw scan reports should not be
committed merely for volume; record the decision, relevant finding IDs when an
exception exists, and a link to access-controlled evidence.

This model intentionally avoids a new S3 evidence bucket, KMS key, or paid
long-retention service. Revisit immutable external archival only if the
portfolio becomes an operational service with formal audit requirements.

## Human alerting readiness

The existing runtime path is already:

```text
CloudWatch alarms / focused EventBridge security and ECS signals
  -> source-restricted NonProd SNS topic
  -> no subscription
```

The least-complex useful model is one confirmed human-owned email destination
on the existing SNS topic, plus GitHub-native failure notifications for the
owner's CI/CD workflows. The endpoint must not be committed to this public
repository. Subscription creation, confirmation, and any Terraform/state
handling require their own AWS/settings approval gate.

| Category | High-value conditions | Proposed path | Noise control |
| --- | --- | --- | --- |
| SECURITY CRITICAL | Active HIGH/CRITICAL Inspector finding for the project ECR repository | Existing EventBridge rule -> SNS -> confirmed human destination | Repository, status, and severity filters already narrow the rule. |
| DEPLOYMENT FAILED | Deployment workflow failure or confirmed automatic rollback | GitHub Actions failure notification; later consider one sanitized SNS bridge only if native notifications prove insufficient | Notify failures/rollback, not successful promotions. One serialized deployment at a time. |
| RUNTIME DEGRADED | Unhealthy target, target 5XX, sustained CPU/memory alarm, failure-oriented ECS stop | Existing CloudWatch/EventBridge -> SNS -> confirmed human destination | Alarm evaluation windows and failure-only ECS stop codes; avoid all task state changes. |
| ACTION REQUIRED | Repeated CI/Security failure on a PR intended for merge | GitHub-native Actions notification and PR status | No notification for every successful or draft run. Owner triages at the PR. |

Stage 10.5 should define an owner, acknowledgement expectation, and a simple
test message under an explicit gate. It should verify end-to-end delivery and
document unsubscribe/rotation handling without recording the private endpoint.
Success notifications are excluded. Recovery notifications may be added only
where they help close an incident rather than double alert volume.

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
| 10.2 | Deployment approval governance | Live Environment read; documented feasible/current and independent/future states | Environment settings gate if any change is chosen |
| 10.3 | Dependency/artifact integrity | Small reproducible-lock pilot and maintenance procedure, or documented proportional deferral | Source changes only; no publication/deployment |
| 10.4 | Deployment evidence retention | Sanitized schema, 90-day GitHub retention decision, artifact/index workflow design | Repository/Actions settings gate where required |
| 10.5 | Human-owned alerting readiness | Destination ownership/runbook and separately approved end-to-end delivery test | AWS/SNS subscription and notification gate |
| 10.6 | Comprehensive governance/security validation | Full Stage 10 diff, workflow, dependency, secret, documentation, and live-settings evidence | Read-only unless separately approved |
| 10.7 | Stage 10 closure | One major PR, reviewed checks, honest residual risks and deferred live exercises | Merge-to-`main` gate |

Related changes should accumulate on `stage-10-governance-hardening`; a PR is
not required after each substage.

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

## Prepared Stage 10.1 action gate

```text
ACTION GATE — STAGE 10.1 MAIN GOVERNANCE APPLY

Operation:
Create one active repository branch ruleset named `main-governance` using the
exact reviewed payload in this document, after Stage 10.1 revalidation.

Resources affected:
GitHub repository Nex-opensourcehorray/secure-cicd-pipeline; default branch main

Environment:
GitHub repository governance (not the nonprod deployment Environment)

AWS account:
N/A

Region:
N/A

Creates:
1 repository branch ruleset

Updates:
Effective governance of main: PR required, seven GitHub Actions checks required,
review threads resolved, branch up to date, force push blocked, deletion blocked

Destroys:
0

IAM changes:
NONE

Network changes:
NONE

Expected external effects:
Ordinary direct pushes, force pushes, and deletion of main are blocked. PRs must
produce all seven current job checks. The exact owner has PR-only emergency
bypass; no direct-push bypass is proposed.

Destructive changes:
NO

Rollback:
Capture the created ruleset ID and response. After separate owner approval,
disable or delete that exact ruleset; do not weaken unrelated controls.

Evidence reviewed:
Remote main SHA and PR #20 merge; CI/Security run #55; seven live check runs and
GitHub Actions integration ID; empty ruleset collection; unprotected main branch;
20-PR convention; workflow PR triggers; Stage 9 closure and threat evidence.
```

The gate is prepared only. No approval is inferred and no settings mutation
occurred in Stage 10.0.
