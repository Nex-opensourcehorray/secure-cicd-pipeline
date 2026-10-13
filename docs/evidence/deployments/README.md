# Deployment Evidence Records

This directory is the durable, human-reviewed portfolio record for meaningful
NonProd ECS deployment outcomes. It is intentionally empty of deployment
records until a real deployment occurs. Stage 9 preflight validation was not a
live deployment and is not represented here as one.

## Evidence layers

1. GitHub retains workflow runs, checks, Environment approval records, job
   logs, and workflow summaries for the configured bounded retention period.
2. A future deployment workflow run produces a sanitized artifact containing
   only `deployment-evidence.json` and `deployment-evidence.sha256`.
3. A maintainer may promote the reviewed JSON manifest into this directory
   through the normal feature-branch, pull-request, required-check, and merge
   process.

The GitHub artifact is operational evidence with a 90-day target. A manifest
merged here is durable until removed through normal Git history and repository
governance. Neither layer replaces authoritative AWS audit records, whose
retention is not claimed without separate verification.

## Accepted record

A repository record must:

- conform to `deployment-evidence.schema.json` and schema version `1`;
- have been produced by the allowlist-based evidence generator;
- correlate to the named GitHub workflow run and attempt;
- use one approved outcome: `SUCCESS`,
  `AUTOMATIC_ROLLBACK_CONFIRMED`, `FAIL_CLOSED_UNVERIFIED`, or
  `PRE_MUTATION_FAILURE`;
- have a verified manifest checksum from the workflow artifact; and
- remain limited to the sanitized JSON manifest after review.

Use this filename convention:

```text
YYYY-MM-DD-run-<github_run_id>.json
```

Do not add a record for a simulated, local, preflight-only, or otherwise
non-live deployment. Do not copy the checksum file into the durable directory;
verify it before promotion and record the reviewed JSON through Git history.

## Prohibited data

Never retain credentials, tokens, authorization headers, GitHub Environment
variable values, repository secret values, raw environment dumps, private IP
addresses, ECS task IDs, ENI IDs, session credentials, local filesystem paths,
user email addresses, notification destinations, raw AWS errors, or raw AWS
responses. Prefer the task-definition family, revision integers, image
digests, finding counts, and verified boolean outcomes over full resource
identifiers.

Treat workflow artifacts as potentially reviewable outside the private AWS
environment. Sanitization is mandatory and must not depend on artifact
confidentiality.

## Manual promotion procedure

1. Download the GitHub deployment-evidence artifact.
2. Verify `deployment-evidence.sha256` against `deployment-evidence.json`.
3. Validate the manifest against the schema and inspect its sanitization.
4. Confirm the run ID, attempt, source SHAs, outcome, and artifact digest match
   the GitHub workflow record.
5. Copy only `deployment-evidence.json` here using the naming convention.
6. Create a normal feature-branch commit and pull request.
7. Let all required CI and Security checks pass.
8. Review the evidence diff and merge through the governed `main` process.

The deployment workflow must never write to this directory. It must not gain
`contents: write`, use `git push`, call a repository file-write API, or use a
GitHub App credential with repository-write authority. This preserves human
review and keeps source governance independent of deployment authority.

## Checksums

The workflow checksum uses the conventional form:

```text
<sha256>  deployment-evidence.json
```

It detects accidental or unauthorized manifest changes and aids correlation.
It is not a digital signature and does not establish signer identity.
