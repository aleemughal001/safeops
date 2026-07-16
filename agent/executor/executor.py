"""SafeOps Remediation Executor service.

Prototype behavior:
- Enforces the action allowlist locally.
- Supports dry-run/simulated execution by default.
- Supports a tightly scoped Kubernetes mode for the local demo.
- Provides /verify endpoint so the backend can close the loop.

Safety rules for this prototype:
- No arbitrary shell commands.
- No delete operations.
- Real Kubernetes actions are restricted by environment allowlists.
- Default real-action scope is namespace=demo and service/deployment=checkout-api.
- Smart env remediation is restricted to REDIS_URL with a known-good value.

This service must run with narrowly scoped Kubernetes RBAC in real deployments.
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from kubernetes import client, config
    from kubernetes.config.config_exception import ConfigException
except Exception:  # Kubernetes dependency may not be installed in backend-only demos.
    client = None  # type: ignore
    config = None  # type: ignore
    ConfigException = Exception  # type: ignore

app = FastAPI(title="SafeOps Executor", version="0.4.0")

EXECUTOR_MODE = os.getenv("SAFEOPS_EXECUTOR_MODE", "simulate")  # simulate | kubernetes
VERIFY_TIMEOUT_SECONDS = int(os.getenv("SAFEOPS_VERIFY_TIMEOUT_SECONDS", "90"))
VERIFY_INTERVAL_SECONDS = float(os.getenv("SAFEOPS_VERIFY_INTERVAL_SECONDS", "2"))
KUBECTL_BIN = os.getenv("SAFEOPS_KUBECTL_BIN", "kubectl")

DEFAULT_REDIS_URL = "redis://redis.demo.svc.cluster.local:6379"


def _env_set(name: str, default_csv: str) -> set[str]:
    raw = os.getenv(name, default_csv)
    return {item.strip() for item in raw.split(",") if item.strip()}


# Defense-in-depth scope restrictions. Backend policy also checks these, but the
# executor must protect itself even if a caller bypasses the backend.
ALLOWED_K8S_NAMESPACES = _env_set("SAFEOPS_ALLOWED_K8S_NAMESPACES", "demo")
ALLOWED_K8S_SERVICES = _env_set("SAFEOPS_ALLOWED_K8S_SERVICES", "checkout-api")
ALLOWED_ENV_NAMES = _env_set("SAFEOPS_ALLOWED_ENV_NAMES", "REDIS_URL")
ALLOWED_REDIS_URL = os.getenv("SAFEOPS_ALLOWED_REDIS_URL", DEFAULT_REDIS_URL)

ALLOWED_ACTIONS = {
    "set_env_deployment": {
        "description": "Set a tightly allowlisted environment variable on a Kubernetes deployment.",
        "approval_required": True,
        "resource": "deployment",
    },
    "rollout_undo_deployment": {
        "description": "Roll back a Kubernetes deployment to the previous stable version.",
        "approval_required": True,
        "resource": "deployment",
    },
    "rollout_restart_deployment": {
        "description": "Restart a Kubernetes deployment.",
        "approval_required": True,
        "resource": "deployment",
    },
    "rerun_pipeline": {
        "description": "Re-run a CI/CD workflow or pipeline.",
        "approval_required": True,
        "resource": "pipeline",
    },
    "create_issue": {
        "description": "Create a tracking issue with incident context.",
        "approval_required": False,
        "resource": "issue",
    },
}

BLOCKED_ACTIONS = {
    "delete_namespace",
    "delete_secret",
    "edit_secret",
    "run_arbitrary_command",
    "modify_iam_policy",
}


class ExecuteRequest(BaseModel):
    incident_id: str
    action_id: str
    approved: bool
    approved_by: Optional[str] = None
    service: str = Field(..., description="Kubernetes deployment/service name")
    namespace: str = Field(default="default")
    dry_run: bool = Field(default=True)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class VerifyRequest(BaseModel):
    incident_id: str
    action_id: str
    execution_id: str
    service: str
    namespace: str = Field(default="default")
    parameters: Dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "mode": EXECUTOR_MODE,
        "allowed_namespaces": sorted(ALLOWED_K8S_NAMESPACES),
        "allowed_services": sorted(ALLOWED_K8S_SERVICES),
        "allowed_env_names": sorted(ALLOWED_ENV_NAMES),
    }


def validate_action(action_id: str, approved: bool) -> Dict[str, Any]:
    if action_id in BLOCKED_ACTIONS:
        return {"allowed": False, "reason": "Action is explicitly blocked."}
    if action_id not in ALLOWED_ACTIONS:
        return {"allowed": False, "reason": "Action is not allowlisted."}
    if ALLOWED_ACTIONS[action_id]["approval_required"] and not approved:
        return {"allowed": False, "reason": "Human approval is required."}
    return {"allowed": True, "reason": "Action is allowlisted and approved."}


def _load_kube_config() -> None:
    if config is None:
        raise RuntimeError("kubernetes package is not installed")
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()


def _guard_kubernetes_scope(namespace: str, service: str) -> None:
    if namespace not in ALLOWED_K8S_NAMESPACES:
        raise HTTPException(
            status_code=403,
            detail={
                "allowed": False,
                "reason": f"Namespace {namespace!r} is outside executor allowlist.",
                "allowed_namespaces": sorted(ALLOWED_K8S_NAMESPACES),
            },
        )
    if service not in ALLOWED_K8S_SERVICES:
        raise HTTPException(
            status_code=403,
            detail={
                "allowed": False,
                "reason": f"Service/deployment {service!r} is outside executor allowlist.",
                "allowed_services": sorted(ALLOWED_K8S_SERVICES),
            },
        )


def _guard_set_env_parameters(parameters: Dict[str, Any]) -> tuple[str, str]:
    env_name = str(parameters.get("env_name", ""))
    env_value = str(parameters.get("env_value", ""))

    if env_name not in ALLOWED_ENV_NAMES:
        raise HTTPException(
            status_code=403,
            detail={
                "allowed": False,
                "reason": f"Environment variable {env_name!r} is outside executor allowlist.",
                "allowed_env_names": sorted(ALLOWED_ENV_NAMES),
            },
        )

    if env_name == "REDIS_URL" and env_value != ALLOWED_REDIS_URL:
        raise HTTPException(
            status_code=403,
            detail={
                "allowed": False,
                "reason": "REDIS_URL value is not the approved known-good demo value.",
                "expected_value": ALLOWED_REDIS_URL,
            },
        )

    if not env_value:
        raise HTTPException(status_code=403, detail="env_value is required for set_env_deployment.")

    return env_name, env_value


def _run_kubectl(args: List[str], timeout: int = 30) -> Dict[str, Any]:
    """Run a fixed kubectl argv list. Never use shell=True."""
    command = [KUBECTL_BIN] + args
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    finished = datetime.now(timezone.utc).isoformat()
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "started_at": started,
        "finished_at": finished,
    }


def _simulate_execute(request: ExecuteRequest) -> Dict[str, Any]:
    return {
        "execution_id": f"exec_{uuid4().hex[:12]}",
        "status": "executed",
        "mode": "simulate",
        "action_id": request.action_id,
        "service": request.service,
        "namespace": request.namespace,
        "parameters": request.parameters,
        "message": f"Simulated {request.action_id} for deployment/{request.service} in namespace {request.namespace}.",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


def _kubernetes_execute(request: ExecuteRequest) -> Dict[str, Any]:
    _guard_kubernetes_scope(namespace=request.namespace, service=request.service)

    if request.dry_run:
        result = _simulate_execute(request)
        result["mode"] = "kubernetes-dry-run"
        result["message"] = (
            f"Kubernetes dry-run accepted for {request.action_id} on "
            f"deployment/{request.service} in namespace {request.namespace}."
        )
        return result

    started_at = datetime.now(timezone.utc).isoformat()
    kubectl_result: Optional[Dict[str, Any]] = None

    if request.action_id == "set_env_deployment":
        env_name, env_value = _guard_set_env_parameters(request.parameters)
        kubectl_result = _run_kubectl(
            [
                "-n",
                request.namespace,
                "set",
                "env",
                f"deployment/{request.service}",
                f"{env_name}={env_value}",
            ],
            timeout=30,
        )
        if kubectl_result["returncode"] != 0:
            raise HTTPException(status_code=500, detail={"kubectl": kubectl_result})
        message = kubectl_result["stdout"] or f"Set {env_name} on deployment/{request.service}."

    elif request.action_id == "rollout_undo_deployment":
        # Fixed argv only. This is not arbitrary command execution.
        kubectl_result = _run_kubectl(
            ["-n", request.namespace, "rollout", "undo", f"deployment/{request.service}"],
            timeout=30,
        )
        if kubectl_result["returncode"] != 0:
            raise HTTPException(status_code=500, detail={"kubectl": kubectl_result})
        message = kubectl_result["stdout"] or f"Rolled back deployment/{request.service}."

    elif request.action_id == "rollout_restart_deployment":
        _load_kube_config()
        apps_api = client.AppsV1Api()  # type: ignore[union-attr]
        patch_body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "safeops.dev/restarted-at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                }
            }
        }
        apps_api.patch_namespaced_deployment(
            name=request.service,
            namespace=request.namespace,
            body=patch_body,
        )
        message = f"Restarted deployment/{request.service}."

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported Kubernetes action {request.action_id}")

    return {
        "execution_id": f"exec_{uuid4().hex[:12]}",
        "status": "executed",
        "mode": "kubernetes",
        "action_id": request.action_id,
        "service": request.service,
        "namespace": request.namespace,
        "parameters": request.parameters,
        "message": message,
        "kubectl": kubectl_result,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/execute")
def execute(request: ExecuteRequest) -> Dict[str, Any]:
    validation = validate_action(request.action_id, request.approved)
    if not validation["allowed"]:
        raise HTTPException(status_code=403, detail=validation)

    if EXECUTOR_MODE == "kubernetes":
        return _kubernetes_execute(request)
    return _simulate_execute(request)


def _simulate_verify(request: VerifyRequest) -> Dict[str, Any]:
    return {
        "verification_id": f"ver_{uuid4().hex[:12]}",
        "execution_id": request.execution_id,
        "status": "healthy",
        "mode": "simulate",
        "checks": [
            {"name": "rollout_status", "status": "passed", "detail": "Simulated rollout is complete."},
            {"name": "pod_readiness", "status": "passed", "detail": "Simulated pods are ready."},
            {"name": "service_health", "status": "passed", "detail": "Simulated health endpoint returned 200."},
            {"name": "error_rate", "status": "passed", "detail": "Simulated error rate recovered."},
        ],
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def _deployment_health_snapshot(namespace: str, service: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _load_kube_config()
    apps_api = client.AppsV1Api()  # type: ignore[union-attr]
    core_api = client.CoreV1Api()  # type: ignore[union-attr]

    checks = []
    healthy = True
    parameters = parameters or {}

    deployment = apps_api.read_namespaced_deployment(name=service, namespace=namespace)
    desired = deployment.spec.replicas or 0
    ready = deployment.status.ready_replicas or 0
    available = deployment.status.available_replicas or 0
    unavailable = deployment.status.unavailable_replicas or 0
    updated = deployment.status.updated_replicas or 0
    rollout_passed = desired > 0 and ready >= desired and available >= desired and unavailable == 0
    checks.append(
        {
            "name": "rollout_status",
            "status": "passed" if rollout_passed else "failed",
            "detail": f"desired={desired}, updated={updated}, ready={ready}, available={available}, unavailable={unavailable}",
        }
    )
    healthy = healthy and rollout_passed

    expected_env_name = parameters.get("env_name")
    expected_env_value = parameters.get("env_value")
    if expected_env_name and expected_env_value:
        container = deployment.spec.template.spec.containers[0]
        env_map = {env.name: env.value for env in (container.env or [])}
        env_passed = env_map.get(expected_env_name) == expected_env_value
        checks.append(
            {
                "name": "deployment_env",
                "status": "passed" if env_passed else "failed",
                "detail": f"{expected_env_name} present={expected_env_name in env_map}",
            }
        )
        healthy = healthy and env_passed

    pods = core_api.list_namespaced_pod(namespace=namespace, label_selector=f"app={service}")
    active_pods = [pod for pod in pods.items if pod.metadata.deletion_timestamp is None]
    pod_count = len(active_pods)
    ready_pods = 0
    not_ready_details = []
    for pod in active_pods:
        statuses = pod.status.container_statuses or []
        pod_ready = bool(statuses) and all(cs.ready for cs in statuses)
        if pod_ready:
            ready_pods += 1
        else:
            reason_parts = []
            for cs in statuses:
                if cs.state and cs.state.waiting:
                    reason_parts.append(f"{cs.name}:waiting={cs.state.waiting.reason}")
                if cs.state and cs.state.terminated:
                    reason_parts.append(f"{cs.name}:terminated={cs.state.terminated.reason}")
            not_ready_details.append(f"{pod.metadata.name}({','.join(reason_parts) or pod.status.phase})")

    pods_passed = desired > 0 and ready_pods >= desired and not not_ready_details
    checks.append(
        {
            "name": "pod_readiness",
            "status": "passed" if pods_passed else "failed",
            "detail": f"ready_pods={ready_pods}, active_pods={pod_count}, desired={desired}, not_ready={not_ready_details}",
        }
    )
    healthy = healthy and pods_passed

    return {"healthy": healthy, "checks": checks}


def _kubernetes_verify(request: VerifyRequest) -> Dict[str, Any]:
    _guard_kubernetes_scope(namespace=request.namespace, service=request.service)

    deadline = time.time() + VERIFY_TIMEOUT_SECONDS
    last_snapshot: Dict[str, Any] = {"healthy": False, "checks": []}
    while time.time() <= deadline:
        try:
            last_snapshot = _deployment_health_snapshot(
                request.namespace,
                request.service,
                parameters=request.parameters,
            )
            if last_snapshot["healthy"]:
                break
        except Exception as exc:
            last_snapshot = {
                "healthy": False,
                "checks": [{"name": "kubernetes_api", "status": "failed", "detail": str(exc)}],
            }
        time.sleep(VERIFY_INTERVAL_SECONDS)

    return {
        "verification_id": f"ver_{uuid4().hex[:12]}",
        "execution_id": request.execution_id,
        "status": "healthy" if last_snapshot.get("healthy") else "unhealthy",
        "mode": "kubernetes",
        "checks": last_snapshot.get("checks", []),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "timeout_seconds": VERIFY_TIMEOUT_SECONDS,
    }


@app.post("/verify")
def verify(request: VerifyRequest) -> Dict[str, Any]:
    if EXECUTOR_MODE == "kubernetes":
        return _kubernetes_verify(request)
    return _simulate_verify(request)
