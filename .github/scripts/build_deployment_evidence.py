#!/usr/bin/env python3
"""Build and verify a small, sanitized deployment evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1"
EXPECTED_REPOSITORY = "Nex-opensourcehorray/secure-cicd-pipeline"
EXPECTED_ENVIRONMENT = "nonprod"
EXPECTED_WORKFLOW = "Deploy approved image to NonProd ECS"
MANIFEST_NAME = "deployment-evidence.json"
CHECKSUM_NAME = "deployment-evidence.sha256"

OUTCOME_SUCCESS = "SUCCESS"
OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED = "AUTOMATIC_ROLLBACK_CONFIRMED"
OUTCOME_FAIL_CLOSED_UNVERIFIED = "FAIL_CLOSED_UNVERIFIED"
OUTCOME_PRE_MUTATION_FAILURE = "PRE_MUTATION_FAILURE"
OUTCOMES = {
    OUTCOME_SUCCESS,
    OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED,
    OUTCOME_FAIL_CLOSED_UNVERIFIED,
    OUTCOME_PRE_MUTATION_FAILURE,
}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CHECKSUM_RE = re.compile(r"^([0-9a-f]{64})  deployment-evidence\.json\n?$")
AWS_KEY_RE = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
PRIVATE_IPV4_RE = re.compile(
    r"(?<![0-9])(?:10(?:\.[0-9]{1,3}){3}|192\.168(?:\.[0-9]{1,3}){2}|"
    r"172\.(?:1[6-9]|2[0-9]|3[01])(?:\.[0-9]{1,3}){2})(?![0-9])"
)
LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/(?:home|Users|tmp)/)")
AUTHORIZATION_RE = re.compile(r"(?i)\b(?:authorization\s*:|bearer\s+[A-Za-z0-9._-]+)")

PROHIBITED_KEYS = {
    "authorization",
    "aws_access_key_id",
    "aws_error",
    "aws_secret_access_key",
    "aws_session_token",
    "credential_store",
    "eni_id",
    "environment_dump",
    "github_token",
    "oidc_jwt",
    "oidc_token",
    "password",
    "private_ip",
    "raw_environment",
    "secret",
    "session_credentials",
    "sns_destination",
    "task_id",
    "token",
}

TOP_LEVEL_KEYS = {
    "candidate",
    "deployment",
    "environment",
    "repository",
    "rollback_baseline",
    "schema_version",
    "task_definition_family",
    "verification",
    "workflow",
}
TOP_LEVEL_REQUIRED = {
    "candidate",
    "deployment",
    "environment",
    "repository",
    "schema_version",
    "task_definition_family",
    "workflow",
}


class EvidenceError(ValueError):
    """Raised when evidence is invalid or cannot be written safely."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def require_exact_keys(
    value: dict[str, Any], required: set[str], optional: set[str], label: str
) -> None:
    keys = set(value)
    require(required <= keys, f"{label} is missing required keys")
    require(keys <= required | optional, f"{label} contains unknown keys")


def require_positive_int(value: Any, label: str) -> int:
    require(
        isinstance(value, int) and not isinstance(value, bool) and value > 0,
        f"{label} must be a positive integer",
    )
    return value


def require_count(value: Any, label: str) -> int:
    require(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0,
        f"{label} must be a non-negative integer",
    )
    return value


def require_bool(value: Any, label: str) -> bool:
    require(isinstance(value, bool), f"{label} must be a boolean")
    return value


def require_sha(value: Any, label: str) -> str:
    require(
        isinstance(value, str) and SHA_RE.fullmatch(value) is not None,
        f"{label} must be a lowercase 40-character Git SHA",
    )
    return value


def require_digest(value: Any, label: str) -> str:
    require(
        isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None,
        f"{label} must be a sha256 image digest",
    )
    return value


