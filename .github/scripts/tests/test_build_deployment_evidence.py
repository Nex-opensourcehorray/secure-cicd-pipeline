import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).parents[1] / "build_deployment_evidence.py"
SPEC = importlib.util.spec_from_file_location("build_deployment_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
EVIDENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVIDENCE)

SOURCE_SHA = "a" * 40
WORKFLOW_SHA = "b" * 40
CANDIDATE_DIGEST = "sha256:" + "c" * 64
ROLLBACK_DIGEST = "sha256:" + "d" * 64


def evidence_args(outcome=EVIDENCE.OUTCOME_SUCCESS, **overrides):
    values = {
        "repository": EVIDENCE.EXPECTED_REPOSITORY,
        "environment": EVIDENCE.EXPECTED_ENVIRONMENT,
        "task_definition_family": "secure-cicd-pipeline-nonprod",
        "workflow_name": EVIDENCE.EXPECTED_WORKFLOW,
        "run_id": 123456789,
        "run_attempt": 1,
        "source_workflow_sha": WORKFLOW_SHA,
        "candidate_source_sha": SOURCE_SHA,
        "outcome": outcome,
        "candidate_digest": None,
        "candidate_high": None,
        "candidate_critical": None,
        "rollback_revision": None,
        "rollback_digest": None,
        "rollback_high": None,
        "rollback_critical": None,
        "attempted_revision": None,
        "restored_revision": None,
        "service_stable": None,
        "target_healthy": None,
        "public_task_ip_absent": None,
        "alb_ingress_rules": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def successful_args():
    return evidence_args(
        candidate_digest=CANDIDATE_DIGEST,
        candidate_high=0,
        candidate_critical=0,
        rollback_revision=7,
        rollback_digest=ROLLBACK_DIGEST,
        rollback_high=0,
        rollback_critical=0,
        attempted_revision=8,
        service_stable=True,
        target_healthy=True,
        public_task_ip_absent=True,
        alb_ingress_rules=0,
    )


class ValidEvidenceTests(unittest.TestCase):
    def test_success_manifest(self):
        manifest = EVIDENCE.build_manifest(successful_args())
        self.assertEqual(manifest["deployment"]["outcome"], "SUCCESS")
        self.assertTrue(manifest["deployment"]["succeeded"])
        self.assertFalse(manifest["deployment"]["runtime_recovery_verified"])
        self.assertEqual(manifest["deployment"]["attempted_revision"], 8)
        self.assertEqual(manifest["rollback_baseline"]["revision"], 7)
        self.assertTrue(manifest["verification"]["public_task_ip_absent"])

    def test_automatic_rollback_manifest(self):
        args = successful_args()
        args.outcome = EVIDENCE.OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED
        args.restored_revision = 7
        manifest = EVIDENCE.build_manifest(args)
        self.assertFalse(manifest["deployment"]["succeeded"])
        self.assertTrue(manifest["deployment"]["runtime_recovery_verified"])
        self.assertEqual(manifest["deployment"]["restored_revision"], 7)

    def test_pre_mutation_failure_omits_unavailable_values(self):
        manifest = EVIDENCE.build_manifest(
            evidence_args(EVIDENCE.OUTCOME_PRE_MUTATION_FAILURE)
        )
        self.assertEqual(set(manifest["candidate"]), {"source_sha"})
        self.assertNotIn("rollback_baseline", manifest)
        self.assertNotIn("verification", manifest)
        self.assertNotIn("attempted_revision", manifest["deployment"])

    def test_fail_closed_unverified_can_retain_safe_preflight_values(self):
        args = successful_args()
        args.outcome = EVIDENCE.OUTCOME_FAIL_CLOSED_UNVERIFIED
        args.service_stable = None
        args.target_healthy = None
        args.public_task_ip_absent = None
        args.alb_ingress_rules = None
        manifest = EVIDENCE.build_manifest(args)
        self.assertFalse(manifest["deployment"]["succeeded"])
        self.assertFalse(manifest["deployment"]["runtime_recovery_verified"])
        self.assertNotIn("verification", manifest)

    def test_canonical_output_is_deterministic_and_newline_terminated(self):
        manifest = EVIDENCE.build_manifest(successful_args())
        first = EVIDENCE.canonical_json(manifest)
        second = EVIDENCE.canonical_json(copy.deepcopy(manifest))
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))
        self.assertEqual(json.loads(first), manifest)

    def test_fixture_directory_contains_only_manifest_and_checksum(self):
        manifest = EVIDENCE.build_manifest(successful_args())
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "evidence"
            digest = EVIDENCE.write_evidence(manifest, output_dir)
            self.assertEqual(
                {item.name for item in output_dir.iterdir()},
                {EVIDENCE.MANIFEST_NAME, EVIDENCE.CHECKSUM_NAME},
            )
            manifest_bytes = (output_dir / EVIDENCE.MANIFEST_NAME).read_bytes()
            self.assertEqual(digest, hashlib.sha256(manifest_bytes).hexdigest())
            verified = EVIDENCE.verify_checksum(
                output_dir / EVIDENCE.MANIFEST_NAME,
                output_dir / EVIDENCE.CHECKSUM_NAME,
            )
            self.assertEqual(verified, digest)

    def test_schema_file_is_strict_and_versioned(self):
        schema_path = (
            Path(__file__).parents[3]
            / "docs/evidence/deployments/deployment-evidence.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1")
        self.assertFalse(schema["additionalProperties"])


