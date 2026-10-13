#!/usr/bin/env python3
"""Fail-closed preparation and validation for the Stage 9 ECS deployment.

The helper consumes AWS CLI JSON files produced by trusted workflow code. It
does not call AWS or execute candidate source. It validates the current
runtime, constructs allowlisted ECS mutation requests, and validates the
resulting task-definition revision and deployed runtime.
"""

from __future__ import annotations

import argparse
import copy
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
    target_group_arn: str
    alb_security_group_id: str


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

REGISTER_TASK_DEFINITION_FIELDS = TASK_DEFINITION_EXPECTED_INPUT_FIELDS | {
    "enableFaultInjection",
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
    require(
        association.get("targetGroupArn") == expectations.target_group_arn,
        "load balancer target group mismatch",
    )

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
    require(
        isinstance(task.get("revision"), int) and task["revision"] > 0,
        "task-definition revision must be a positive integer",
    )
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


def validate_digest_image(
    image: Any, expectations: RuntimeExpectations, label: str
) -> str:
    pattern = re.compile(
        re.escape(expectations.image_prefix) + r"(sha256:[0-9a-f]{64})$"
    )
    match = pattern.fullmatch(image) if isinstance(image, str) else None
    require(
        match is not None,
        f"{label} image must use the approved repository and an immutable digest",
    )
    return match.group(1)


def task_definition_identity(
    task_definition_arn: Any, expectations: RuntimeExpectations
) -> tuple[str, int]:
    account_id = expectations.cluster_arn.split(":")[4]
    prefix = (
        f"arn:aws:ecs:{expectations.region}:{account_id}:task-definition/"
        f"{expectations.task_family}:"
    )
    require(
        isinstance(task_definition_arn, str)
        and task_definition_arn.startswith(prefix),
        "task-definition ARN must use the approved account, Region, and family",
    )
    revision_text = task_definition_arn.removeprefix(prefix)
    require(
        re.fullmatch(r"[1-9][0-9]*", revision_text) is not None,
        "task-definition revision must be a positive integer",
    )
    return task_definition_arn, int(revision_text)


def registration_payload_from_task(
    task: dict[str, Any],
    candidate_image: str,
    expectations: RuntimeExpectations,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current_image = task["containerDefinitions"][0]["image"]
    current_digest = validate_digest_image(current_image, expectations, "current")
    candidate_digest = validate_digest_image(candidate_image, expectations, "candidate")
    require(
        candidate_digest != current_digest,
        "candidate digest must differ from the currently serving digest",
    )

    current_payload = {
        "family": task["family"],
        "containerDefinitions": copy.deepcopy(task["containerDefinitions"]),
        "volumes": copy.deepcopy(task["volumes"]),
        "placementConstraints": copy.deepcopy(task["placementConstraints"]),
        "executionRoleArn": task["executionRoleArn"],
        "requiresCompatibilities": copy.deepcopy(task["requiresCompatibilities"]),
        "networkMode": task["networkMode"],
        "cpu": str(task["cpu"]),
        "memory": str(task["memory"]),
        "runtimePlatform": copy.deepcopy(task["runtimePlatform"]),
        "enableFaultInjection": False,
    }
    require_exact_keys(
        current_payload,
        REGISTER_TASK_DEFINITION_FIELDS,
        set(),
        "registration payload",
    )

    candidate_payload = copy.deepcopy(current_payload)
    candidate_payload["containerDefinitions"][0]["image"] = candidate_image

    expected_candidate = copy.deepcopy(current_payload)
    expected_candidate["containerDefinitions"][0]["image"] = candidate_image
    require(
        candidate_payload == expected_candidate,
        "candidate task definition must differ only by container image",
    )
    require(
        "taskRoleArn" not in candidate_payload,
        "registration payload must omit taskRoleArn",
    )

    return candidate_payload, {
        "candidate_digest": candidate_digest,
        "candidate_image": candidate_image,
        "current_digest": current_digest,
        "current_image": current_image,
        "semantic_change": "containerDefinitions[0].image",
        "status": "PASS",
    }


def prepare_registration(
    service_document: dict[str, Any],
    task_document: dict[str, Any],
    candidate_image: str,
    expectations: RuntimeExpectations,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime = validate_runtime(service_document, task_document, expectations)
    task = require_object(task_document.get("taskDefinition"), "taskDefinition")
    payload, evidence = registration_payload_from_task(
        task, candidate_image, expectations
    )
    return payload, {
        **runtime,
        **evidence,
        "registration_payload_fields": sorted(payload),
        "task_definition_response_only_fields_excluded": sorted(
            TASK_DEFINITION_RESPONSE_FIELDS
        ),
    }


def validate_registration_response(
    registration_document: dict[str, Any],
    previous_task_definition_arn: str,
    previous_revision: int,
    candidate_image: str,
    expectations: RuntimeExpectations,
) -> dict[str, Any]:
    previous_arn, parsed_previous_revision = task_definition_identity(
        previous_task_definition_arn, expectations
    )
    require(
        previous_revision == parsed_previous_revision,
        "previous task-definition revision evidence is inconsistent",
    )
    task = require_object(
        registration_document.get("taskDefinition"), "taskDefinition"
    )
    new_arn, new_revision = task_definition_identity(
        task.get("taskDefinitionArn"), expectations
    )
    require(
        new_revision > previous_revision,
        "registered task-definition revision must increase monotonically",
    )
    _, image, digest = validate_task_definition(
        registration_document, new_arn, expectations
    )
    require(image == candidate_image, "registered task definition image mismatch")
    return {
        "candidate_digest": digest,
        "new_task_definition_arn": new_arn,
        "new_task_definition_revision": new_revision,
        "previous_task_definition_arn": previous_arn,
        "previous_task_definition_revision": previous_revision,
        "previous_revision_preserved": True,
        "status": "PASS",
    }


def validate_service_update_request(
    request: dict[str, Any],
    task_definition_arn: str,
    expectations: RuntimeExpectations,
) -> None:
    require_exact_keys(
        request,
        {"cluster", "service", "taskDefinition"},
        set(),
        "UpdateService request",
    )
    expected_cluster_name = expectations.cluster_arn.rsplit("/", 1)[-1]
    require(request.get("cluster") == expected_cluster_name, "update cluster mismatch")
    require(request.get("service") == expectations.service_name, "update service mismatch")
    task_definition_identity(task_definition_arn, expectations)
    require(
        request.get("taskDefinition") == task_definition_arn,
        "update task-definition ARN mismatch",
    )


def build_service_update_request(
    task_definition_arn: str, expectations: RuntimeExpectations
) -> dict[str, Any]:
    request = {
        "cluster": expectations.cluster_arn.rsplit("/", 1)[-1],
        "service": expectations.service_name,
        "taskDefinition": task_definition_arn,
    }
    validate_service_update_request(request, task_definition_arn, expectations)
    return request


def validate_update_response(
    response: dict[str, Any],
    expected_task_definition_arn: str,
    expectations: RuntimeExpectations,
) -> dict[str, Any]:
    require_exact_keys(response, {"service"}, set(), "UpdateService response")
    service = require_object(response.get("service"), "service")
    require(service.get("serviceArn") == expectations.service_arn, "service ARN mismatch")
    require(service.get("clusterArn") == expectations.cluster_arn, "cluster ARN mismatch")
    require(service.get("serviceName") == expectations.service_name, "service name mismatch")
    require(service.get("status") == "ACTIVE", "updated service must remain ACTIVE")
    require(service.get("desiredCount") == 1, "updated service desired count must remain 1")
    require(service.get("launchType") == "FARGATE", "updated service must remain FARGATE")
    require(service.get("enableExecuteCommand") is False, "ECS Exec must remain disabled")
    require(
        service.get("taskDefinition") == expected_task_definition_arn,
        "updated service task-definition mismatch",
    )

    deployment_configuration = require_object(
        service.get("deploymentConfiguration"), "deploymentConfiguration"
    )
    require(
        deployment_configuration.get("minimumHealthyPercent") == 100,
        "minimum healthy percent must remain 100",
    )
    require(
        deployment_configuration.get("maximumPercent") == 200,
        "maximum deployment percent must remain 200",
    )
    circuit_breaker = require_object(
        deployment_configuration.get("deploymentCircuitBreaker"),
        "deploymentCircuitBreaker",
    )
    require(circuit_breaker == {"enable": True, "rollback": True}, "circuit breaker mismatch")

    network = require_object(service.get("networkConfiguration"), "networkConfiguration")
    awsvpc = require_object(network.get("awsvpcConfiguration"), "awsvpcConfiguration")
    require(awsvpc.get("assignPublicIp") == "DISABLED", "public task IP must remain disabled")

    load_balancers = service.get("loadBalancers")
    require(isinstance(load_balancers, list) and len(load_balancers) == 1, "load balancer association mismatch")
    association = require_object(load_balancers[0], "load balancer association")
    require(
        association
        == {
            "targetGroupArn": expectations.target_group_arn,
            "containerName": expectations.container_name,
            "containerPort": 8000,
        },
        "load balancer association changed unexpectedly",
    )
    return {
        "service_arn": expectations.service_arn,
        "task_definition_arn": expected_task_definition_arn,
        "status": "PASS",
    }


def validate_deployed_runtime(
    service_document: dict[str, Any],
    task_document: dict[str, Any],
    tasks_document: dict[str, Any],
    target_health_document: dict[str, Any],
    security_group_document: dict[str, Any],
    expected_task_definition_arn: str,
    expected_image: str,
    expectations: RuntimeExpectations,
) -> dict[str, Any]:
    runtime = validate_runtime(service_document, task_document, expectations)
    require(
        runtime["task_definition_arn"] == expected_task_definition_arn,
        "stable service does not use the registered task definition",
    )
    expected_digest = validate_digest_image(expected_image, expectations, "deployed")
    require(runtime["current_image"] == expected_image, "stable task definition image mismatch")

    require(tasks_document.get("failures", []) == [], "task discovery returned failures")
    tasks = tasks_document.get("tasks")
    require(isinstance(tasks, list) and len(tasks) == 1, "exactly one running service task is required")
    task = require_object(tasks[0], "task")
    require(task.get("clusterArn") == expectations.cluster_arn, "running task cluster mismatch")
    require(task.get("taskDefinitionArn") == expected_task_definition_arn, "running task revision mismatch")
    require(task.get("lastStatus") == "RUNNING", "task must be RUNNING")
    require(task.get("desiredStatus") == "RUNNING", "task desired status must be RUNNING")
    require(task.get("healthStatus") == "HEALTHY", "task must be HEALTHY")

    containers = task.get("containers")
    require(isinstance(containers, list) and len(containers) == 1, "exactly one running container is required")
    container = require_object(containers[0], "running container")
    require(container.get("name") == expectations.container_name, "running container name mismatch")
    require(container.get("imageDigest") == expected_digest, "running container digest mismatch")
    require(container.get("lastStatus") == "RUNNING", "container must be RUNNING")

    attachments = task.get("attachments")
    require(isinstance(attachments, list) and len(attachments) == 1, "exactly one task network attachment is required")
    attachment = require_object(attachments[0], "task attachment")
    require(attachment.get("type") == "ElasticNetworkInterface", "task attachment must be an ENI")
    details = attachment.get("details")
    require(isinstance(details, list), "task attachment details must be an array")
    detail_map = {
        item.get("name"): item.get("value")
        for item in details
        if isinstance(item, dict)
    }
    private_ip = detail_map.get("privateIPv4Address")
    require(isinstance(private_ip, str) and private_ip != "", "task private IPv4 address is required")
    require("publicIPv4Address" not in detail_map, "task must not have a public IPv4 address")

    target_descriptions = target_health_document.get("TargetHealthDescriptions")
    require(
        isinstance(target_descriptions, list) and len(target_descriptions) >= 1,
        "at least one target-health result is required",
    )
    matching_targets = []
    draining_targets = []
    for item in target_descriptions:
        target = require_object(item, "target health")
        target_value = require_object(target.get("Target"), "target")
        target_health = require_object(
            target.get("TargetHealth"), "target health state"
        )
        if (
            target_value.get("Id") == private_ip
            and target_value.get("Port") == 8000
        ):
            matching_targets.append(target_health)
        else:
            draining_targets.append(target_health)
    require(
        len(matching_targets) == 1,
        "target group must contain the running task private IP on port 8000",
    )
    require(
        matching_targets[0].get("State") == "healthy",
        "running task target must be healthy",
    )
    require(
        all(item.get("State") == "draining" for item in draining_targets),
        "unexpected non-draining target remains in the target group",
    )

    groups = security_group_document.get("SecurityGroups")
    require(isinstance(groups, list) and len(groups) == 1, "exactly one ALB security group is required")
    group = require_object(groups[0], "ALB security group")
    require(group.get("GroupId") == expectations.alb_security_group_id, "ALB security group mismatch")
    require(group.get("IpPermissions") == [], "ALB security group must have zero ingress rules")

    return {
        "expected_digest": expected_digest,
        "public_task_ip": None,
        "running_task_definition_arn": expected_task_definition_arn,
        "service_counts": {"desired": 1, "pending": 0, "running": 1},
        "draining_target_count": len(draining_targets),
        "target_health": "healthy",
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


def add_expectation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--expected-cluster-arn", required=True)
    parser.add_argument("--expected-service-arn", required=True)
    parser.add_argument("--expected-service-name", required=True)
    parser.add_argument("--expected-task-family", required=True)
    parser.add_argument("--expected-container-name", required=True)
    parser.add_argument("--expected-execution-role-arn", required=True)
    parser.add_argument("--expected-image-prefix", required=True)
    parser.add_argument("--expected-region", required=True)
    parser.add_argument("--expected-target-group-arn", required=True)
    parser.add_argument("--expected-alb-security-group-id", required=True)


def expectations_from_args(args: argparse.Namespace) -> RuntimeExpectations:
    return RuntimeExpectations(
        cluster_arn=args.expected_cluster_arn,
        service_arn=args.expected_service_arn,
        service_name=args.expected_service_name,
        task_family=args.expected_task_family,
        container_name=args.expected_container_name,
        execution_role_arn=args.expected_execution_role_arn,
        image_prefix=args.expected_image_prefix,
        region=args.expected_region,
        target_group_arn=args.expected_target_group_arn,
        alb_security_group_id=args.expected_alb_security_group_id,
    )


def write_json(path: str, value: dict[str, Any]) -> None:
    try:
        Path(path).write_text(
            json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ValidationError(f"unable to write JSON: {path}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    runtime = subparsers.add_parser("runtime", help="validate service and task-definition JSON")
    runtime.add_argument("--service", required=True)
    runtime.add_argument("--task-definition", required=True)
    add_expectation_arguments(runtime)

    prepare = subparsers.add_parser(
        "prepare", help="construct an allowlisted RegisterTaskDefinition request"
    )
    prepare.add_argument("--service", required=True)
    prepare.add_argument("--task-definition", required=True)
    prepare.add_argument("--candidate-image", required=True)
    prepare.add_argument("--output-payload", required=True)
    add_expectation_arguments(prepare)

    registration = subparsers.add_parser(
        "registration", help="validate a RegisterTaskDefinition response"
    )
    registration.add_argument("--input", required=True)
    registration.add_argument("--previous-task-definition-arn", required=True)
    registration.add_argument("--previous-revision", required=True, type=int)
    registration.add_argument("--candidate-image", required=True)
    add_expectation_arguments(registration)

    update_request = subparsers.add_parser(
        "update-request", help="construct an exact UpdateService request"
    )
    update_request.add_argument("--task-definition-arn", required=True)
    update_request.add_argument("--output-request", required=True)
    add_expectation_arguments(update_request)

    update_response = subparsers.add_parser(
        "update-response", help="validate an UpdateService response"
    )
    update_response.add_argument("--input", required=True)
    update_response.add_argument("--task-definition-arn", required=True)
    add_expectation_arguments(update_response)

    deployed = subparsers.add_parser(
        "deployed", help="validate the stable deployed service and target"
    )
    deployed.add_argument("--service", required=True)
    deployed.add_argument("--task-definition", required=True)
    deployed.add_argument("--tasks", required=True)
    deployed.add_argument("--target-health", required=True)
    deployed.add_argument("--security-group", required=True)
    deployed.add_argument("--expected-task-definition-arn", required=True)
    deployed.add_argument("--expected-image", required=True)
    add_expectation_arguments(deployed)

    scan = subparsers.add_parser("scan", help="validate enhanced-scan JSON")
    scan.add_argument("--input", required=True)
    scan.add_argument("--label", required=True, choices=("candidate", "rollback"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            result = validate_scan(load_json(args.input), args.label)
        else:
            expectations = expectations_from_args(args)
            if args.command == "runtime":
                result = validate_runtime(
                    load_json(args.service),
                    load_json(args.task_definition),
                    expectations,
                )
            elif args.command == "prepare":
                payload, result = prepare_registration(
                    load_json(args.service),
                    load_json(args.task_definition),
                    args.candidate_image,
                    expectations,
                )
                write_json(args.output_payload, payload)
            elif args.command == "registration":
                result = validate_registration_response(
                    load_json(args.input),
                    args.previous_task_definition_arn,
                    args.previous_revision,
                    args.candidate_image,
                    expectations,
                )
            elif args.command == "update-request":
                request = build_service_update_request(
                    args.task_definition_arn, expectations
                )
                write_json(args.output_request, request)
                result = {
                    "request_fields": sorted(request),
                    "status": "PASS",
                    "task_definition_arn": args.task_definition_arn,
                }
            elif args.command == "update-response":
                result = validate_update_response(
                    load_json(args.input),
                    args.task_definition_arn,
                    expectations,
                )
            else:
                result = validate_deployed_runtime(
                    load_json(args.service),
                    load_json(args.task_definition),
                    load_json(args.tasks),
                    load_json(args.target_health),
                    load_json(args.security_group),
                    args.expected_task_definition_arn,
                    args.expected_image,
                    expectations,
                )
    except ValidationError as exc:
        print(f"preflight validation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
