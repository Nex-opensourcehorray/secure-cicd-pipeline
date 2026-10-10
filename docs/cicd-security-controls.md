# CI/CD security controls

## Stage 7 boundary

Stage 7 validates trusted publication of one commit-addressed container image
to the private `secure-cicd-demo` Amazon ECR repository. It does not deploy ECS,
networking, load balancers, DNS, or application runtime infrastructure.

Stage 7 uses separate owner approval gates for:

1. the NonProd ECR foundation;
2. the Management GitHub OIDC foundation;
3. the NonProd publisher IAM foundation;
4. the Management broker-policy conversion;
5. the GitHub role-chain repository variables;
6. the read-only role-chain trust check; and
7. the first trusted ECR image publication.

Publishing source, changing GitHub settings, running the trust check, and
publishing an image are distinct operations. Approval for one does not
authorize another.

The active identity path is:

```text
GitHub Actions
    -> GitHub OIDC / AssumeRoleWithWebIdentity
    -> Management broker role
    -> sts:AssumeRole
    -> NonProd ECR publisher role
    -> same-account ECR authorization
    -> secure-cicd-demo
```

## Publication workflow

`.github/workflows/deploy.yml` is intentionally manual (`workflow_dispatch`).
It refuses to publish unless it is running for the exact repository and `main`
branch:

```text
Repository: Nex-opensourcehorray/secure-cicd-pipeline
Ref:        refs/heads/main
```

The validation job receives only `contents: read`. The publication job receives
`contents: read` and `id-token: write`; it receives no broader GitHub token
permissions. The workflow uses no static AWS credentials.

Before publication, the workflow:

1. runs the application tests;
2. builds the image from `application/`;
3. reports vulnerabilities at all severities;
4. blocks on HIGH or CRITICAL findings;
5. obtains short-lived Management credentials through GitHub OIDC;
6. uses the Management broker to assume the dedicated NonProd publisher role;
7. verifies that the active AWS account is `119033255630`;
8. logs in to private NonProd ECR;
9. pushes a Git-commit-SHA tag; and
10. retrieves and reports the immutable ECR digest.

The workflow performs no Terraform apply and no ECS deployment.

## Required non-secret GitHub repository variables

The owner must review and configure exactly these repository variables under a
separate approval gate:

| Variable | Purpose |
| --- | --- |
| `AWS_REGION` | Selects the `ap-southeast-1` workload Region. |
| `AWS_MANAGEMENT_ACCOUNT_ID` | Constrains the first credential step to Management account `191125774822`. |
| `AWS_NONPROD_ACCOUNT_ID` | Constrains and verifies the second credential step against NonProd account `119033255630`. |
| `AWS_MANAGEMENT_BROKER_ROLE_ARN` | Identifies the Management role trusted by GitHub OIDC. |
| `AWS_NONPROD_ECR_PUBLISH_ROLE_ARN` | Identifies the dedicated NonProd role assumed by the broker. |
| `ECR_REPOSITORY` | Identifies the `secure-cicd-demo` repository. |

These values are infrastructure metadata, not credentials. They belong in
GitHub repository variables rather than secrets. The workflow must not use or
store `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or `AWS_SESSION_TOKEN`.

## GitHub OIDC trust

The Management role trust requires all of these exact values:

```text
Provider:      token.actions.githubusercontent.com
Audience:      sts.amazonaws.com
Owner ID:      82328818
Repository ID: 1409968457
Ref:           refs/heads/main
Subject:       repo:Nex-opensourcehorray@82328818/secure-cicd-pipeline@1409968457:ref:refs/heads/main
```

This repository was created after GitHub's immutable-subject cutover, so the
numeric owner and repository IDs are part of its default subject. The IDs and
the separate claim checks prevent owner or repository name reuse from
reproducing the trusted identity.

## AWS account boundary

Management account `191125774822` contains:

- the GitHub OIDC provider; and
- the existing GitHub broker role.

NonProd account `119033255630` contains:

- the private `secure-cicd-demo` ECR repository; and
- the dedicated ECR publisher role.

The cross-account transition is `sts:AssumeRole` from the exact Management
broker to the exact NonProd publisher. There is no active ECR repository
resource policy. The role-chain design intentionally avoids further
`SetRepositoryPolicy` attempts, while the accounts and Terraform states remain
separate.

## AWS permission boundary

### Management broker policy

The Management broker permits only:

```text
Action:   sts:AssumeRole
Resource: arn:aws:iam::119033255630:role/secure-cicd-pipeline-nonprod-ecr-publisher
```

It has no direct ECR publication permissions.

### NonProd publisher policy

The NonProd publisher permits `ecr:GetAuthorizationToken` on `*` because AWS
does not support repository-level resource scoping for that action. It permits
exactly these repository operations:

```text
ecr:BatchCheckLayerAvailability
ecr:CompleteLayerUpload
ecr:DescribeImages
ecr:InitiateLayerUpload
ecr:PutImage
ecr:UploadLayerPart
```

Those six actions are scoped to exactly:

```text
arn:aws:ecr:ap-southeast-1:119033255630:repository/secure-cicd-demo
```

Neither identity policy grants `ecr:*`, delete operations, IAM write, ECS,
networking, or KMS administration.

## Read-only role-chain trust check

`.github/workflows/trust-check.yml` proves the identity chain before the first
image publication:

```text
GitHub OIDC
    -> Management broker
    -> NonProd publisher
    -> STS account verification
    -> read-only ECR image inventory
```

The workflow is `workflow_dispatch` only. It calls `ecr:DescribeImages`, does
not publish an image, and requires a separate execution approval gate.

## Historical repository-policy diagnostic

Before role chaining was selected, four authenticated cross-account ECR
`SetRepositoryPolicy` attempts failed with `InvalidParameterException`. No
repository policy was successfully created, no managed repository-policy
Terraform state was created, and no image was published. The repository and
lifecycle controls remained intact. Diagnostic review did not establish a
confirmed service-acceptance root cause, so the direct repository-policy
architecture was abandoned rather than retried speculatively. This history is
not the active design.

## Image identity

The Git commit SHA is the ECR tag. The verified ECR `sha256:` digest is the
authoritative immutable image identity. The workflow does not publish or
overwrite a `latest` tag.
