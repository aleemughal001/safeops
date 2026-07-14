"""SafeOps Kubernetes Collector MVP.

Read-only collector for real Kubernetes evidence.

It scans a namespace for unhealthy pods, recent warning events, deployment
environment configuration, and short log excerpts. It then sends an incident
payload to the SafeOps backend /incidents/analyze endpoint.

Safety design:
- Read-only Kubernetes API calls only.
- No secrets collection.
- No arbitrary command execution.
- Log collection is limited and sanitized before sending.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

SAFEOPS_BACKEND_URL = os.getenv("SAFEOPS_BACKEND_URL", "http://localhost:8000")
NAMESPACE = os.getenv("SAFEOPS_NAMESPACE", "demo")
POLL_SECONDS = int(os.getenv("SAFEOPS_POLL_SECONDS", "30"))
RUN_ONCE = os.getenv("SAFEOPS_RUN_ONCE", "false").lower() in {"1", "true", "yes"}
MAX_LOG_CHARS = int(os.getenv("SAFEOPS_MAX_LOG_CHARS", "2000"))

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(secret|token|api[_-]?key)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(authorization:\s*bearer)\s+\S+"),
]


def sanitize_text(text: str) -> str:
    cleaned = text or ""
    for pattern in SENSITIVE_PATTERNS:
        cleaned = pattern.sub(lambda m: f"{m.group(1)}=<redacted>", cleaned)
    cleaned = cleaned.replace("\x00", "")
    return cleaned[:MAX_LOG_CHARS]


def load_kube_config() -> None:
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()


def container_status_evidence(pod: Any) -> Tuple[List[Dict[str, Any]], bool]:
    evidence: List[Dict[str, Any]] = []
    unhealthy = False
    pod_name = pod.metadata.name

    if not pod.status.container_statuses:
        return evidence, unhealthy

    for cs in pod.status.container_statuses:
        state = cs.state
        last_state = cs.last_state
        ready = bool(cs.ready)
        restart_count = int(cs.restart_count or 0)

        details = [
            f"pod={pod_name}",
            f"container={cs.name}",
            f"ready={ready}",
            f"restart_count={restart_count}",
        ]

        if state and state.waiting:
            unhealthy = True
            details.append(f"waiting_reason={state.waiting.reason}")
            if state.waiting.message:
                details.append(f"waiting_message={state.waiting.message}")

        if last_state and last_state.terminated:
            unhealthy = True
            details.append(f"last_terminated_reason={last_state.terminated.reason}")
            details.append(f"exit_code={last_state.terminated.exit_code}")

        if not ready or restart_count > 0:
            unhealthy = True

        if unhealthy:
            evidence.append(
                {
                    "source": "kubernetes.pod_status",
                    "summary": "; ".join(details),
                    "raw_ref": pod_name,
                }
            )

    return evidence, unhealthy


def collect_logs(v1: Any, namespace: str, pod_name: str) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []

    # Try current logs and previous logs. In CrashLoopBackOff, one of these may fail
    # depending on timing/runtime, so errors are also useful evidence.
    for previous in (False, True):
        label = "previous" if previous else "current"
        try:
            log_text = v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                previous=previous,
                tail_lines=80,
                timestamps=False,
            )
            log_text = sanitize_text(log_text)
            if log_text.strip():
                # Keep short evidence summary. Full raw logs should not be stored in MVP.
                first_lines = " | ".join(log_text.strip().splitlines()[:5])
                evidence.append(
                    {
                        "source": f"kubernetes.log.{label}",
                        "summary": first_lines,
                        "raw_ref": pod_name,
                    }
                )
        except Exception as exc:
            evidence.append(
                {
                    "source": f"kubernetes.log.{label}.error",
                    "summary": f"Unable to read {label} logs for pod {pod_name}: {sanitize_text(str(exc))}",
                    "raw_ref": pod_name,
                }
            )

    return evidence


def deployment_config_evidence(apps: Any, namespace: str) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    deployments = apps.list_namespaced_deployment(namespace=namespace)

    for deployment in deployments.items:
        deployment_name = deployment.metadata.name
        for container in deployment.spec.template.spec.containers:
            env_names = [env.name for env in (container.env or [])]
            evidence.append(
                {
                    "source": "kubernetes.deployment_config",
                    "summary": f"Deployment {deployment_name} container {container.name} env_names={env_names}",
                    "raw_ref": deployment_name,
                }
            )
            # Demo-specific but still realistic: missing required env causes many crashes.
            if deployment_name == "checkout-api" and "REDIS_URL" not in env_names:
                evidence.append(
                    {
                        "source": "kubernetes.deployment_config",
                        "summary": "Deployment checkout-api is missing expected environment variable REDIS_URL",
                        "raw_ref": deployment_name,
                    }
                )

    return evidence


def event_evidence(v1: Any, namespace: str) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    events = v1.list_namespaced_event(namespace=namespace)
    sorted_events = sorted(events.items, key=lambda e: e.last_timestamp or e.event_time or e.metadata.creation_timestamp)

    for event in sorted_events[-30:]:
        event_type = event.type or "Unknown"
        reason = event.reason or "Unknown"
        message = event.message or ""
        evidence.append(
            {
                "source": "kubernetes.event",
                "summary": f"{event_type} {reason}: {message}",
                "raw_ref": event.metadata.name,
            }
        )

    return evidence


def collect_namespace_evidence(namespace: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    v1 = client.CoreV1Api()
    apps = client.AppsV1Api()

    evidence: List[Dict[str, Any]] = []
    suspected_service: Optional[str] = None

    pods = v1.list_namespaced_pod(namespace=namespace)
    for pod in pods.items:
        pod_evidence, unhealthy = container_status_evidence(pod)
        evidence.extend(pod_evidence)

        if unhealthy:
            labels = pod.metadata.labels or {}
            suspected_service = labels.get("app") or suspected_service or pod.metadata.name.split("-")[0]
            evidence.extend(collect_logs(v1, namespace, pod.metadata.name))

    evidence.extend(deployment_config_evidence(apps, namespace))
    evidence.extend(event_evidence(v1, namespace))

    return evidence, suspected_service


def incident_needed(evidence: List[Dict[str, Any]]) -> bool:
    evidence_text = " ".join(item.get("summary", "").lower() for item in evidence)
    triggers = [
        "crashloopbackoff",
        "back-off restarting failed container",
        "restart_count=",
        "last_terminated_reason=error",
        "missing required environment variable",
        "missing expected environment variable",
        "imagepullbackoff",
        "errimagepull",
    ]
    return any(trigger in evidence_text for trigger in triggers)


def send_incident_if_needed(evidence: List[Dict[str, Any]], service: Optional[str]) -> None:
    if not incident_needed(evidence):
        print("No SafeOps-triggering incident found.")
        return

    service_name = service or "unknown-service"
    payload = {
        "incident_id": f"inc_{service_name}_{int(time.time())}",
        "service": service_name,
        "namespace": NAMESPACE,
        "symptoms": ["Kubernetes workload is unhealthy"],
        "evidence": evidence,
    }

    print(f"Sending incident to SafeOps backend: service={service_name}, evidence_count={len(evidence)}")
    try:
        response = requests.post(f"{SAFEOPS_BACKEND_URL}/incidents/analyze", json=payload, timeout=10)
        response.raise_for_status()
        print(response.json())
    except Exception as exc:
        print(f"Failed to send incident evidence: {exc}")


def main() -> None:
    load_kube_config()
    print(f"SafeOps collector started for namespace={NAMESPACE}, backend={SAFEOPS_BACKEND_URL}, run_once={RUN_ONCE}")

    while True:
        evidence, suspected_service = collect_namespace_evidence(NAMESPACE)
        send_incident_if_needed(evidence, suspected_service)

        if RUN_ONCE:
            break
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
