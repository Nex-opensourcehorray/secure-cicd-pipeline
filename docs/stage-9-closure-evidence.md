# Stage 9 Continuous Deployment Closure Evidence

## Executive Summary

Stage 9 implements a controlled continuous-deployment capability for promoting
an already-published, immutable ECR image digest into one private NonProd ECS
Fargate service. It adds a dedicated GitHub Environment approval boundary,
Environment-bound OIDC trust, separate cross-account deployment identities,
least-privilege ECS permissions, trusted-source and image provenance checks,
time-of-deploy vulnerability enforcement, allowlisted task-definition revision
automation, runtime verification, and fail-closed rollback classification.

Stage 9 closes as **source and control implementation complete; live promotion
deferred**. No Stage 9 ECS deployment or live failed-deployment exercise was
performed. The historical distinct candidate was rejected because of an active
HIGH zlib finding, and the policy was not weakened to manufacture deployment
evidence.

## Trusted Baseline

- PR [#18](https://github.com/Nex-opensourcehorray/secure-cicd-pipeline/pull/18)
  merged the Stage 9.4-9.6 implementation.
- PR [#19](https://github.com/Nex-opensourcehorray/secure-cicd-pipeline/pull/19)
  merged the Stage 9.7 security-review correction.
- Final pre-closure `main` baseline:
  `03238ce917d236165e4385aeefd70cc33db59568`.
- [Merged-main CI](https://github.com/Nex-opensourcehorray/secure-cicd-pipeline/actions/runs/38351894631): PASS.
- [Merged-main Security](https://github.com/Nex-opensourcehorray/secure-cicd-pipeline/actions/runs/38351894561): PASS.

## Architecture

Publication and deployment remain separate trust paths:

```text
trusted main -> CI/Security -> manual publication -> scan gate
  -> Management publication broker -> NonProd ECR publisher
  -> commit-SHA tag -> immutable digest

trusted published source SHA -> provenance checks -> nonprod approval
  -> GitHub OIDC -> Management deployment broker -> NonProd ECS deployer
  -> time-of-deploy scan -> allowlisted task revision
  -> exact service pointer update -> runtime/rollback verification
```

The deployment workflow never rebuilds or pushes the image. It resolves the
source commit's ECR tag to one digest and registers the digest-addressed image
URI. Terraform continues to own the infrastructure and baseline task
definition; CD owns only newly registered revisions and the ECS service's
selected task-definition pointer. Terraform ignores only that pointer.

## Stage Outcomes

| Stage | Objective | Source implementation | Validation | Live mutation | Final status |
| --- | --- | ---: | ---: | ---: | --- |
| 9.0 | CD architecture and threat model | YES | YES | N/A | PASS |
| 9.1 | Deployment IAM foundation | YES | YES | Completed under prior gates | PASS |
| 9.2 | Deployment workflow foundation | YES | YES | No deployment | PASS |
| 9.3 | GitHub Environment approval boundary | YES/configured | YES | GitHub settings only | PASS |
| 9.3-R1 | Environment and preflight test | N/A | YES | Read-only workflow | PASS |
| 9.4 | Digest/task-revision automation | YES | Fixture/read-only validation | NO | PASS |
| 9.5 | First ECS deployment | Capability YES | Readiness evaluated | NO | DEFERRED - NO DISTINCT SCAN-CLEAN TRUSTED PUBLISHED CANDIDATE |
| 9.6 | Circuit-breaker rollback controls | YES | 57 deterministic tests | No live failure | PASS - LIVE TEST DEFERRED |
| 9.7 | Supply-chain and least privilege | YES | YES | NONE | PASS WITH WARNINGS |
| 9.8 | Stage closure | YES | Final regression | NONE | CLOSED AFTER FINAL MERGE |

The Stage 9.8 row describes the intended post-merge classification. Before the
closure PR is merged, Stage 9 remains at the final closure merge gate.

## Security Controls

- The `nonprod` GitHub Environment requires a reviewer and allows only the
  exact `main` branch policy. Tags and feature branches are not authorized.
- The Management broker trust requires `sts.amazonaws.com`, the immutable
  Environment subject, numeric owner ID `82328818`, numeric repository ID
  `1409968457`, and `refs/heads/main`.
- Publication and deployment use separate Management brokers and separate
  NonProd roles.
- Every GitHub Action dependency is pinned to a full commit SHA.
- Publication and deployment block active HIGH and CRITICAL findings.
- Deployment provenance requires trusted-main ancestry plus successful CI,
  Security, and publication workflow evidence.
- The ECS image is addressed by `repository@sha256:...`, not a mutable tag.
- The Management deployment broker may only assume the exact NonProd deployer.
- The NonProd deployer is limited to required metadata reads, one task family,
  one service, exact cluster conditions where supported, and `PassRole` for
  the exact ECS execution role to `ecs-tasks.amazonaws.com`.
- Task-definition validation requires Fargate, fixed CPU/memory, no task role,
  non-root execution, read-only root filesystem, no privilege, all Linux
  capabilities dropped, expected logging, expected health check, and private
  networking.
- Deployment concurrency is serialized with cancellation disabled.
- ECS automatic rollback is observed without issuing a second service update.

## Validation Evidence

The closure baseline has the following evidence:

- GitHub CI: application tests, Docker build, readiness, API smoke tests,
  Docker health, and non-root runtime validation passed.
- GitHub Security: Bandit, pip-audit, Gitleaks, Checkov, and Trivy passed.
- Stage 9 deployment helper: 57 of 57 deterministic tests passed.
- Actionlint and immutable action-pin review passed.
- Terraform formatting passed and all four environment roots validated.
- Stage 9.1 OIDC claim and deployment role-chain checks passed through
  separately approved read-only workflows.
- Stage 9.3-R1 run `38272473650` validated the Environment approval path and
  preflight without deploying.
- Stage 9.7 reviewed action provenance, workflow permissions and triggers,
  IAM actions and conditions, resource wildcards, secrets, Terraform provider
  locks, artifact provenance, vulnerability gates, and rollback controls.

Validation proves the source and control behavior described here. It does not
claim that the first mutating deployment or a failed-deployment rollback was
executed.

## Publication and Deployment Authority

| Capability | Publication path | Deployment path |
| --- | ---: | ---: |
| Build image | YES | NO |
| Push ECR | YES | NO |
| Read image metadata | YES | YES |
| Register task definition | NO | YES, exact family/pattern |
| Update ECS service | NO | YES, exact service only |
| Pass execution role | NO | YES, exact role only |
| IAM administration | NO | NO |
| Network mutation | NO | NO |
| Terraform apply/state | NO | NO |

## Deployment and Rollback Evidence

```text
Deployment capability implemented: YES
First live ECS promotion executed: NO
Reason: no distinct scan-clean trusted published candidate; intentionally deferred

Automatic rollback verification source implemented: YES
Fixture validation: PASS
Live failed deployment: NO
Live automatic rollback observed: NO
```

The historical candidate with `CVE-2026-85091` in zlib was blocked at HIGH.
That rejection is positive evidence that the deployment vulnerability policy
fails closed.

## Accepted Limitations

1. `main` has no branch protection or repository ruleset. An authorized
   maintainer can push directly; the other trust-chain controls do not replace
   enforced pre-merge review.
2. The Environment is single-maintainer. Self-review is permitted and
   administrator bypass is available, so approval is not separation of duties.
3. Python dependencies and Python-installed security tools are version-pinned
   but not cryptographically artifact-hash pinned.
4. A vulnerability can become known after the rollback digest is checked and
   before a later automatic rollback. Continuous scanning and alerting reduce,
   but cannot eliminate, that timing window.
5. The NonProd service uses one task for cost-conscious validation, limiting
   resilience during a failed rollout.

## Deferred Evidence

The first mutating ECS promotion was not executed because no distinct,
scan-clean, trusted published candidate was available at closure. The project
did not publish or deploy an artificial candidate merely to turn this item
green.

A live failed deployment and automatic rollback were also not executed. A
future exercise requires a trusted scan-clean test image, a safe failure mode,
and explicit approval for task-definition registration and service update.

## Future Hardening

- Require pull requests and successful CI/Security checks through a branch
  protection rule or repository ruleset.
- Add a second independent Environment reviewer, prevent self-review, and
  reconsider administrator bypass.
- Add cryptographic dependency locking where it can be maintained reliably.
- Establish explicit deployment-evidence retention and a human-owned alert
  destination.
- Perform a separately approved first promotion and periodic rollback exercise
  using trusted scan-clean artifacts.

## Closure Classification

After the final closure PR is merged:

```text
STAGE 9 - CLOSED
CD architecture: COMPLETE
Deployment IAM: COMPLETE
Environment approval boundary: COMPLETE
Deployment source implementation: COMPLETE
Supply-chain validation: COMPLETE
Rollback-control source validation: COMPLETE
First live ECS promotion: DEFERRED
Live rollback exercise: DEFERRED
```
