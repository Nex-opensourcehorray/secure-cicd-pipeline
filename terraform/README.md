# Stage 7 Terraform account boundaries

Stage 7 uses separate Terraform roots and state boundaries for the approved
two-account architecture:

- `environments/nonprod/ecr` owns only the private ECR repository, lifecycle
  policy, and cross-account publisher policy in the NonProd account.
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
2. use the deployed and verified Management identity foundation, scoped to the
   reviewed NonProd ECR repository ARN;
3. apply the prepared NonProd ECR cross-account repository policy after its
   separate approval gate; and
4. publish the first commit-addressed image after its separate approval gate.

The Stage 7.5 NonProd ECR foundation and Stage 7.6 Management OIDC/IAM
foundation have been deployed and verified. The Stage 7.7 cross-account ECR
repository-policy source is prepared but has not been applied. The first ECR
image publication has not occurred. The NonProd and Management roots remain
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

Cross-account publication requires both the Management role's identity policy
and the NonProd ECR repository resource policy. The prepared repository policy
uses the Management account principal together with an exact `ArnEquals`
`aws:PrincipalArn` condition for the verified publisher role. Both checks must
match, so the effective trusted identity remains that one role. Its allowed
actions are limited to:

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

## Stage 7.7.1 repository-policy semantics repair

The first Stage 7.7 apply was rejected by the ECR `SetRepositoryPolicy` API
with `InvalidParameterException`. AWS created no live repository policy, and
Terraform created no managed repository-policy state. The failure was an
implementation issue involving ECR's service-specific repository resource
policy semantics; it had no security impact.

The repository policy now uses `Resource = "*"`, consistent with AWS ECR
repository-policy examples. Because the policy is attached directly to
`secure-cicd-demo`, that value does not grant access to every ECR repository.
At that repair, the exact publisher-role Principal and six allowed actions
remained unchanged, and the Management identity policy continued to scope those
repository actions to the exact NonProd ECR repository ARN.

Checkov's generic wildcard-resource checks do not model this ECR-specific
attachment scope, so the two applicable findings are explicitly documented as
service-semantic exceptions on this policy document. Wildcard Principal and
wildcard Action checks remain enabled.

## Stage 7.7.2 cross-account Principal compatibility repair

The approved Stage 7.7.1 retry was also rejected by the ECR
`SetRepositoryPolicy` API with `InvalidParameterException`. The second failure
created no live repository policy, no managed repository-policy Terraform
state, no image, and no change to the existing ECR repository or lifecycle
policy. This remains ECR cross-account policy compatibility troubleshooting;
security impact and live resource damage are both `NONE`.

Stage 7.7.2 aligns the repository policy with AWS's canonical cross-account
pattern by using `arn:aws:iam::191125774822:root` as the Principal while an
exact `ArnEquals` condition requires `aws:PrincipalArn` to equal the durable
Management publisher-role ARN. The account Principal alone is not sufficient.
The five documented upload actions and the `ecr:DescribeImages` verification
action are in separate statements. Both statements retain `Resource = "*"`,
the exact-role condition, and the repository-specific attachment scope. The
Management identity policy remains unchanged and scoped to the exact NonProd
repository ARN.
