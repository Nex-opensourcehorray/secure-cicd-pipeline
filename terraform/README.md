# Stage 7 Terraform account boundaries

Stage 7 uses three Terraform roots and separate state boundaries for its
two-account role-chaining architecture:

- `environments/nonprod/ecr` owns only the private ECR repository and lifecycle
  policy in the NonProd account.
- `environments/nonprod/identity` owns only the dedicated ECR publisher role,
  managed policy, and role-policy attachment in the NonProd account.
- `environments/management/identity` owns only the GitHub OIDC provider,
  existing GitHub broker role, managed policy, and attachment in the Management
  account.

No root configures ECS, networking, a remote backend, or application runtime
resources. Each root must be initialized and planned with its dedicated AWS
profile. The roots exchange reviewed ARNs through explicit inputs; none reads
another root's state.

## Active role-chaining architecture

The target publication path is:

```text
GitHub Actions
    -> GitHub OIDC / AssumeRoleWithWebIdentity
    -> Management broker role
    -> sts:AssumeRole
    -> NonProd publisher role
    -> same-account IAM authorization
    -> secure-cicd-demo
```

This design uses no static AWS keys. GitHub OIDC remains restricted by the
immutable owner and repository IDs and the exact `main` branch. After migration,
the existing Management role cannot publish to ECR directly and can assume only
the exact NonProd publisher role. The NonProd role can publish to exactly one
repository. No ECR repository resource policy is required.

## Deployment dependency

The required future migration order is:

1. publish and validate this source;
2. create the NonProd publisher role, managed policy, and attachment;
3. verify that the NonProd role exists;
4. convert the existing Management role policy from direct ECR publication to
   `sts:AssumeRole` for only the NonProd publisher role;
5. configure the required GitHub repository variables under a separate gate;
6. run the manual read-only role-chain trust check under a separate gate;
7. verify the ECR image inventory remains zero; and
8. authorize the first commit-addressed image publication separately.

The Stage 7.5 NonProd ECR foundation and Stage 7.6 Management OIDC/IAM
foundation are deployed and verified. The NonProd publisher identity and
Management broker-policy conversion are source design only until separately
approved and applied. The first ECR image publication has not occurred.

This repository was created after GitHub's July 15, 2026 immutable-subject
cutover. Its default GitHub OIDC subject therefore includes the immutable owner
and repository IDs alongside their names:

```text
repo:Nex-opensourcehorray@82328818/secure-cicd-pipeline@1409968457:ref:refs/heads/main
```

The IDs prevent repository or owner name reuse from reproducing the trusted
subject. The trust policy also checks the audience, owner ID, repository ID, and
exact `main` branch ref separately.

The dedicated NonProd publisher role's same-account identity policy limits
repository operations to:

```text
ecr:BatchCheckLayerAvailability
ecr:CompleteLayerUpload
ecr:DescribeImages
ecr:InitiateLayerUpload
ecr:PutImage
ecr:UploadLayerPart
```

Those actions are scoped to
`arn:aws:ecr:ap-southeast-1:119033255630:repository/secure-cicd-demo`. The role
also grants `ecr:GetAuthorizationToken` on `*` because that API does not support
repository-level resource scoping. Its trust policy accepts only
`arn:aws:iam::191125774822:role/secure-cicd-pipeline-nonprod-github-ecr-publisher`
for `sts:AssumeRole`; it does not trust the account root, GitHub OIDC provider,
or any wildcard principal.

## Historical Stage 7.7.1 repository-policy semantics repair

The first Stage 7.7 apply was rejected by the ECR `SetRepositoryPolicy` API
with `InvalidParameterException`. AWS created no live repository policy, and
Terraform created no managed repository-policy state. The failure was an
implementation issue involving ECR's service-specific repository resource
policy semantics; it had no security impact.

That repair changed the repository policy to `Resource = "*"`, consistent with
AWS ECR repository-policy examples. Because the policy was attached directly to
`secure-cicd-demo`, that value does not grant access to every ECR repository.
At that repair, the exact publisher-role Principal and six allowed actions
remained unchanged, and the Management identity policy continued to scope those
repository actions to the exact NonProd ECR repository ARN.

Checkov's generic wildcard-resource checks do not model this ECR-specific
attachment scope, so the two applicable findings are explicitly documented as
service-semantic exceptions on this policy document. Wildcard Principal and
wildcard Action checks remain enabled.

## Historical Stage 7.7.2 cross-account Principal compatibility repair

The approved Stage 7.7.1 retry was also rejected by the ECR
`SetRepositoryPolicy` API with `InvalidParameterException`. The second failure
created no live repository policy, no managed repository-policy Terraform
state, no image, and no change to the existing ECR repository or lifecycle
policy. This remains ECR cross-account policy compatibility troubleshooting;
security impact and live resource damage are both `NONE`.

Stage 7.7.2 aligned the repository policy with AWS's canonical cross-account
pattern by using `arn:aws:iam::191125774822:root` as the Principal while an
exact `ArnEquals` condition requires `aws:PrincipalArn` to equal the durable
Management publisher-role ARN. The account Principal alone is not sufficient.
The five documented upload actions and the `ecr:DescribeImages` verification
action are in separate statements. Both statements retain `Resource = "*"`,
the exact-role condition, and the repository-specific attachment scope. The
Management identity policy remains unchanged and scoped to the exact NonProd
repository ARN.

## Historical Stage 7.7.3 repository-policy anti-lockout compatibility repair

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

To preserve an administration path without bypassing the safeguard, that
prepared policy added one same-account statement for
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

## Historical Stage 7.7.4 acceptance-isolation diagnostic

The approved fourth and final repository-policy attempt was also rejected by
Amazon ECR with HTTP 400 `InvalidParameterException` and `Invalid repository
policy provided`. Its CloudTrail request ID was:

```text
81098ebf-ea99-4b4d-9d02-af467ba3a487
```

Across all four attempts, the request reached the correct NonProd account and
Region with an authenticated caller, but Amazon ECR accepted none of the policy
forms. No attempt created a live repository policy, managed repository-policy
Terraform state, or image. The ECR repository and lifecycle policy remained
unchanged. The underlying service-acceptance cause therefore remains
unidentified; another speculative live retry is not justified.

## Stage 7.7.5 role-chaining fallback

The direct cross-account ECR repository-policy architecture is historical and
has been intentionally abandoned. Its Terraform resource, policy-document data
source, dedicated inputs, and Checkov exceptions have been removed from active
source. The prior sections remain as an audit trail of the four failed attempts;
they do not describe the active design.

The replacement source keeps the deployed Management OIDC provider and role
resource identities unchanged. Only the Management role's attached permission
policy is designed to change, from direct ECR actions to `sts:AssumeRole` on the
exact NonProd publisher role. A separate NonProd identity root owns that role,
its same-account ECR policy, and its attachment. This avoids further
`SetRepositoryPolicy` retries while preserving account and Terraform-state
separation.

The manual `trust-check.yml` workflow is deliberately separate from image
publication. It performs the two role assumptions, verifies the active NonProd
account, and calls only read-only `ecr:DescribeImages`. Creating or publishing
that workflow does not authorize running it or publishing an image.
