"""SafeOps Remediation Executor service.

Prototype behavior:
- Enforces the action allowlist locally.
- Supports dry-run/simulated execution by default.
- Optionally uses Kubernetes APIs when SAFEOPS_EXECUTOR_MODE=kubernetes.
- Provides /verify endpoint so the backend can close the loop.

This service must run with narrowly scoped Kubernetes RBAC in real deployments.
It must never execute arbitrary shell commands.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from kubernetes import client, config
    from kubernetes.config.config_exception import ConfigException
except Exception:  # Kubernetes dependency may not be installed in local backend-only demos.
    client = None  # type: ignore
    config = None  # type: ignore
    ConfigException = Exception  # type: ignore

app = FastAPI(title="SafeOps Executor", version="0.2.0")

EXECUTOR_MODE = os.getenv("SAFEOPS_EXECUTOR_MODE", "simulate")  # simulate | kubernetes

ALLOWED_ACTIONS = {
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
def health() -> Dict[str, str]:
    return {"status": "ok", "mode": EXECUTOR_MODE}


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


def _simulate_execute(request: ExecuteRequest) -> Dict[str, Any]:
    return {
        "execution_id": f"exec_{uuid4().hex[:12]}",
        "status": "executed",
        "mode": "simulate",
        "action_id": request.action_id,
        "service": request.service,
        "namespace": request.namespace,
        "message": f"Simulated {request.action_id} for deployment/{request.service} in namespace {request.namespace}.",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


def _kubernetes_execute(request: ExecuteRequest) -> Dict[str, Any]:
    if request.dry_run:
        return _simulate_execute(request) | {"mode": "kubernetes-dry-run"}

    _load_kube_config()
    apps_api = client.AppsV1Api()  # type: ignore[union-attr]

    if request.action_id == "rollout_restart_deployment":
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
    elif request.action_id == "rollout_undo_deployment":
        # The Kubernetes Python client does not expose `kubectl rollout undo` as a
        # single safe API call. A production executor should use rollout history,
        # ReplicaSet revisions, and a strict patch strategy. For this prototype,
        # keep real rollback disabled and use dry-run/simulated mode.
        raise HTTPException(
            status_code=501,
            detail="Real rollout undo is intentionally not implemented in prototype. Use dry_run=true.",
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported Kubernetes action {request.action_id}")

    return {
        "execution_id": f"exec_{uuid4().hex[:12]}",
        "status": "executed",
        "mode": "kubernetes",
        "action_id": request.action_id,
        "service": request.service,
        "namespace": request.namespace,
        "message": f"Executed {request.action_id} for deployment/{request.service}.",
        "started_at": datetime.now(timezone.utc).isoformat(),
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


def _kubernetes_verify(request: VerifyRequest) -> Dict[str, Any]:
    _load_kube_config()
    apps_api = client.AppsV1Api()  # type: ignore[union-attr]
    core_api = client.CoreV1Api()  # type: ignore[union-attr]

    checks = []
    healthy = True

    try:
        deployment = apps_api.read_namespaced_deployment(name=request.service, namespace=request.namespace)
        desired = deployment.spec.replicas or 0
        ready = deployment.status.ready_replicas or 0
        available = deployment.status.available_replicas or 0
        rollout_passed = desired > 0 and ready >= desired and available >= desired
        checks.append(
            {
                "name": "rollout_status",
                "status": "passed" if rollout_passed else "failed",
                "detail": f"desired={desired}, ready={ready}, available={available}",
            }
        )
        healthy = healthy and rollout_passed
    except Exception as exc:
        checks.append({"name": "rollout_status", "status": "failed", "detail": str(exc)})
        healthy = False

    try:
        pods = core_api.list_namespaced_pod(namespace=request.namespace, label_selector=f"app={request.service}")
        pod_count = len(pods.items)
        ready_pods = 0
        for pod in pods.items:
            if pod.status.container_statuses and all(cs.ready for cs in pod.status.container_statuses):
                ready_pods += 1
        pods_passed = pod_count > 0 and ready_pods == pod_count
        checks.append(
            {
                "name": "pod_readiness",
                "status": "passed" if pods_passed else "failed",
                "detail": f"ready_pods={ready_pods}, pod_count={pod_count}",
            }
        )
        healthy = healthy and pods_passed
    except Exception as exc:
        checks.append({"name": "pod_readiness", "status": "failed", "detail": str(exc)})
        healthy = False

    return {
        "verification_id": f"ver_{uuid4().hex[:12]}",
        "execution_id": request.execution_id,
        "status": "healthy" if healthy else "unhealthy",
        "mode": "kubernetes",
        "checks": checks,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/verify")
def verify(request: VerifyRequest) -> Dict[str, Any]:
    if EXECUTOR_MODE == "kubernetes":
        return _kubernetes_verify(request)
    return _simulate_verify(request)
