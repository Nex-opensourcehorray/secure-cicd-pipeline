#!/usr/bin/env python3
"""Fail-closed validation for the Stage 9 ECS deployment preflight.

The helper consumes AWS CLI JSON files produced by trusted workflow code. It
does not call AWS, execute candidate source, or construct a registration
payload. Stage 9.2 uses it only to validate the current service, task
definition, and ECR scan state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """Raised when preflight input violates a required invariant."""


@dataclass(frozen=True)
class RuntimeExpectations:
    cluster_arn: str
    service_arn: str
    service_name: str
    task_family: str
    container_name: str
    execution_role_arn: str
    image_prefix: str
    region: str


TASK_DEFINITION_RESPONSE_FIELDS = {
    "compatibilities",
    "registeredAt",
    "registeredBy",
    "requiresAttributes",
    "revision",
    "status",
    "taskDefinitionArn",
}

TASK_DEFINITION_EXPECTED_INPUT_FIELDS = {
    "containerDefinitions",
    "cpu",
    "executionRoleArn",
    "family",
    "memory",
    "networkMode",
    "placementConstraints",
    "requiresCompatibilities",
    "runtimePlatform",
    "volumes",
}

# AWS may omit these defaulted fields or return them explicitly. Any non-null
# task role or enabled fault injection still fails below.
TASK_DEFINITION_OPTIONAL_DEFAULT_FIELDS = {
    "enableFaultInjection",
    "taskRoleArn",
}

CONTAINER_EXPECTED_FIELDS = {
    "cpu",
    "environment",
    "essential",
    "healthCheck",
    "image",
    "linuxParameters",
    "logConfiguration",
    "mountPoints",
    "name",
    "portMappings",
    "privileged",
    "readonlyRootFilesystem",
    "systemControls",
    "user",
    "volumesFrom",
}

EXPECTED_HEALTH_COMMAND = [
    "CMD",
    "python",
    "-c",
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).close()",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def require_exact_keys(
    value: dict[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    keys = set(value)
    missing = required - keys
    unexpected = keys - required - optional
    require(not missing, f"{label} is missing fields: {sorted(missing)}")
    require(not unexpected, f"{label} has unexpected fields: {sorted(unexpected)}")


def load_json(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"unable to read valid JSON: {path}") from exc
    return require_object(value, "document")


def validate_service(
    service_document: dict[str, Any], expectations: RuntimeExpectations
) -> tuple[dict[str, Any], str]:
    services = service_document.get("services")
    require(isinstance(services, list), "services must be an array")
    require(len(services) == 1, "exactly one ECS service must be returned")
    failures = service_document.get("failures", [])
    require(failures == [], "ECS service discovery returned failures")

    service = require_object(services[0], "service")
    require(service.get("serviceArn") == expectations.service_arn, "service ARN mismatch")
    require(service.get("clusterArn") == expectations.cluster_arn, "cluster ARN mismatch")
    require(service.get("serviceName") == expectations.service_name, "service name mismatch")
    require(service.get("status") == "ACTIVE", "service must be ACTIVE")
    require(service.get("desiredCount") == 1, "service desired count must be 1")
    require(service.get("runningCount") == 1, "service running count must be 1")
    require(service.get("pendingCount") == 0, "service pending count must be 0")
    require(service.get("launchType") == "FARGATE", "service launch type must be FARGATE")
    require(service.get("enableExecuteCommand") is False, "ECS Exec must be disabled")

    task_definition_arn = service.get("taskDefinition")
    task_pattern = re.compile(
        rf"^arn:aws:ecs:[^:]+:[0-9]{{12}}:task-definition/"
        rf"{re.escape(expectations.task_family)}:[1-9][0-9]*$"
    )
    require(
        isinstance(task_definition_arn, str) and task_pattern.fullmatch(task_definition_arn),
        "service task definition does not belong to the approved family",
    )

    deployments = service.get("deployments")
    require(isinstance(deployments, list), "service deployments must be an array")
    primary = [item for item in deployments if item.get("status") == "PRIMARY"]
    require(len(primary) == 1, "service must have exactly one PRIMARY deployment")
    require(primary[0].get("rolloutState") == "COMPLETED", "PRIMARY rollout must be COMPLETED")
    require(primary[0].get("taskDefinition") == task_definition_arn, "PRIMARY task definition mismatch")

    deployment_configuration = require_object(
        service.get("deploymentConfiguration"), "deploymentConfiguration"
    )
    require(
        deployment_configuration.get("minimumHealthyPercent") == 100,
        "minimum healthy percent must be 100",
    )
    require(
        deployment_configuration.get("maximumPercent") == 200,
        "maximum deployment percent must be 200",
    )
    circuit_breaker = require_object(
        deployment_configuration.get("deploymentCircuitBreaker"),
        "deploymentCircuitBreaker",
    )
    require(circuit_breaker.get("enable") is True, "deployment circuit breaker must be enabled")
    require(circuit_breaker.get("rollback") is True, "deployment rollback must be enabled")

    network = require_object(service.get("networkConfiguration"), "networkConfiguration")
    awsvpc = require_object(network.get("awsvpcConfiguration"), "awsvpcConfiguration")
    require(awsvpc.get("assignPublicIp") == "DISABLED", "public task IP assignment must be disabled")

    load_balancers = service.get("loadBalancers")
    require(isinstance(load_balancers, list), "loadBalancers must be an array")
    require(len(load_balancers) == 1, "service must have exactly one load balancer association")
    association = require_object(load_balancers[0], "load balancer association")
    require(association.get("containerName") == expectations.container_name, "load balancer container mismatch")
    require(association.get("containerPort") == 8000, "load balancer container port must be 8000")

    return service, task_definition_arn


def validate_task_definition(
    task_document: dict[str, Any],
    task_definition_arn: str,
    expectations: RuntimeExpectations,
) -> tuple[dict[str, Any], str, str]:
    require_exact_keys(
        task_document, {"taskDefinition"}, {"tags"}, "task-definition response"
    )
    require(task_document.get("tags", []) == [], "task-definition tags must be empty")
    task = require_object(task_document.get("taskDefinition"), "taskDefinition")
    require_exact_keys(
        task,
        TASK_DEFINITION_RESPONSE_FIELDS | TASK_DEFINITION_EXPECTED_INPUT_FIELDS,
        TASK_DEFINITION_OPTIONAL_DEFAULT_FIELDS,
        "taskDefinition",
    )

    require(task.get("taskDefinitionArn") == task_definition_arn, "task-definition ARN mismatch")
    require(task.get("family") == expectations.task_family, "task-definition family mismatch")
    require(task.get("status") == "ACTIVE", "task definition must be ACTIVE")
    require(task.get("requiresCompatibilities") == ["FARGATE"], "FARGATE must be the only required compatibility")
    require(task.get("networkMode") == "awsvpc", "network mode must be awsvpc")
    require(str(task.get("cpu")) == "256", "task CPU must be 256")
    require(str(task.get("memory")) == "512", "task memory must be 512")
    require(task.get("executionRoleArn") == expectations.execution_role_arn, "execution role mismatch")
    require(task.get("taskRoleArn") in (None, ""), "task role must be absent")
    require(task.get("enableFaultInjection") in (None, False), "fault injection must be disabled")
    require(task.get("volumes") == [], "task volumes must be empty")
    require(task.get("placementConstraints") == [], "task placement constraints must be empty")

    runtime = require_object(task.get("runtimePlatform"), "runtimePlatform")
    require_exact_keys(runtime, {"cpuArchitecture", "operatingSystemFamily"}, set(), "runtimePlatform")
    require(runtime.get("operatingSystemFamily") == "LINUX", "operating system must be LINUX")
    require(runtime.get("cpuArchitecture") == "X86_64", "CPU architecture must be X86_64")

    containers = task.get("containerDefinitions")
    require(isinstance(containers, list), "containerDefinitions must be an array")
    require(len(containers) == 1, "exactly one container definition is supported")
    container = require_object(containers[0], "containerDefinition")
    require_exact_keys(container, CONTAINER_EXPECTED_FIELDS, set(), "containerDefinition")
    require(container.get("name") == expectations.container_name, "container name mismatch")
    require(container.get("essential") is True, "application container must be essential")
    require(container.get("cpu") == 0, "container CPU override must remain zero")
    require(container.get("user") == "10001:10001", "container must run as 10001:10001")
    require(container.get("privileged") is False, "container must not be privileged")
    require(container.get("readonlyRootFilesystem") is True, "root filesystem must be read-only")

    image = container.get("image")
    image_pattern = re.compile(re.escape(expectations.image_prefix) + r"(sha256:[0-9a-f]{64})$")
    match = image_pattern.fullmatch(image) if isinstance(image, str) else None
    require(match is not None, "container image must use the approved repository and an immutable digest")
    digest = match.group(1)

    linux_parameters = require_object(container.get("linuxParameters"), "linuxParameters")
    require_exact_keys(linux_parameters, {"capabilities"}, set(), "linuxParameters")
    capabilities = require_object(linux_parameters.get("capabilities"), "capabilities")
    require_exact_keys(capabilities, {"add", "drop"}, set(), "capabilities")
    require(capabilities.get("add") == [], "no Linux capability may be added")
    require(capabilities.get("drop") == ["ALL"], "all Linux capabilities must be dropped")

    for field in ("environment", "mountPoints", "systemControls", "volumesFrom"):
        require(container.get(field) == [], f"{field} must be an empty array")

    ports = container.get("portMappings")
    require(isinstance(ports, list) and len(ports) == 1, "exactly one port mapping is required")
    require(
        ports[0] == {"containerPort": 8000, "hostPort": 8000, "protocol": "tcp"},
        "port mapping must be exactly TCP/8000",
    )

    logging = require_object(container.get("logConfiguration"), "logConfiguration")
    require_exact_keys(logging, {"logDriver", "options"}, set(), "logConfiguration")
    require(logging.get("logDriver") == "awslogs", "log driver must be awslogs")
    require(
        logging.get("options")
        == {
            "awslogs-group": "/ecs/secure-cicd-pipeline/nonprod",
            "awslogs-region": expectations.region,
            "awslogs-stream-prefix": "ecs",
        },
        "awslogs options mismatch",
    )

    health = require_object(container.get("healthCheck"), "healthCheck")
    require_exact_keys(
        health,
        {"command", "interval", "timeout", "retries", "startPeriod"},
        set(),
        "healthCheck",
    )
    require(health.get("command") == EXPECTED_HEALTH_COMMAND, "health-check command mismatch")
    require(health.get("interval") == 30, "health-check interval must be 30")
    require(health.get("timeout") == 5, "health-check timeout must be 5")
    require(health.get("retries") == 3, "health-check retries must be 3")
    require(health.get("startPeriod") == 30, "health-check start period must be 30")

    return task, image, digest


def validate_runtime(
    service_document: dict[str, Any],
    task_document: dict[str, Any],
    expectations: RuntimeExpectations,
) -> dict[str, Any]:
    _, task_definition_arn = validate_service(service_document, expectations)
    task, image, digest = validate_task_definition(
        task_document, task_definition_arn, expectations
    )
    return {
        "current_digest": digest,
        "current_image": image,
        "task_definition_arn": task_definition_arn,
        "task_definition_revision": task["revision"],
        "task_definition_response_only_fields": sorted(TASK_DEFINITION_RESPONSE_FIELDS),
        "status": "PASS",
    }


def validate_scan(scan_document: dict[str, Any], label: str) -> dict[str, Any]:
    status = require_object(scan_document.get("imageScanStatus"), "imageScanStatus")
    require(status.get("status") == "ACTIVE", f"{label} enhanced scan status must be ACTIVE")
    findings = require_object(scan_document.get("imageScanFindings"), "imageScanFindings")

    reported = findings.get("findingSeverityCounts", {})
    require(isinstance(reported, dict), "findingSeverityCounts must be an object")
    for severity, count in reported.items():
        require(isinstance(severity, str), "severity names must be strings")
        require(isinstance(count, int) and count >= 0, "severity counts must be non-negative integers")

    enumerated: Counter[str] = Counter()
    for collection_name in ("enhancedFindings", "findings"):
        collection = findings.get(collection_name, [])
        require(isinstance(collection, list), f"{collection_name} must be an array")
        for finding in collection:
            item = require_object(finding, collection_name[:-1] or "finding")
            severity = item.get("severity")
            if severity is not None:
                require(isinstance(severity, str), "finding severity must be a string")
                enumerated[severity.upper()] += 1

    critical = max(int(reported.get("CRITICAL", 0)), enumerated["CRITICAL"])
    high = max(int(reported.get("HIGH", 0)), enumerated["HIGH"])
    require(critical == 0, f"{label} image has active CRITICAL findings")
    require(high == 0, f"{label} image has active HIGH findings")
    return {
        "critical": critical,
        "high": high,
        "label": label,
        "scan_status": "ACTIVE",
        "status": "PASS",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    runtime = subparsers.add_parser("runtime", help="validate service and task-definition JSON")
    runtime.add_argument("--service", required=True)
    runtime.add_argument("--task-definition", required=True)
    runtime.add_argument("--expected-cluster-arn", required=True)
    runtime.add_argument("--expected-service-arn", required=True)
    runtime.add_argument("--expected-service-name", required=True)
    runtime.add_argument("--expected-task-family", required=True)
    runtime.add_argument("--expected-container-name", required=True)
    runtime.add_argument("--expected-execution-role-arn", required=True)
    runtime.add_argument("--expected-image-prefix", required=True)
    runtime.add_argument("--expected-region", required=True)

    scan = subparsers.add_parser("scan", help="validate enhanced-scan JSON")
    scan.add_argument("--input", required=True)
    scan.add_argument("--label", required=True, choices=("candidate", "rollback"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "runtime":
            expectations = RuntimeExpectations(
                cluster_arn=args.expected_cluster_arn,
                service_arn=args.expected_service_arn,
                service_name=args.expected_service_name,
                task_family=args.expected_task_family,
                container_name=args.expected_container_name,
                execution_role_arn=args.expected_execution_role_arn,
                image_prefix=args.expected_image_prefix,
                region=args.expected_region,
            )
            result = validate_runtime(
                load_json(args.service),
                load_json(args.task_definition),
                expectations,
            )
        else:
            result = validate_scan(load_json(args.input), args.label)
    except ValidationError as exc:
        print(f"preflight validation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
