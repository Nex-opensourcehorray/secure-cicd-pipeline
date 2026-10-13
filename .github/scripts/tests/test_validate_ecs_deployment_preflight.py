import copy
import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_ecs_deployment_preflight.py"
SPEC = importlib.util.spec_from_file_location("validate_ecs_deployment_preflight", MODULE_PATH)
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREFLIGHT
SPEC.loader.exec_module(PREFLIGHT)


ACCOUNT = "119033255630"
REGION = "ap-southeast-1"
FAMILY = "secure-cicd-pipeline-nonprod"
CONTAINER = "secure-cicd-demo"
CLUSTER_ARN = f"arn:aws:ecs:{REGION}:{ACCOUNT}:cluster/{FAMILY}"
SERVICE_ARN = f"arn:aws:ecs:{REGION}:{ACCOUNT}:service/{FAMILY}/{FAMILY}"
TASK_ARN = f"arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/{FAMILY}:1"
EXECUTION_ROLE = f"arn:aws:iam::{ACCOUNT}:role/{FAMILY}-ecs-execution"
IMAGE_PREFIX = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/secure-cicd-demo@"
DIGEST = "sha256:" + "8" * 64
CANDIDATE_DIGEST = "sha256:" + "9" * 64
TARGET_GROUP_ARN = (
    f"arn:aws:elasticloadbalancing:{REGION}:{ACCOUNT}:"
    "targetgroup/secure-cicd-pipeline-nonprod-tg/919de08359876a7b"
)
ALB_SECURITY_GROUP_ID = "sg-0a082963a48d1cc39"


def valid_service():
    return {
        "failures": [],
        "services": [
            {
                "serviceArn": SERVICE_ARN,
                "clusterArn": CLUSTER_ARN,
                "serviceName": FAMILY,
                "status": "ACTIVE",
                "desiredCount": 1,
                "runningCount": 1,
                "pendingCount": 0,
                "launchType": "FARGATE",
                "enableExecuteCommand": False,
                "taskDefinition": TASK_ARN,
                "deployments": [
                    {
                        "status": "PRIMARY",
                        "rolloutState": "COMPLETED",
                        "taskDefinition": TASK_ARN,
                    }
                ],
                "deploymentConfiguration": {
                    "minimumHealthyPercent": 100,
                    "maximumPercent": 200,
                    "deploymentCircuitBreaker": {"enable": True, "rollback": True},
                },
                "networkConfiguration": {
                    "awsvpcConfiguration": {"assignPublicIp": "DISABLED"}
                },
                "loadBalancers": [
                    {
                        "containerName": CONTAINER,
                        "containerPort": 8000,
                        "targetGroupArn": TARGET_GROUP_ARN,
                    }
                ],
            }
        ],
    }


def valid_task_definition():
    return {
        "taskDefinition": {
            "taskDefinitionArn": TASK_ARN,
            "containerDefinitions": [
                {
                    "name": CONTAINER,
                    "image": IMAGE_PREFIX + DIGEST,
                    "cpu": 0,
                    "portMappings": [
                        {"containerPort": 8000, "hostPort": 8000, "protocol": "tcp"}
                    ],
                    "essential": True,
                    "environment": [],
                    "mountPoints": [],
                    "volumesFrom": [],
                    "linuxParameters": {
                        "capabilities": {"add": [], "drop": ["ALL"]}
                    },
                    "readonlyRootFilesystem": True,
                    "privileged": False,
                    "user": "10001:10001",
                    "healthCheck": {
                        "command": list(PREFLIGHT.EXPECTED_HEALTH_COMMAND),
                        "interval": 30,
                        "timeout": 5,
                        "retries": 3,
                        "startPeriod": 30,
                    },
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/ecs/secure-cicd-pipeline/nonprod",
                            "awslogs-region": REGION,
                            "awslogs-stream-prefix": "ecs",
                        },
                    },
                    "systemControls": [],
                }
            ],
            "family": FAMILY,
            "executionRoleArn": EXECUTION_ROLE,
            "networkMode": "awsvpc",
            "revision": 1,
            "volumes": [],
            "status": "ACTIVE",
            "requiresAttributes": [],
            "placementConstraints": [],
            "compatibilities": ["EC2", "FARGATE"],
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "256",
            "memory": "512",
            "registeredAt": "2026-01-01T00:00:00Z",
            "registeredBy": "arn:aws:iam::example",
            "runtimePlatform": {
                "cpuArchitecture": "X86_64",
                "operatingSystemFamily": "LINUX",
            },
        }
    }


