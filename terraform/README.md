# Stage 7 Terraform account boundaries

Stage 7 uses separate Terraform roots and state boundaries for the approved
two-account architecture:

- `environments/nonprod/ecr` owns only the private ECR repository and its
  lifecycle policy in the NonProd account.
- `environments/management/identity` owns only the GitHub OIDC provider,
  publisher role, least-privilege managed policy, and attachment in the
  Management account.

Neither root configures ECS, networking, a remote backend, or application
runtime resources. Each root must be initialized and planned with its dedicated
AWS profile. The Management root accepts the reviewed NonProd repository ARN as
an explicit input; it does not read another root's state.

## Deployment dependency

The required order is:

1. use the deployed and verified NonProd ECR foundation;
2. pass the reviewed ECR repository ARN to and apply the Management identity
   foundation after its separate approval gate;
3. add and apply the NonProd ECR cross-account repository policy after the
   Management publisher-role ARN has been independently verified; and
4. publish the first commit-addressed image after its separate approval gate.

The Stage 7.5 NonProd ECR foundation has been deployed and verified. The
Management OIDC/IAM foundation, cross-account ECR repository policy, and first
ECR image publication have not occurred. The NonProd and Management roots remain
separate Terraform and state boundaries.

This repository was created after GitHub's July 15, 2026 immutable-subject
cutover. Its default GitHub OIDC subject therefore includes the immutable owner
and repository IDs alongside their names:

```text
repo:Nex-opensourcehorray@82328818/secure-cicd-pipeline@1409968457:ref:refs/heads/main
```

The IDs prevent repository or owner name reuse from reproducing the trusted
subject. The trust policy also checks the audience, owner ID, repository ID, and
exact `main` branch ref separately.

The cross-account repository policy remains design-only and is intentionally
absent from both active roots. Its future principal must be the exact Management
publisher-role ARN, never a wildcard or the entire Management account root. Its
allowed actions are limited to:

```text
ecr:BatchCheckLayerAvailability
ecr:CompleteLayerUpload
ecr:DescribeImages
ecr:InitiateLayerUpload
ecr:PutImage
ecr:UploadLayerPart
```

The publisher identity policy grants the same repository-scoped actions to the
exact NonProd repository ARN. It grants `ecr:GetAuthorizationToken` on `*`
because that API does not support repository-level resource scoping.
