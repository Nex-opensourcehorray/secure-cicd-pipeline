# CI/CD security controls

## Stage 7 boundary

Stage 7 prepares and validates trusted publication of one commit-addressed
container image to a private Amazon ECR repository. It does not deploy ECS,
networking, load balancers, DNS, or application runtime infrastructure.

The NonProd ECR foundation, Management OIDC/IAM foundation, NonProd
cross-account repository policy, and first ECR image publication are separate
owner approval gates. A Git push that adds or changes the publication workflow
or Terraform source is also a separate approval gate.

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
AWS_MANAGEMENT_ACCOUNT_ID
AWS_NONPROD_ACCOUNT_ID
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

The Terraform trust uses GitHub's standard branch subject
`repo:Nex-opensourcehorray/secure-cicd-pipeline:ref:refs/heads/main`. It also
requires exact `repository_owner_id`, `repository_id`, and `ref` claim values.
The numeric IDs come from verified public GitHub metadata and must not be
replaced with guessed values.

## AWS account boundary

The GitHub OIDC provider and publisher identity belong to the Management
account. The private ECR repository belongs to the NonProd account. They use
independent Terraform roots and states. The ECR repository policy that will
trust the exact Management publisher-role ARN is deferred until that role
exists and its ARN can be verified; it must not trust a wildcard principal or
the Management account root.

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