EXPECTATIONS = PREFLIGHT.RuntimeExpectations(
    cluster_arn=CLUSTER_ARN,
    service_arn=SERVICE_ARN,
    service_name=FAMILY,
    task_family=FAMILY,
    container_name=CONTAINER,
    execution_role_arn=EXECUTION_ROLE,
    image_prefix=IMAGE_PREFIX,
    region=REGION,
    target_group_arn=TARGET_GROUP_ARN,
    alb_security_group_id=ALB_SECURITY_GROUP_ID,
)


def registered_task_definition():
    document = valid_task_definition()
    task = document["taskDefinition"]
    task["taskDefinitionArn"] = TASK_ARN.removesuffix(":1") + ":2"
    task["revision"] = 2
    task["containerDefinitions"][0]["image"] = IMAGE_PREFIX + CANDIDATE_DIGEST
    return document


def valid_update_response():
    service = copy.deepcopy(valid_service()["services"][0])
    new_arn = TASK_ARN.removesuffix(":1") + ":2"
    service["taskDefinition"] = new_arn
    service["deployments"][0]["taskDefinition"] = new_arn
    service["deployments"][0]["rolloutState"] = "IN_PROGRESS"
    service["deploymentConfiguration"]["deploymentCircuitBreaker"].update(
        {
            "resetOnHealthyTask": True,
            "thresholdConfiguration": {"type": "BOUNDED_PERCENT", "value": 50},
        }
    )
    service["deploymentConfiguration"].update(
        {"strategy": "ROLLING", "bakeTimeInMinutes": 0}
    )
    return {"service": service}


def valid_tasks():
    return {
        "failures": [],
        "tasks": [
            {
                "attachments": [
                    {
                        "type": "ElasticNetworkInterface",
                        "details": [
                            {"name": "subnetId", "value": "subnet-123"},
                            {
                                "name": "networkInterfaceId",
                                "value": "eni-123",
                            },
                            {
                                "name": "privateIPv4Address",
                                "value": "10.0.1.10",
                            },
                        ],
                    }
                ],
                "clusterArn": CLUSTER_ARN,
                "containers": [
                    {
                        "name": CONTAINER,
                        "imageDigest": CANDIDATE_DIGEST,
                        "lastStatus": "RUNNING",
                    }
                ],
                "desiredStatus": "RUNNING",
                "healthStatus": "HEALTHY",
                "lastStatus": "RUNNING",
                "taskDefinitionArn": TASK_ARN.removesuffix(":1") + ":2",
            }
        ],
    }


def valid_target_health():
    return {
        "TargetHealthDescriptions": [
            {
                "Target": {"Id": "10.0.1.10", "Port": 8000},
                "TargetHealth": {"State": "healthy"},
            }
        ]
    }


def valid_security_group():
    return {
        "SecurityGroups": [
            {"GroupId": ALB_SECURITY_GROUP_ID, "IpPermissions": []}
        ]
    }