class InvalidEvidenceTests(unittest.TestCase):
    def test_invalid_git_sha_fails(self):
        args = successful_args()
        args.candidate_source_sha = "not-a-sha"
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_invalid_digest_fails(self):
        args = successful_args()
        args.candidate_digest = "sha256:not-a-digest"
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_negative_finding_count_fails(self):
        args = successful_args()
        args.candidate_high = -1
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_invalid_revision_fails(self):
        args = successful_args()
        args.attempted_revision = 0
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_unknown_outcome_fails(self):
        args = successful_args()
        args.outcome = "PROMOTED_MAYBE"
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_unknown_top_level_field_fails(self):
        manifest = EVIDENCE.build_manifest(successful_args())
        manifest["unexpected"] = "value"
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.validate_manifest(manifest)

    def test_pre_mutation_failure_rejects_attempted_revision(self):
        args = evidence_args(
            EVIDENCE.OUTCOME_PRE_MUTATION_FAILURE,
            attempted_revision=8,
        )
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_rollback_requires_restored_revision(self):
        args = successful_args()
        args.outcome = EVIDENCE.OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_rollback_rejects_wrong_restored_revision(self):
        args = successful_args()
        args.outcome = EVIDENCE.OUTCOME_AUTOMATIC_ROLLBACK_CONFIRMED
        args.restored_revision = 6
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_unverified_failure_rejects_restored_revision(self):
        args = successful_args()
        args.outcome = EVIDENCE.OUTCOME_FAIL_CLOSED_UNVERIFIED
        args.restored_revision = 7
        args.service_stable = None
        args.target_healthy = None
        args.public_task_ip_absent = None
        args.alb_ingress_rules = None
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_partial_candidate_bundle_fails(self):
        args = evidence_args(
            EVIDENCE.OUTCOME_FAIL_CLOSED_UNVERIFIED,
            candidate_digest=CANDIDATE_DIGEST,
        )
        with self.assertRaises(EVIDENCE.EvidenceError):
            EVIDENCE.build_manifest(args)

    def test_checksum_mismatch_fails(self):
        manifest = EVIDENCE.build_manifest(successful_args())
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            EVIDENCE.write_evidence(manifest, output_dir)
            manifest_path = output_dir / EVIDENCE.MANIFEST_NAME
            manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
            with self.assertRaises(EVIDENCE.EvidenceError):
                EVIDENCE.verify_checksum(
                    manifest_path,
                    output_dir / EVIDENCE.CHECKSUM_NAME,
                )

    def test_unexpected_output_file_fails_closed(self):
        manifest = EVIDENCE.build_manifest(successful_args())
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "raw-aws-response.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(EVIDENCE.EvidenceError):
                EVIDENCE.write_evidence(manifest, output_dir)


class SanitizationTests(unittest.TestCase):
    def test_prohibited_keys_fail(self):
        for key in (
            "aws_session_token",
            "authorization",
            "private_ip",
            "task_id",
            "eni_id",
            "oidc_token",
            "github_token",
            "secret",
            "password",
        ):
            with self.subTest(key=key), self.assertRaises(EVIDENCE.EvidenceError):
                EVIDENCE.scan_for_sensitive_data({key: "not-a-real-value"})

    def test_credential_token_and_private_address_patterns_fail(self):
        samples = (
            "AKIA" + "A" * 16,
            "eyJabcdefghijk.abcdefghijklmnop.abcdefghijklmnop",
            "Authorization: Bearer placeholder-token",
            "10.0.1.25",
            "C:\\Users\\example\\evidence.json",
        )
        for sample in samples:
            with self.subTest(sample=sample), self.assertRaises(EVIDENCE.EvidenceError):
                EVIDENCE.scan_for_sensitive_data({"safe_key": sample})

    def test_serialized_manifest_contains_no_raw_aws_identifiers(self):
        serialized = EVIDENCE.canonical_json(
            EVIDENCE.build_manifest(successful_args())
        ).decode("utf-8")
        for prohibited in (
            "taskArn",
            "eni_id",
            "private_ip",
            "aws-error",
            "sessionToken",
            "Authorization",
        ):
            self.assertNotIn(prohibited, serialized)


if __name__ == "__main__":
    unittest.main()
