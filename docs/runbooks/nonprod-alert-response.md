# NonProd Alert Response Runbook

## Scope

This runbook covers actionable security, deployment, runtime, and repository
governance signals for the `secure-cicd-pipeline` NonProd portfolio. It is an
owner-operated response guide, not a production incident-management SLA.

The AWS notification path is deliberately small:

```text
CloudWatch alarms / focused EventBridge rules
  -> secure-cicd-pipeline-nonprod-runtime-alerts
  -> target: one confirmed human-owned email subscription
```

GitHub Actions and pull-request failures remain GitHub-native. Successful and
routine events do not generate human alerts.

## Alert Owner

The responsible role is the **Portfolio / NonProd service owner**. The current
repository owner is `Nex-opensourcehorray`.

The repository records responsibility, not a private notification endpoint.
The owner should keep appropriate GitHub Actions and pull-request notifications
enabled through personal account preferences; those settings are not collected
or managed by this repository.

## Alert Routing Ownership

Terraform owns:

- the SNS topic and source-restricted topic policy;
- four CloudWatch alarms and their SNS actions;
- the failure-oriented ECS and Inspector EventBridge rules; and
- both EventBridge SNS targets.

The human email subscription is a manually managed operational integration.
It is not an `aws_sns_topic_subscription` resource because Terraform state
would retain the private endpoint. The GitHub deployment role receives no
`sns:Subscribe` or `sns:Publish` authority.

An operator performing the separately approved subscription and delivery test
needs only the relevant `sns:Subscribe`, `sns:ListSubscriptionsByTopic`,
`sns:GetTopicAttributes`, and controlled `sns:Publish` permissions on the exact
NonProd topic. Administrative breadth must not be added to deployment IAM.

## SECURITY CRITICAL

Trigger: an active HIGH or CRITICAL Amazon Inspector finding for an
`AWS_ECR_CONTAINER_IMAGE` in `secure-cicd-demo`.

Portfolio response expectation: acknowledge in the same working session or as
soon as practical, and investigate before publication or deployment.

1. Identify the affected immutable ECR digest and associated source commit.
2. Compare it with the candidate, currently serving, and rollback digests.
3. Block promotion when the candidate is affected.
4. Treat a finding on the serving or rollback digest as a security-remediation
   decision, not merely a pipeline failure.
5. Preserve Inspector, Security Hub, ECR, and workflow evidence.
6. Do not suppress or weaken the HIGH/CRITICAL vulnerability gate to restore
   deployability.

## DEPLOYMENT FAILED

Trigger: the future deployment workflow fails or confirms automatic rollback.
The primary notification path is GitHub Actions, not a duplicate SNS success or
failure bridge.

Portfolio response expectation: acknowledge during the same deployment
session and verify rollback/runtime state before any retry.

1. Inspect the trusted workflow run and its protected Environment approval.
2. Download and verify the deployment-evidence artifact and manifest checksum.
3. Classify the result as `PRE_MUTATION_FAILURE`,
   `FAIL_CLOSED_UNVERIFIED`, or `AUTOMATIC_ROLLBACK_CONFIRMED`.
4. Confirm the actual serving task-definition revision and image digest.
5. Do not rerun deployment until the runtime state is understood.
6. Do not issue a manual rollback or deregister a revision without a separate
   explicit authorization.

## RUNTIME DEGRADED

Triggers:

- one or more unhealthy ALB targets for two consecutive minutes;
- at least one target HTTP 5XX response in five minutes;
- average ECS CPU at or above 80 percent for ten minutes;
- average ECS memory at or above 80 percent for ten minutes; or
- an ECS task stopped with `EssentialContainerExited` or
  `TaskFailedToStart` for the exact NonProd service.

Portfolio response expectation: acknowledge within a reasonable NonProd
response window and inspect the signal before changing infrastructure.

Check target health, target 5XX metrics, ECS desired/running/pending counts,
CPU and memory, the stopped-task reason, application logs, and recent
deployment evidence. Do not restart blindly, redeploy reflexively, or weaken
network/security-group controls as a first response.

## ACTION REQUIRED

Trigger: repeated CI or Security failures on a pull request intended for merge.
The primary path is GitHub-native required-check and workflow visibility.

Portfolio response expectation: acknowledge and resolve the failure before PR
merge.

Inspect the failed required check, remediate on the feature branch, and allow
the checks to rerun. Do not weaken or bypass the `main-governance` ruleset for
routine development. PR-only bypass is reserved for genuine recovery use.

## Initial Triage

For an AWS runtime or security notification:

1. Identify the alert category and confirm the repository and `nonprod`
   environment.
2. Inspect the originating CloudWatch alarm, EventBridge event, Inspector
   finding, Security Hub finding, or ECS service evidence.
3. Correlate the signal with recent workflow and deployment evidence.
4. Make no immediate infrastructure mutation solely because a notification
   arrived.
5. Classify the condition as security, deployment, application/runtime, or an
   expected/false condition.
6. Preserve relevant run IDs, immutable digests, revision numbers, timestamps,
   and sanitized findings.
7. Follow the repository security and incident boundaries before remediation.

## Evidence Sources

Use the minimum sources needed for the alert:

- GitHub workflow/check results, summaries, Environment approval, and the
  deployment evidence artifact;
