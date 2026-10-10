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

## Stage 7.7.3 repository-policy anti-lockout compatibility repair

The approved Stage 7.7.2 retry was the third `SetRepositoryPolicy` failure.
Like the first two attempts, Amazon ECR rejected it with HTTP 400
`InvalidParameterException` and `Invalid repository policy provided`. The
three rejected forms were:

- exact Management publisher-role Principal with the exact repository ARN;
- exact Management publisher-role Principal with `Resource = "*"`; and
- Management account Principal with the exact publisher-role `PrincipalArn`
  condition and `Resource = "*"`.

No attempt published an image, created a live repository policy or managed
repository-policy state, or damaged the repository or lifecycle policy. The
CloudTrail request IDs for the three attempts are, from newest to oldest:

```text
c41661fc-5ba2-4063-ac0d-d9ce491e26b9
22d9fcf7-12b0-4604-8eac-59a352a0d893
cd8a487d-eda8-4c88-9280-b65e2a2865dd
```

CloudTrail records all three calls in NonProd account `119033255630`, Region
`ap-southeast-1`, from the authenticated NonProd IAM Identity Center
administrator session. The live repository policy and its Terraform state
address remain absent. The repository, lifecycle policy, and zero-image state
remain intact. Security impact and live resource damage are both `NONE`.

AWS documents an anti-lockout safeguard on `SetRepositoryPolicy`: a policy
that would prevent a future policy update must be submitted with `force`.
The installed HashiCorp AWS provider's `aws_ecr_repository_policy` resource
does not expose that API argument. This is therefore a compatibility
hypothesis based on the repeated service validation failures, not a claim of a
validated live fix.

To preserve an administration path without bypassing the safeguard, the
prepared policy adds one same-account statement for
`arn:aws:iam::119033255630:root` with only these repository-policy operations:

```text
ecr:GetRepositoryPolicy
ecr:SetRepositoryPolicy
ecr:DeleteRepositoryPolicy
```

The statement uses `Resource = "*"` because the policy is attached to the one
`secure-cicd-demo` repository. It grants no image, repository deletion,
lifecycle-policy, registry, IAM, or other ECR operations. An AWS account
Principal delegates authority to identities in that account; their applicable
identity permissions and other policy controls still govern access. The two
Management publisher statements, exact publisher-role condition, six publish
and verification actions, and Management identity policy remain unchanged.
The owning-account Principal is preferred over the generated IAM Identity
Center role ARN because permission-set roles can be recreated with a different
suffix; coupling recovery to that implementation detail would reduce
operational resilience. Checkov's permissions-management finding is documented
as a narrow exception for these three same-account anti-lockout actions only.