def scan_for_sensitive_data(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            require(key.lower() not in PROHIBITED_KEYS, f"{path} contains prohibited key")
            scan_for_sensitive_data(nested, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            scan_for_sensitive_data(nested, f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    require(AWS_KEY_RE.search(value) is None, f"{path} resembles an AWS access key")
    require(JWT_RE.search(value) is None, f"{path} resembles a JWT")
    require(PRIVATE_IPV4_RE.search(value) is None, f"{path} contains a private IPv4 address")
    require(LOCAL_PATH_RE.search(value) is None, f"{path} contains a local filesystem path")
    require(AUTHORIZATION_RE.search(value) is None, f"{path} resembles authorization material")


def validate_manifest(manifest: dict[str, Any]) -> None:
    require(isinstance(manifest, dict), "manifest must be an object")
    require_exact_keys(
        manifest,
        TOP_LEVEL_REQUIRED,
        TOP_LEVEL_KEYS - TOP_LEVEL_REQUIRED,
        "manifest",
    )
    require(manifest["schema_version"] == SCHEMA_VERSION, "schema version mismatch")
    require(manifest["repository"] == EXPECTED_REPOSITORY, "repository mismatch")
    require(manifest["environment"] == EXPECTED_ENVIRONMENT, "environment mismatch")
    require(
        isinstance(manifest["task_definition_family"], str)
        and re.fullmatch(r"[A-Za-z0-9_-]{1,255}", manifest["task_definition_family"]),
        "task-definition family is invalid",
    )

    workflow = manifest["workflow"]
    require(isinstance(workflow, dict), "workflow must be an object")
    require_exact_keys(
        workflow,
        {"name", "run_attempt", "run_id", "source_workflow_sha"},
        set(),
        "workflow",
    )
    require(workflow["name"] == EXPECTED_WORKFLOW, "workflow name mismatch")
    require_positive_int(workflow["run_id"], "workflow run ID")
    require_positive_int(workflow["run_attempt"], "workflow run attempt")
    require_sha(workflow["source_workflow_sha"], "workflow source SHA")

    candidate = manifest["candidate"]
    require(isinstance(candidate, dict), "candidate must be an object")
    require_exact_keys(
        candidate,
        {"source_sha"},
        {"critical_findings", "digest", "high_findings"},
        "candidate",
    )
    require_sha(candidate["source_sha"], "candidate source SHA")
    artifact_fields = {"critical_findings", "digest", "high_findings"}
    present_artifact_fields = artifact_fields & set(candidate)
    require(
        not present_artifact_fields or present_artifact_fields == artifact_fields,
        "candidate artifact fields must be supplied together",
    )
    if present_artifact_fields:
        require_digest(candidate["digest"], "candidate digest")
        require_count(candidate["high_findings"], "candidate HIGH findings")
        require_count(candidate["critical_findings"], "candidate CRITICAL findings")

    rollback = manifest.get("rollback_baseline")
    if rollback is not None:
        require(isinstance(rollback, dict), "rollback baseline must be an object")
        require_exact_keys(
            rollback,
            {"critical_findings", "digest", "high_findings", "revision"},
            set(),
            "rollback baseline",
        )
        require_positive_int(rollback["revision"], "rollback revision")
        require_digest(rollback["digest"], "rollback digest")
        require_count(rollback["high_findings"], "rollback HIGH findings")
        require_count(rollback["critical_findings"], "rollback CRITICAL findings")

    deployment = manifest["deployment"]
    require(isinstance(deployment, dict), "deployment must be an object")
    require_exact_keys(
        deployment,
        {"outcome", "runtime_recovery_verified", "succeeded"},
        {"attempted_revision", "previous_revision", "restored_revision"},
        "deployment",
    )
    outcome = deployment["outcome"]
    require(outcome in OUTCOMES, "deployment outcome is not approved")
    require_bool(deployment["succeeded"], "deployment succeeded")
    require_bool(
        deployment["runtime_recovery_verified"],
        "runtime recovery verification",
    )
    for key in ("attempted_revision", "previous_revision", "restored_revision"):
        if key in deployment:
            require_positive_int(deployment[key], f"deployment {key}")

    verification = manifest.get("verification")
    if verification is not None:
        require(isinstance(verification, dict), "verification must be an object")
        require_exact_keys(
            verification,
            {
                "alb_ingress_rules",
                "public_task_ip_absent",
                "service_stable",
                "target_healthy",
            },
            set(),
            "verification",
        )
        require_bool(verification["service_stable"], "service stability")
        require_bool(verification["target_healthy"], "target health")
        require_bool(
            verification["public_task_ip_absent"],
            "public task IP absence",
        )
        require_count(verification["alb_ingress_rules"], "ALB ingress rules")

    if outcome in {OUTCOME_SUCCESS, OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED}:
        require(
            present_artifact_fields == artifact_fields,
            "terminal deployment evidence requires candidate artifact provenance",
        )
        require(
            rollback is not None,
            "terminal deployment evidence requires a rollback baseline",
        )
        require(
            verification is not None,
            "terminal deployment evidence requires runtime verification",
        )
        require(
            "attempted_revision" in deployment,
            "terminal deployment evidence requires an attempted revision",
        )
        require(
            "previous_revision" in deployment,
            "terminal deployment evidence requires a previous revision",
        )
        require(
            deployment["previous_revision"] == rollback["revision"],
            "previous and rollback revisions must match",
        )
        require(
            deployment["attempted_revision"] > rollback["revision"],
            "attempted revision must be newer than rollback revision",
        )
        require(
            candidate["high_findings"] == 0,
            "successful terminal evidence requires zero candidate HIGH findings",
        )
        require(
            candidate["critical_findings"] == 0,
            "successful terminal evidence requires zero candidate CRITICAL findings",
        )
        require(
            rollback["high_findings"] == 0,
            "rollback baseline requires zero HIGH findings",
        )
        require(
            rollback["critical_findings"] == 0,
            "rollback baseline requires zero CRITICAL findings",
        )
        require(
            verification["service_stable"] is True,
            "service stability must be verified",
        )
        require(
            verification["target_healthy"] is True,
            "target health must be verified",
        )
        require(
            verification["public_task_ip_absent"] is True,
            "public task IP absence must be verified",
        )
        require(
            verification["alb_ingress_rules"] == 0,
            "ALB ingress rules must be zero",
        )

    if outcome == OUTCOME_SUCCESS:
        require(deployment["succeeded"] is True, "SUCCESS must report succeeded=true")
        require(
            deployment["runtime_recovery_verified"] is False,
            "SUCCESS must not claim rollback recovery",
        )
        require(
            "restored_revision" not in deployment,
            "SUCCESS must not record a restored revision",
        )
    elif outcome == OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED:
        require(deployment["succeeded"] is False, "rollback must report succeeded=false")
        require(
            deployment["runtime_recovery_verified"] is True,
            "rollback must verify runtime recovery",
        )
        require(
            "restored_revision" in deployment,
            "rollback must record the restored revision",
        )
        require(
            deployment["restored_revision"] == rollback["revision"],
            "restored revision must match the rollback baseline",
        )
    elif outcome == OUTCOME_PRE_MUTATION_FAILURE:
        require(
            deployment["succeeded"] is False,
            "pre-mutation failure must report succeeded=false",
        )
        require(
            deployment["runtime_recovery_verified"] is False,
            "pre-mutation failure cannot claim runtime recovery",
        )
        require(
            not present_artifact_fields,
            "pre-mutation failure must omit unverified artifact provenance",
        )
        require(rollback is None, "pre-mutation failure must omit rollback baseline")
        require(verification is None, "pre-mutation failure must omit runtime verification")
        require(
            set(deployment) == {
                "outcome",
                "runtime_recovery_verified",
                "succeeded",
            },
            "pre-mutation failure must omit revision fields",
        )
    else:
        require(
            deployment["succeeded"] is False,
            "unverified failure must report succeeded=false",
        )
        require(
            deployment["runtime_recovery_verified"] is False,
            "unverified failure cannot claim runtime recovery",
        )
        require(verification is None, "unverified failure must omit runtime verification")
        require(
            "restored_revision" not in deployment,
            "unverified failure must not claim a restored revision",
        )

    scan_for_sensitive_data(manifest)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    candidate: dict[str, Any] = {"source_sha": args.candidate_source_sha}
    candidate_values = (
        args.candidate_digest,
        args.candidate_high,
        args.candidate_critical,
    )
    if any(value is not None for value in candidate_values):
        require(
            all(value is not None for value in candidate_values),
            "candidate artifact arguments must be supplied together",
        )
        candidate.update(
            {
                "digest": args.candidate_digest,
                "high_findings": args.candidate_high,
                "critical_findings": args.candidate_critical,
            }
        )

    deployment: dict[str, Any] = {
        "outcome": args.outcome,
        "succeeded": args.outcome == OUTCOME_SUCCESS,
        "runtime_recovery_verified": (
            args.outcome == OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED
        ),
    }
    if args.rollback_revision is not None:
        deployment["previous_revision"] = args.rollback_revision
    if args.attempted_revision is not None:
        deployment["attempted_revision"] = args.attempted_revision
    if args.restored_revision is not None:
        deployment["restored_revision"] = args.restored_revision

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "repository": args.repository,
        "environment": args.environment,
        "task_definition_family": args.task_definition_family,
        "workflow": {
            "name": args.workflow_name,
            "run_id": args.run_id,
            "run_attempt": args.run_attempt,
            "source_workflow_sha": args.source_workflow_sha,
        },
        "candidate": candidate,
        "deployment": deployment,
    }

    rollback_values = (
        args.rollback_revision,
        args.rollback_digest,
        args.rollback_high,
        args.rollback_critical,
    )
    if any(value is not None for value in rollback_values):
        require(
            all(value is not None for value in rollback_values),
            "rollback arguments must be supplied together",
        )
        manifest["rollback_baseline"] = {
            "revision": args.rollback_revision,
            "digest": args.rollback_digest,
            "high_findings": args.rollback_high,
            "critical_findings": args.rollback_critical,
        }

    verification_values = (
        args.service_stable,
        args.target_healthy,
        args.public_task_ip_absent,
        args.alb_ingress_rules,
    )
    if any(value is not None for value in verification_values):
        require(
            all(value is not None for value in verification_values),
            "verification arguments must be supplied together",
        )
        manifest["verification"] = {
            "service_stable": args.service_stable,
            "target_healthy": args.target_healthy,
            "public_task_ip_absent": args.public_task_ip_absent,
            "alb_ingress_rules": args.alb_ingress_rules,
        }

    validate_manifest(manifest)
    return manifest


def canonical_json(manifest: dict[str, Any]) -> bytes:
    validate_manifest(manifest)
    text = json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
        separators=(",", ": "),
        sort_keys=True,
    )
    return (text + "\n").encode("utf-8")


def write_evidence(manifest: dict[str, Any], output_dir: Path) -> str:
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    expected_names = {MANIFEST_NAME, CHECKSUM_NAME}
    unexpected = {item.name for item in output_dir.iterdir()} - expected_names
    require(not unexpected, "evidence output directory contains unexpected files")

    manifest_bytes = canonical_json(manifest)
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    manifest_path = output_dir / MANIFEST_NAME
    checksum_path = output_dir / CHECKSUM_NAME
    manifest_path.write_bytes(manifest_bytes)
    checksum_path.write_text(
        f"{digest}  {MANIFEST_NAME}\n",
        encoding="utf-8",
        newline="\n",
    )
    require(
        {item.name for item in output_dir.iterdir()} == expected_names,
        "evidence output must contain exactly the manifest and checksum",
    )
    return digest


def verify_checksum(manifest_path: Path, checksum_path: Path) -> str:
    checksum_text = checksum_path.read_text(encoding="utf-8")
    match = CHECKSUM_RE.fullmatch(checksum_text)
    require(match is not None, "checksum file format is invalid")
    expected = match.group(1)
    actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    require(actual == expected, "manifest checksum mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    require(
        manifest_path.read_bytes() == canonical_json(manifest),
        "manifest JSON is not canonical",
    )
    return actual


def parse_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("expected a non-negative integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build canonical evidence files")
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--repository", required=True)
    build.add_argument("--environment", required=True)
    build.add_argument("--task-definition-family", required=True)
    build.add_argument("--workflow-name", required=True)
    build.add_argument("--run-id", type=positive_int, required=True)
    build.add_argument("--run-attempt", type=positive_int, required=True)
    build.add_argument("--source-workflow-sha", required=True)
    build.add_argument("--candidate-source-sha", required=True)
    build.add_argument("--outcome", choices=sorted(OUTCOMES), required=True)
    build.add_argument("--candidate-digest")
    build.add_argument("--candidate-high", type=non_negative_int)
    build.add_argument("--candidate-critical", type=non_negative_int)
    build.add_argument("--rollback-revision", type=positive_int)
    build.add_argument("--rollback-digest")
    build.add_argument("--rollback-high", type=non_negative_int)
    build.add_argument("--rollback-critical", type=non_negative_int)
    build.add_argument("--attempted-revision", type=positive_int)
    build.add_argument("--restored-revision", type=positive_int)
    build.add_argument("--service-stable", type=parse_bool)
    build.add_argument("--target-healthy", type=parse_bool)
    build.add_argument("--public-task-ip-absent", type=parse_bool)
    build.add_argument("--alb-ingress-rules", type=non_negative_int)

    verify = subparsers.add_parser("verify", help="verify checksum and manifest")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--checksum", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            digest = write_evidence(build_manifest(args), args.output_dir)
        else:
            digest = verify_checksum(args.manifest, args.checksum)
    except (EvidenceError, json.JSONDecodeError, OSError) as exc:
        print(f"deployment evidence error: {exc}", file=sys.stderr)
        return 1
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
