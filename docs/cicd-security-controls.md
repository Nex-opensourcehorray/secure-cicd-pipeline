# CI/CD security controls

## Stage 7 boundary

Stage 7 prepares and validates trusted publication of one commit-addressed
container image to a private Amazon ECR repository. It does not deploy ECS,
networking, load balancers, DNS, or application runtime infrastructure.

The ECR/OIDC foundation apply and the first ECR image publication are separate
owner approval gates. A Git push that adds or changes the publication workflow
is also a separate approval gate.

## Publication workflow

`.github/workflows/deploy.yml` is intentionally manual (`workflow_dispatch`).
This prevents a repository push from automatically becoming an AWS mutation.
The workflow refuses to publish unless it is running for:

```text
Repository: Nex-opensourcehorray/secure-cicd-pipeline
Ref:        refs/heads/main
```

The validation job receives only `contents: read`. The publication job receives
`contents: read` and `id-token: write`; it receives no broader GitHub token
permissions.

Before requesting an OIDC token, the workflow:

1. runs the application tests;
2. builds the image from `application/`;
3. reports vulnerabilities at all severities; and
4. blocks on HIGH or CRITICAL image findings.

After an approved manual dispatch, it assumes the least-privilege AWS role,
logs in to private ECR, pushes a `${{ github.sha }}` tag, and verifies the ECR
digest. It has no ECS or Terraform step.

## Required non-secret GitHub repository variables

The owner must review and configure these repository variables separately:

```text
AWS_ACCOUNT_ID
AWS_REGION
AWS_ECR_PUBLISH_ROLE_ARN
ECR_REPOSITORY
```

They are identifiers and configuration values, not long-lived credentials. The
workflow must not use repository secrets containing `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, or `AWS_SESSION_TOKEN`.

## GitHub OIDC trust

The trust policy requires:

```text
Provider:   token.actions.githubusercontent.com
Audience:   sts.amazonaws.com
Repository: Nex-opensourcehorray/secure-cicd-pipeline
Branch:     refs/heads/main
```

For GitHub repositories using immutable subject claims, the Terraform design
expects the numeric owner and repository IDs in the `sub` value and also checks
`repository_owner_id`, `repository_id`, and `ref` separately. The real IDs must
be collected from authenticated GitHub metadata before planning or applying the
AWS foundation. Do not replace them with guessed values.

## AWS permission boundary

The publication role permits `ecr:GetAuthorizationToken` globally because AWS
does not support repository-level scoping for that action. Layer upload,
manifest publication, and digest verification actions are scoped to the single
target ECR repository ARN.

No `ecr:*`, `iam:*`, `AdministratorAccess`, or `PowerUserAccess` permission is
used.

## Image identity

The Git commit SHA is the ECR tag. The verified ECR `sha256:` digest is the
authoritative published identity. The workflow does not publish or overwrite a
`latest` tag.