class RuntimeValidationTests(unittest.TestCase):
    def assert_invalid(self, mutator):
        service = valid_service()
        task = valid_task_definition()
        mutator(service, task)
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_runtime(service, task, EXPECTATIONS)

    def test_valid_current_task_definition_passes(self):
        result = PREFLIGHT.validate_runtime(
            valid_service(), valid_task_definition(), EXPECTATIONS
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["current_digest"], DIGEST)

    def test_wrong_family_fails(self):
        self.assert_invalid(lambda _s, t: t["taskDefinition"].update(family="wrong"))

    def test_wrong_network_mode_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"].update(networkMode="bridge")
        )

    def test_wrong_runtime_architecture_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["runtimePlatform"].update(
                cpuArchitecture="ARM64"
            )
        )

    def test_task_role_present_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"].update(
                taskRoleArn=f"arn:aws:iam::{ACCOUNT}:role/not-approved"
            )
        )

    def test_fault_injection_enabled_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"].update(enableFaultInjection=True)
        )

    def test_wrong_execution_role_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"].update(executionRoleArn="wrong")
        )

    def test_privileged_true_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0].update(
                privileged=True
            )
        )

    def test_writable_root_filesystem_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0].update(
                readonlyRootFilesystem=False
            )
        )

    def test_non_root_user_missing_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0].update(
                user=None
            )
        )

    def test_capabilities_must_drop_all(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0][
                "linuxParameters"
            ]["capabilities"].update(drop=[])
        )

    def test_unexpected_capability_add_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0][
                "linuxParameters"
            ]["capabilities"].update(add=["NET_ADMIN"])
        )

    def test_wrong_cpu_fails(self):
        self.assert_invalid(lambda _s, t: t["taskDefinition"].update(cpu="512"))

    def test_wrong_memory_fails(self):
        self.assert_invalid(lambda _s, t: t["taskDefinition"].update(memory="1024"))

    def test_wrong_port_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0].update(
                portMappings=[
                    {"containerPort": 9000, "hostPort": 9000, "protocol": "tcp"}
                ]
            )
        )

    def test_wrong_log_group_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0][
                "logConfiguration"
            ]["options"].update({"awslogs-group": "/wrong"})
        )

    def test_wrong_health_check_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0][
                "healthCheck"
            ].update(command=["CMD", "false"])
        )

    def test_mutable_tag_image_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0].update(
                image=IMAGE_PREFIX.removesuffix("@") + ":latest"
            )
        )

    def test_malformed_digest_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"]["containerDefinitions"][0].update(
                image=IMAGE_PREFIX + "sha256:not-a-digest"
            )
        )

    def test_unexpected_second_container_fails(self):
        def mutate(_service, task):
            extra = copy.deepcopy(task["taskDefinition"]["containerDefinitions"][0])
            extra["name"] = "sidecar"
            task["taskDefinition"]["containerDefinitions"].append(extra)

        self.assert_invalid(mutate)

    def test_unexpected_registration_field_fails(self):
        self.assert_invalid(
            lambda _s, t: t["taskDefinition"].update(ephemeralStorage={"sizeInGiB": 40})
        )

    def test_execute_command_enabled_fails(self):
        self.assert_invalid(
            lambda s, _t: s["services"][0].update(enableExecuteCommand=True)
        )

    def test_public_ip_enabled_fails(self):
        self.assert_invalid(
            lambda s, _t: s["services"][0]["networkConfiguration"][
                "awsvpcConfiguration"
            ].update(assignPublicIp="ENABLED")
        )

    def test_wrong_target_group_fails(self):
        self.assert_invalid(
            lambda s, _t: s["services"][0]["loadBalancers"][0].update(
                targetGroupArn="arn:aws:elasticloadbalancing:wrong"
            )
        )

    def test_circuit_breaker_rollback_disabled_fails(self):
        self.assert_invalid(
            lambda s, _t: s["services"][0]["deploymentConfiguration"][
                "deploymentCircuitBreaker"
            ].update(rollback=False)
        )

    def test_task_definition_tags_fail(self):
        self.assert_invalid(
            lambda _s, t: t.update(tags=[{"key": "unexpected", "value": "tag"}])
        )


class TaskDefinitionAutomationTests(unittest.TestCase):
    def test_allowlisted_payload_changes_only_digest_image(self):
        payload, evidence = PREFLIGHT.prepare_registration(
            valid_service(),
            valid_task_definition(),
            IMAGE_PREFIX + CANDIDATE_DIGEST,
            EXPECTATIONS,
        )
        self.assertEqual(set(payload), PREFLIGHT.REGISTER_TASK_DEFINITION_FIELDS)
        self.assertEqual(
            payload["containerDefinitions"][0]["image"],
            IMAGE_PREFIX + CANDIDATE_DIGEST,
        )
        self.assertNotIn("taskRoleArn", payload)
        self.assertFalse(payload["enableFaultInjection"])
        self.assertTrue(
            PREFLIGHT.TASK_DEFINITION_RESPONSE_FIELDS.isdisjoint(payload)
        )
        self.assertEqual(
            evidence["semantic_change"], "containerDefinitions[0].image"
        )

    def test_same_digest_registration_fails(self):
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.prepare_registration(
                valid_service(),
                valid_task_definition(),
                IMAGE_PREFIX + DIGEST,
                EXPECTATIONS,
            )

    def test_registration_response_captures_rollback_metadata(self):
        result = PREFLIGHT.validate_registration_response(
            registered_task_definition(),
            TASK_ARN,
            1,
            IMAGE_PREFIX + CANDIDATE_DIGEST,
            EXPECTATIONS,
        )
        self.assertEqual(result["previous_task_definition_arn"], TASK_ARN)
        self.assertEqual(result["previous_task_definition_revision"], 1)
        self.assertEqual(result["new_task_definition_revision"], 2)
        self.assertTrue(result["previous_revision_preserved"])

    def test_registration_revision_must_increase(self):
        document = registered_task_definition()
        document["taskDefinition"]["taskDefinitionArn"] = TASK_ARN
        document["taskDefinition"]["revision"] = 1
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_registration_response(
                document,
                TASK_ARN,
                1,
                IMAGE_PREFIX + CANDIDATE_DIGEST,
                EXPECTATIONS,
            )


