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
                        "targetGroupArn": "arn:aws:elasticloadbalancing:example",
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
)


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