- CloudWatch alarm history, metrics, and application logs;
- EventBridge rule and target metadata;
- ECS service events and task-definition revision/digest mapping;
- ALB target health;
- Inspector, ECR scan, and organization-owned Security Hub evidence; and
- CloudTrail evidence where authorized and available.

Do not copy raw AWS event bodies, personal endpoints, task IDs, private IPs,
tokens, credentials, or unnecessary account/resource identifiers into the
public repository.

## Acknowledgement Expectations

These are portfolio response expectations, not a formal 24x7 SLA:

| Category | Acknowledgement | Required decision |
| --- | --- | --- |
| SECURITY CRITICAL | Same working session / as soon as practical | Investigate before publication or deployment |
| DEPLOYMENT FAILED | Same deployment session | Verify serving and rollback state before retry |
| RUNTIME DEGRADED | Reasonable NonProd response window | Inspect alarm, ECS/ALB state, and logs |
| ACTION REQUIRED | Before PR merge | Resolve required-check failures |

## Escalation / Stop Conditions

Stop instead of proceeding with subscription or test activity when:

- AWS authentication is absent, expired, or identifies the wrong account;
- any monitored alarm is unexpectedly `ALARM`;
- the SNS topic policy contains anonymous/wildcard or unexpected publish
  authority;
- an unknown or duplicate subscription exists;
- the CloudWatch/EventBridge routing differs from reviewed Terraform;
- a rule is disabled or broader than the exact service/repository filters;
- the operation would require broader IAM, a topic/policy change, or a real
  runtime/security failure; or
- an actual incident signal needs investigation.

Treat authentication failure separately from infrastructure drift. Never use a
synthetic message while an unexplained real alarm is active.

## Subscription Lifecycle

The desired solo-portfolio state is exactly one confirmed human-owned email
subscription:

```text
SUBSCRIPTION REQUESTED
  -> PendingConfirmation
  -> owner opens the AWS confirmation message
  -> SUBSCRIPTION CONFIRMED
  -> controlled test publication
  -> END-TO-END DELIVERY VERIFIED
```

A successful `Subscribe` API response is not delivery readiness. Confirmation
requires `ListSubscriptionsByTopic` to return a real subscription ARN rather
than `PendingConfirmation`. End-to-end success additionally requires the owner
to confirm receipt of the controlled test message.

Do not repeat a pending subscription request or poll aggressively. If multiple
or unknown subscriptions appear, stop, identify their purpose, and do not
delete them automatically.

## Subscription Rotation

When the human destination changes:

1. Under explicit approval, request and confirm the new destination.
2. Send one controlled message and verify human receipt.
3. Under a separate owner decision, remove the exact old subscription.
4. Read back the topic and verify only intended subscriptions remain.
5. Keep both endpoint values out of source, Terraform state, variables,
   evidence artifacts, and reports.

Unsubscribe stale endpoints promptly; do not delete the SNS topic.

## Test Procedure

The test requires the explicit **Stage 10.5 Human Alert Subscription & Delivery
Test** approval gate and an authenticated NonProd operator session.

1. Confirm AWS account `119033255630` and Region `ap-southeast-1`.
2. Read back the exact topic, policy, tags, alarm states, rules, targets, and
   subscriptions.
3. Abort for policy/routing drift, an unexpected `ALARM`, or any existing
   unknown subscription.
4. Accept the owner-provided email only as ephemeral command input.
5. Issue exactly one email subscription request.
6. Report `PendingConfirmation` and wait for the owner to use the AWS
   confirmation message.
7. Re-read subscriptions at a reasonable interval and require a confirmed ARN.
8. Publish exactly one direct SNS message; do not trigger a real alarm or ECS
   failure.
9. Require the owner to confirm receipt.
10. Re-read subscriptions and alert infrastructure to ensure no unintended
    changes.

Use this exact safe message:

```text
Subject: [TEST] secure-cicd-pipeline NonProd alert delivery

Stage 10.5 notification delivery test.
This is a controlled NonProd portfolio test.
No incident or production outage is occurring.
```

Expected mutation count: one subscription request, one human confirmation, and
one test publication. Confirmation is a human action; the workflow must not
attempt to automate it.

## Data Handling

The human endpoint is private operational data. Supply it only at execution
time, keep it out of shell history where practical, and never commit or record
it in Markdown, Terraform, tfvars examples, GitHub variables/secrets,
deployment evidence, screenshots, or final reports.

AWS-generated notification bodies may include account/resource identifiers,
task ARNs, cluster ARNs, or other operational metadata. That content belongs
only in the private owner inbox or access-controlled AWS evidence. Public
documentation describes categories and outcomes, not raw messages.

## Noise Controls

No human alert is sent for:

- successful CI or Security runs;
- successful deployment;
- normal ECS task lifecycle events;
- normal CPU or memory levels; or
- LOW or MEDIUM Inspector findings.

The portfolio alerts on actionable failures, degradation, and serious security
conditions. Broader or recovery notifications require demonstrated operating
value before they are added.

## Known Limitations

- One solo maintainer owns acknowledgement and response; no independent
  on-call rotation or formal 24x7 SLA exists.
- The human subscription and inbox receipt are not proven until the explicit
  mutation gate is approved and completed.
- SNS uses the accepted NonProd service-default encryption posture. Alert
  payloads remain sanitized/non-secret, and no dedicated CMK is introduced
  solely for this stage.
- CloudTrail, Inspector, and Security Hub lifecycle controls are
  organization-owned and are not inferred from repository source.