class ServiceUpdateAutomationTests(unittest.TestCase):
    def test_exact_update_request_is_constructed(self):
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        request = PREFLIGHT.build_service_update_request(new_arn, EXPECTATIONS)
        self.assertEqual(
            request,
            {
                "cluster": FAMILY,
                "service": FAMILY,
                "taskDefinition": new_arn,
            },
        )

    def test_desired_count_change_is_rejected(self):
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        request = PREFLIGHT.build_service_update_request(new_arn, EXPECTATIONS)
        request["desiredCount"] = 2
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_service_update_request(
                request, new_arn, EXPECTATIONS
            )

    def test_network_change_is_rejected(self):
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        request = PREFLIGHT.build_service_update_request(new_arn, EXPECTATIONS)
        request["networkConfiguration"] = {}
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_service_update_request(
                request, new_arn, EXPECTATIONS
            )

    def test_wrong_service_is_rejected(self):
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        request = PREFLIGHT.build_service_update_request(new_arn, EXPECTATIONS)
        request["service"] = "other"
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_service_update_request(
                request, new_arn, EXPECTATIONS
            )

    def test_update_response_preserves_service_controls(self):
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        result = PREFLIGHT.validate_update_response(
            valid_update_response(), new_arn, EXPECTATIONS
        )
        self.assertEqual(result["task_definition_arn"], new_arn)

    def test_update_response_rejects_disabled_rollback(self):
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        response = valid_update_response()
        response["service"]["deploymentConfiguration"][
            "deploymentCircuitBreaker"
        ]["rollback"] = False
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_update_response(response, new_arn, EXPECTATIONS)


class DeployedRuntimeValidationTests(unittest.TestCase):
    def stable_candidate_service(self):
        service = valid_service()
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        service["services"][0]["taskDefinition"] = new_arn
        service["services"][0]["deployments"][0]["taskDefinition"] = new_arn
        return service

    def test_stable_candidate_runtime_passes(self):
        new_arn = TASK_ARN.removesuffix(":1") + ":2"
        result = PREFLIGHT.validate_deployed_runtime(
            self.stable_candidate_service(),
            registered_task_definition(),
            valid_tasks(),
            valid_target_health(),
            valid_security_group(),
            new_arn,
            IMAGE_PREFIX + CANDIDATE_DIGEST,
            EXPECTATIONS,
        )
        self.assertEqual(result["target_health"], "healthy")
        self.assertIsNone(result["public_task_ip"])

    def test_public_task_ip_is_rejected(self):
        tasks = valid_tasks()
        tasks["tasks"][0]["attachments"][0]["details"].append(
            {"name": "publicIPv4Address", "value": "203.0.113.10"}
        )
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_deployed_runtime(
                self.stable_candidate_service(),
                registered_task_definition(),
                tasks,
                valid_target_health(),
                valid_security_group(),
                TASK_ARN.removesuffix(":1") + ":2",
                IMAGE_PREFIX + CANDIDATE_DIGEST,
                EXPECTATIONS,
            )

    def test_old_draining_target_is_tolerated(self):
        target_health = valid_target_health()
        target_health["TargetHealthDescriptions"].append(
            {
                "Target": {"Id": "10.0.1.9", "Port": 8000},
                "TargetHealth": {"State": "draining"},
            }
        )
        result = PREFLIGHT.validate_deployed_runtime(
            self.stable_candidate_service(),
            registered_task_definition(),
            valid_tasks(),
            target_health,
            valid_security_group(),
            TASK_ARN.removesuffix(":1") + ":2",
            IMAGE_PREFIX + CANDIDATE_DIGEST,
            EXPECTATIONS,
        )
        self.assertEqual(result["draining_target_count"], 1)


class ScanValidationTests(unittest.TestCase):
    def test_zero_findings_passes_when_counts_are_omitted(self):
        result = PREFLIGHT.validate_scan(
            {
                "imageScanStatus": {"status": "ACTIVE"},
                "imageScanFindings": {"findings": []},
            },
            "candidate",
        )
        self.assertEqual(result["high"], 0)
        self.assertEqual(result["critical"], 0)

    def test_high_summary_fails(self):
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_scan(
                {
                    "imageScanStatus": {"status": "ACTIVE"},
                    "imageScanFindings": {
                        "findingSeverityCounts": {"HIGH": 1},
                        "enhancedFindings": [],
                    },
                },
                "candidate",
            )

    def test_critical_enumerated_finding_fails(self):
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_scan(
                {
                    "imageScanStatus": {"status": "ACTIVE"},
                    "imageScanFindings": {
                        "enhancedFindings": [{"severity": "CRITICAL"}]
                    },
                },
                "rollback",
            )

    def test_unavailable_scan_fails_closed(self):
        with self.assertRaises(PREFLIGHT.ValidationError):
            PREFLIGHT.validate_scan(
                {
                    "imageScanStatus": {"status": "PENDING"},
                    "imageScanFindings": {},
                },
                "candidate",
            )


if __name__ == "__main__":
    unittest.main()
