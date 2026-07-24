#!/usr/bin/env python3
"""SafeOps real Kubernetes incident detector with evidence grouping.

Read-only detector for real Kubernetes clusters. It inspects live cluster state,
classifies common workload/release failures, groups related Kubernetes symptoms
into root incidents, and writes JSON + Markdown evidence packs for engineers.

No production changes are made by this script.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ABNORMAL_WAITING_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerConfigError",
    "CreateContainerError",
    "InvalidImageName",
    "RunContainerError",
    "ContainerCreating",
    "PodInitializing",
}

HIGH_SIGNAL_EVENT_PATTERNS = [
    "back-off restarting failed container",
    "failed to pull image",
    "errimagepull",
    "imagepullbackoff",
    "secret .* not found",
    "configmap .* not found",
    "readiness probe failed",
    "liveness probe failed",
    "oomkilled",
    "exceeded its progress deadline",
    "failed scheduling",
    "insufficient cpu",
    "insufficient memory",
]

SECRETISH_KEYS = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|authorization|bearer)"
)
SECRETISH_VALUES = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key|authorization|bearer)\s*[:=]\s*[^\s,;]+"
)

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
SEVERITY_SORT = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_cmd(cmd: List[str], timeout: int = 20) -> Tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def kubectl_json(args: List[str], context: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
    cmd = ["kubectl"]
    if context:
        cmd += ["--context", context]
    cmd += args + ["-o", "json"]
    code, out, err = run_cmd(cmd, timeout=timeout)
    if code != 0:
        raise RuntimeError(f"kubectl command failed: {' '.join(cmd)}\n{err.strip()}")
    try:
        return json.loads(out or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"kubectl returned invalid JSON for {' '.join(cmd)}: {exc}") from exc


def kubectl_text(args: List[str], context: Optional[str] = None, timeout: int = 20) -> str:
    cmd = ["kubectl"]
    if context:
        cmd += ["--context", context]
    cmd += args
    code, out, err = run_cmd(cmd, timeout=timeout)
    if code != 0:
        return f"kubectl_error: {err.strip()}"
    return out


def sanitize_text(text: str, max_chars: int = 5000) -> str:
    if not text:
        return ""
    text = SECRETISH_VALUES.sub(lambda m: m.group(0).split("=")[0] + "=<redacted>" if "=" in m.group(0) else "<redacted>", text)
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line[:1000]
        if SECRETISH_KEYS.search(line):
            line = SECRETISH_KEYS.sub("<redacted-key>", line)
            line = re.sub(r"=\S+", "=<redacted>", line)
        lines.append(line)
    redacted = "\n".join(lines)
    return redacted[:max_chars]


def ns_args(namespace: str) -> List[str]:
    if namespace in {"all", "*", ""}:
        return ["-A"]
    return ["-n", namespace]


def meta(obj: Dict[str, Any], key: str, default: Any = None) -> Any:
    return obj.get("metadata", {}).get(key, default)


def pod_ready(pod: Dict[str, Any]) -> bool:
    """Return True only when Kubernetes currently reports the pod as Ready.

    This prevents stale restart history or old readiness events from being
    treated as active incidents after a pod has already recovered.
    """
    conditions = pod.get("status", {}).get("conditions", []) or []
    for condition in conditions:
        if condition.get("type") == "Ready":
            return condition.get("status") == "True"
    return False


def safe_env_summary(container: Dict[str, Any]) -> Dict[str, Any]:
    env_names = []
    env_value_from = []
    for env in container.get("env", []) or []:
        name = env.get("name")
        if name:
            env_names.append(name)
        if env.get("valueFrom"):
            env_value_from.append({"name": name, "valueFrom_keys": sorted(env.get("valueFrom", {}).keys())})

    env_from = []
    for item in container.get("envFrom", []) or []:
        if "configMapRef" in item:
            env_from.append({"type": "configMapRef", "name": item["configMapRef"].get("name")})
        if "secretRef" in item:
            env_from.append({"type": "secretRef", "name": item["secretRef"].get("name")})

    return {
        "container": container.get("name"),
        "image": container.get("image"),
        "env_names": env_names,
        "env_value_from": env_value_from,
        "env_from_refs": env_from,
        "ports": container.get("ports", []),
        "readinessProbe_present": bool(container.get("readinessProbe")),
        "livenessProbe_present": bool(container.get("livenessProbe")),
        "resources": container.get("resources", {}),
    }


def pod_owner(pod: Dict[str, Any]) -> Dict[str, str]:
    owners = meta(pod, "ownerReferences", []) or []
    if not owners:
        return {"kind": "Pod", "name": meta(pod, "name", "unknown"), "inferred_deployment": ""}
    owner = owners[0]
    owner_kind = owner.get("kind", "Unknown")
    owner_name = owner.get("name", "unknown")
    inferred_deployment = ""
    if owner_kind == "ReplicaSet":
        # Deployment-managed ReplicaSets usually end in a generated hash.
        inferred_deployment = re.sub(r"-[a-f0-9]{8,10}$", "", owner_name)
    return {
        "kind": owner_kind,
        "name": owner_name,
        "inferred_deployment": inferred_deployment,
    }


def event_is_high_signal(event: Dict[str, Any]) -> bool:
    msg = f"{event.get('reason', '')} {event.get('message', '')}".lower()
    return any(re.search(pattern, msg) for pattern in HIGH_SIGNAL_EVENT_PATTERNS)


def compact_event(event: Dict[str, Any]) -> Dict[str, Any]:
    involved = event.get("involvedObject", {})
    return {
        "type": event.get("type"),
        "reason": event.get("reason"),
        "message": sanitize_text(event.get("message", ""), max_chars=1000),
        "count": event.get("count"),
        "firstTimestamp": event.get("firstTimestamp") or event.get("eventTime"),
        "lastTimestamp": event.get("lastTimestamp") or event.get("eventTime"),
        "involvedObject": {
            "kind": involved.get("kind"),
            "namespace": involved.get("namespace"),
            "name": involved.get("name"),
        },
    }


def events_for(events: Iterable[Dict[str, Any]], namespace: str, name: str, uid: Optional[str] = None) -> List[Dict[str, Any]]:
    matched = []
    for event in events:
        involved = event.get("involvedObject", {})
        if involved.get("namespace") == namespace and (involved.get("name") == name or (uid and involved.get("uid") == uid)):
            matched.append(compact_event(event))
    return matched[-10:]


def classify_from_reason(reason: str, message: str = "", logs: str = "") -> Dict[str, str]:
    combined = f"{reason} {message} {logs}".lower()
    if reason in {"ImagePullBackOff", "ErrImagePull", "InvalidImageName"}:
        return {
            "category": "image_or_registry",
            "hypothesis": "The workload cannot pull or resolve the configured container image.",
            "recommended_action": "Check image name/tag, registry access, imagePullSecrets, and recent CI/CD image publication. Consider rollback to the previous working image after approval.",
        }
    if reason == "CrashLoopBackOff":
        if re.search(r"missing|required|env|environment|config|secret|redis|database|url", combined):
            return {
                "category": "application_config",
                "hypothesis": "The container is repeatedly crashing and logs/events suggest missing or invalid application configuration.",
                "recommended_action": "Compare the latest deployment/config with the last known good release. Restore missing config through an approved patch or rollback.",
            }
        return {
            "category": "application_crash",
            "hypothesis": "The application process starts and exits repeatedly. Root cause is likely application/runtime/config related.",
            "recommended_action": "Inspect sanitized logs, recent commits, environment/config changes, and rollback if the latest release caused the crash.",
        }
    if reason == "OOMKilled":
        return {
            "category": "resource_pressure",
            "hypothesis": "The container was killed because it exceeded its memory limit or the node was under memory pressure.",
            "recommended_action": "Inspect memory limits, recent traffic/code changes, and memory metrics. Consider rollback, scaling, or resource limit adjustment after approval.",
        }
    if reason in {"CreateContainerConfigError", "CreateContainerError"}:
        if re.search(r"secret.*not found|configmap.*not found", combined):
            return {
                "category": "missing_secret_or_configmap",
                "hypothesis": "Kubernetes cannot create the container because a referenced Secret or ConfigMap is missing or invalid.",
                "recommended_action": "Restore the missing Secret/ConfigMap, fix the reference, or rollback the deployment after approval.",
            }
        return {
            "category": "container_creation_failure",
            "hypothesis": "Kubernetes cannot create the container because the pod spec or runtime configuration is invalid.",
            "recommended_action": "Review recent manifest changes, env refs, volume mounts, image command/args, and events. Apply a scoped config fix or rollback after approval.",
        }
    if reason == "Pending":
        return {
            "category": "scheduling_or_capacity",
            "hypothesis": "The pod is pending, often due to image pull, scheduling constraints, insufficient resources, node selectors, taints, or PVC issues.",
            "recommended_action": "Inspect waiting reason, image status, scheduling events, resource requests, node capacity, tolerations, affinity, and PVC state.",
        }
    if reason == "ReadinessProbeFailed":
        return {
            "category": "readiness_probe_failure",
            "hypothesis": "The pod is running but not becoming ready because readiness checks are failing.",
            "recommended_action": "Check application health endpoint, service dependencies, probe path/port, startup time, and recent deployment changes.",
        }
    if reason == "ServiceNoEndpoints":
        return {
            "category": "networking_or_selector",
            "hypothesis": "A Kubernetes Service has no ready endpoints, usually due to selector mismatch or all matching pods being unready.",
            "recommended_action": "Compare Service selector labels with pod labels and check readiness of matching pods. Patch selector/labels only after approval.",
        }
    if reason == "DeploymentUnavailable":
        return {
            "category": "rollout_failure",
            "hypothesis": "A Deployment has unavailable replicas or is not progressing successfully.",
            "recommended_action": "Inspect rollout status, ReplicaSet events, pod failures, and recent deployment changes. Consider rollback after approval.",
        }
    return {
        "category": "unknown_kubernetes_failure",
        "hypothesis": "SafeOps found an abnormal Kubernetes state, but the exact root cause requires more evidence.",
        "recommended_action": "Collect related events, logs, rollout history, and recent CI/CD changes before applying remediation.",
    }


def severity_for(reason: str, namespace: str = "") -> str:
    if reason in {"CrashLoopBackOff", "OOMKilled", "DeploymentUnavailable"}:
        return "high" if namespace in {"prod", "production"} else "medium"
    if reason in {"ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError", "CreateContainerError"}:
        return "medium"
    if reason in {"ServiceNoEndpoints", "ReadinessProbeFailed"}:
        return "medium"
    return "low"


def prevention_ideas_for(category: str) -> List[str]:
    mapping = {
        "image_or_registry": [
            "Add CI gate to verify image tag exists before deployment.",
            "Require immutable image tags or digest pinning for production.",
            "Validate imagePullSecrets and registry access during preflight checks.",
        ],
        "application_config": [
            "Add required environment variable validation to CI/CD.",
            "Add startup config checks with clear error messages.",
            "Add manifest diff guardrail for required env/config keys.",
        ],
        "missing_secret_or_configmap": [
            "Add pre-deployment check for referenced Secrets and ConfigMaps.",
            "Manage config dependencies with GitOps or sealed-secret workflow.",
        ],
        "resource_pressure": [
            "Add memory SLO and OOMKilled alerting.",
            "Review resource requests/limits and load tests before release.",
        ],
        "readiness_probe_failure": [
            "Validate readiness path/port in CI or staging.",
            "Tune startup/readiness timing for slow-starting services.",
        ],
        "networking_or_selector": [
            "Add CI check comparing Service selectors with Deployment pod labels.",
            "Add endpoint availability alert after deployment.",
        ],
        "rollout_failure": [
            "Enable progressive delivery/canary checks.",
            "Fail deployment automatically when rollout exceeds progress deadline.",
        ],
    }
    return mapping.get(category, ["Add this incident signature to the SafeOps pattern library after engineer review."])


def detect_pod_incidents(
    pods: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    context: Optional[str],
    include_logs: bool,
    logs_tail: int,
) -> List[Dict[str, Any]]:
    incidents: List[Dict[str, Any]] = []
    for pod in pods:
        # Deleting pods usually represent rollout cleanup. Ignore them unless a future
        # detector adds explicit stuck-terminating logic with age thresholds.
        if meta(pod, "deletionTimestamp"):
            continue

        namespace = meta(pod, "namespace", "default")
        pod_name = meta(pod, "name", "unknown")
        pod_uid = meta(pod, "uid")
        phase = pod.get("status", {}).get("phase", "Unknown")
        is_ready = pod_ready(pod)
        pod_events = events_for(events, namespace, pod_name, pod_uid)

        containers = (pod.get("status", {}).get("initContainerStatuses") or []) + (pod.get("status", {}).get("containerStatuses") or [])
        spec_containers = pod.get("spec", {}).get("containers", []) or []
        env_summary = [safe_env_summary(c) for c in spec_containers]

        reasons: List[Tuple[str, str, Optional[str], int]] = []
        if phase == "Pending":
            reasons.append(("Pending", "Pod is pending and not scheduled/running yet.", None, 0))
        if phase == "Failed":
            reasons.append(("PodFailed", pod.get("status", {}).get("message", "Pod phase is Failed."), None, 0))

        for status in containers:
            cname = status.get("name")
            restart_count = int(status.get("restartCount") or 0)
            state = status.get("state") or {}
            last_state = status.get("lastState") or {}

            if "waiting" in state:
                waiting = state["waiting"] or {}
                reason = waiting.get("reason") or "Waiting"
                message = waiting.get("message") or ""
                if reason in ABNORMAL_WAITING_REASONS or (not is_ready and restart_count >= 3):
                    reasons.append((reason, message, cname, restart_count))

            if "terminated" in last_state:
                terminated = last_state["terminated"] or {}
                reason = terminated.get("reason") or "Terminated"
                exit_code = terminated.get("exitCode")
                message = terminated.get("message") or ""
                # lastState can be historical after a recovered pod or VM reboot.
                # Only treat it as an active incident when the pod is not Ready.
                if not is_ready and (reason == "OOMKilled" or (exit_code not in (None, 0) and restart_count >= 1)):
                    reasons.append((reason, message or f"Previous container exit code: {exit_code}", cname, restart_count))

            # High restart count alone is a warning, not an active incident,
            # if Kubernetes currently reports the pod as Ready.
            if not is_ready and restart_count >= 5 and not any(r[2] == cname for r in reasons):
                reasons.append(("HighRestartCount", f"Container restart count is {restart_count}.", cname, restart_count))

        # Readiness probe events can remain after a pod has recovered.
        # Only treat them as active incidents when the pod is currently not Ready.
        event_text = "\n".join((e.get("message") or "") for e in pod_events)
        if not is_ready and re.search(r"readiness probe failed", event_text, flags=re.I):
            reasons.append(("ReadinessProbeFailed", "Current pod readiness is false and events show readiness probe failures.", None, 0))

        seen = set()
        for reason, message, container_name, restart_count in reasons:
            key = (namespace, pod_name, reason, container_name)
            if key in seen:
                continue
            seen.add(key)

            logs = ""
            if include_logs and container_name:
                logs = kubectl_text(
                    ["-n", namespace, "logs", pod_name, "-c", container_name, "--tail", str(logs_tail), "--previous"],
                    context=context,
                    timeout=15,
                )
                if logs.startswith("kubectl_error"):
                    logs = kubectl_text(
                        ["-n", namespace, "logs", pod_name, "-c", container_name, "--tail", str(logs_tail)],
                        context=context,
                        timeout=15,
                    )
                logs = sanitize_text(logs)

            classification = classify_from_reason(reason, message, logs)
            incident = {
                "finding_id": f"finding_{namespace}_{pod_name}_{reason}_{len(incidents)+1}",
                "detected_at": now_iso(),
                "source": "kubernetes",
                "kind": "Pod",
                "namespace": namespace,
                "name": pod_name,
                "group_resource": grouping_resource_for_pod(pod),
                "owner": pod_owner(pod),
                "severity": severity_for(reason, namespace),
                "reason": reason,
                "message": sanitize_text(message, max_chars=1500),
                "category": classification["category"],
                "root_cause_hypothesis": classification["hypothesis"],
                "recommended_safe_action": classification["recommended_action"],
                "approval_required": True,
                "execute_allowed_by_detector": False,
                "evidence": {
                    "pod_phase": phase,
                    "pod_ready": is_ready,
                    "container": container_name,
                    "restart_count": restart_count,
                    "pod_ip": pod.get("status", {}).get("podIP"),
                    "node_name": pod.get("spec", {}).get("nodeName"),
                    "container_env_summary_no_values": env_summary,
                    "high_signal_events": [e for e in pod_events if event_is_high_signal({"reason": e.get("reason"), "message": e.get("message")})] or pod_events[-5:],
                    "sanitized_logs_tail": logs,
                },
                "verification_plan": [
                    "kubectl rollout status for the owner deployment when available",
                    "pod Ready condition is true",
                    "restart count stops increasing",
                    "health endpoint and telemetry recover if configured",
                ],
                "prevention_ideas": prevention_ideas_for(classification["category"]),
            }
            incidents.append(incident)
    return incidents


def grouping_resource_for_pod(pod: Dict[str, Any]) -> str:
    owner = pod_owner(pod)
    if owner.get("inferred_deployment"):
        return owner["inferred_deployment"]
    if owner.get("kind") == "Deployment":
        return owner.get("name", meta(pod, "name", "unknown"))
    if owner.get("kind") in {"ReplicaSet", "StatefulSet", "DaemonSet", "Job"}:
        return owner.get("name", meta(pod, "name", "unknown"))
    return meta(pod, "name", "unknown")


def detect_deployment_incidents(deployments: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    incidents: List[Dict[str, Any]] = []
    for dep in deployments:
        namespace = meta(dep, "namespace", "default")
        name = meta(dep, "name", "unknown")
        status = dep.get("status", {}) or {}
        spec = dep.get("spec", {}) or {}
        desired = spec.get("replicas", 1)
        unavailable = status.get("unavailableReplicas", 0) or 0
        updated = status.get("updatedReplicas", 0) or 0
        available = status.get("availableReplicas", 0) or 0
        conditions = status.get("conditions", []) or []
        progressing_bad = any(c.get("type") == "Progressing" and c.get("status") == "False" for c in conditions)
        available_bad = desired and available < desired
        if unavailable > 0 or progressing_bad or available_bad:
            msg = "; ".join(
                f"{c.get('type')}={c.get('status')} {c.get('reason') or ''} {c.get('message') or ''}" for c in conditions
            )
            classification = classify_from_reason("DeploymentUnavailable", msg)
            incidents.append(
                {
                    "finding_id": f"finding_{namespace}_{name}_DeploymentUnavailable_{len(incidents)+1}",
                    "detected_at": now_iso(),
                    "source": "kubernetes",
                    "kind": "Deployment",
                    "namespace": namespace,
                    "name": name,
                    "group_resource": name,
                    "severity": severity_for("DeploymentUnavailable", namespace),
                    "reason": "DeploymentUnavailable",
                    "message": sanitize_text(msg or "Deployment has unavailable replicas or failed conditions.", 2000),
                    "category": classification["category"],
                    "root_cause_hypothesis": classification["hypothesis"],
                    "recommended_safe_action": classification["recommended_action"],
                    "approval_required": True,
                    "execute_allowed_by_detector": False,
                    "evidence": {
                        "desired_replicas": desired,
                        "updated_replicas": updated,
                        "available_replicas": available,
                        "unavailable_replicas": unavailable,
                        "conditions": conditions,
                        "high_signal_events": events_for(events, namespace, name)[-5:],
                    },
                    "verification_plan": [
                        f"kubectl -n {namespace} rollout status deployment/{name}",
                        "desired replicas equal available replicas",
                        "related pods become Ready",
                    ],
                    "prevention_ideas": prevention_ideas_for(classification["category"]),
                }
            )
    return incidents


def detect_service_endpoint_incidents(services: List[Dict[str, Any]], endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    incidents: List[Dict[str, Any]] = []
    endpoint_index = {(meta(ep, "namespace", "default"), meta(ep, "name", "unknown")): ep for ep in endpoints}
    for svc in services:
        namespace = meta(svc, "namespace", "default")
        name = meta(svc, "name", "unknown")
        spec = svc.get("spec", {}) or {}
        if spec.get("type") == "ExternalName" or not spec.get("selector"):
            continue
        ep = endpoint_index.get((namespace, name), {})
        subsets = ep.get("subsets") or []
        ready_addresses = sum(len(s.get("addresses") or []) for s in subsets)
        not_ready = sum(len(s.get("notReadyAddresses") or []) for s in subsets)
        if ready_addresses == 0:
            classification = classify_from_reason("ServiceNoEndpoints")
            incidents.append(
                {
                    "finding_id": f"finding_{namespace}_{name}_ServiceNoEndpoints_{len(incidents)+1}",
                    "detected_at": now_iso(),
                    "source": "kubernetes",
                    "kind": "Service",
                    "namespace": namespace,
                    "name": name,
                    "group_resource": name,
                    "severity": severity_for("ServiceNoEndpoints", namespace),
                    "reason": "ServiceNoEndpoints",
                    "message": "Service has selectors but no ready endpoints.",
                    "category": classification["category"],
                    "root_cause_hypothesis": classification["hypothesis"],
                    "recommended_safe_action": classification["recommended_action"],
                    "approval_required": True,
                    "execute_allowed_by_detector": False,
                    "evidence": {
                        "service_selector": spec.get("selector"),
                        "ports": spec.get("ports"),
                        "ready_endpoint_count": ready_addresses,
                        "not_ready_endpoint_count": not_ready,
                    },
                    "verification_plan": [
                        f"kubectl -n {namespace} get endpoints {name}",
                        "Service has at least one ready endpoint",
                        "application health check succeeds through Service/Ingress",
                    ],
                    "prevention_ideas": prevention_ideas_for(classification["category"]),
                }
            )
    return incidents


def choose_primary_category(findings: List[Dict[str, Any]]) -> str:
    categories = {f.get("category") for f in findings}
    priority = [
        "image_or_registry",
        "missing_secret_or_configmap",
        "application_config",
        "application_crash",
        "resource_pressure",
        "readiness_probe_failure",
        "networking_or_selector",
        "rollout_failure",
        "scheduling_or_capacity",
    ]
    for category in priority:
        if category in categories:
            return category
    return sorted(c for c in categories if c)[0] if categories else "unknown_kubernetes_failure"


def root_incident_profile(category: str, resource: str) -> Dict[str, Any]:
    profiles = {
        "image_or_registry": {
            "title": "Image pull failure / bad image or registry access",
            "root_cause_hypothesis": f"{resource} is failing rollout because Kubernetes cannot pull or resolve the configured container image. This is commonly caused by a bad tag, unpublished image, registry auth problem, or imagePullSecret issue.",
            "recommended_safe_action": "Rollback to the previous working image or restore a known-good image tag after approval. Also verify the CI/CD image build and registry push completed successfully.",
            "safe_action_options": [
                "Inspect latest deployment image and CI/CD image publication result.",
                "Rollback deployment to previous revision after approval.",
                "Set deployment image back to last known-good tag after approval.",
                "Validate imagePullSecrets and registry access before retrying rollout.",
            ],
        },
        "missing_secret_or_configmap": {
            "title": "Missing Secret or ConfigMap dependency",
            "root_cause_hypothesis": f"{resource} cannot start because the pod spec references a Secret or ConfigMap that is missing or invalid.",
            "recommended_safe_action": "Restore the missing Secret/ConfigMap or rollback the deployment after approval. Do not expose secret values in logs or prompts.",
            "safe_action_options": [
                "Confirm referenced Secret/ConfigMap exists in the same namespace.",
                "Rollback the deployment after approval if the latest manifest introduced the bad reference.",
                "Restore the missing config object through the approved secret/config workflow.",
            ],
        },
        "application_config": {
            "title": "Application configuration crash",
            "root_cause_hypothesis": f"{resource} is crashing and evidence suggests missing or invalid runtime configuration such as env vars, URLs, feature flags, or dependency settings.",
            "recommended_safe_action": "Compare latest deployment/config with the previous working version. Restore missing config or rollback after approval.",
            "safe_action_options": [
                "Inspect sanitized logs and environment key names, not values.",
                "Compare deployment manifest against last known-good release.",
                "Restore missing config via approved patch or rollback after approval.",
            ],
        },
        "application_crash": {
            "title": "Application runtime crash",
            "root_cause_hypothesis": f"{resource} starts and exits repeatedly. The cause may be application code, dependency initialization, command/args, or runtime config.",
            "recommended_safe_action": "Inspect sanitized logs and recent commits. Roll back if the latest release introduced the crash.",
            "safe_action_options": [
                "Inspect previous and current logs.",
                "Check recent commits and deployment timing.",
                "Rollback to previous stable revision after approval.",
            ],
        },
        "resource_pressure": {
            "title": "Resource pressure / OOMKilled",
            "root_cause_hypothesis": f"{resource} is failing because one or more containers exceeded memory limits or experienced node resource pressure.",
            "recommended_safe_action": "Review memory metrics and recent traffic/code changes. Consider rollback, scaling, or resource limit adjustment after approval.",
            "safe_action_options": [
                "Check memory usage trend and restart timing.",
                "Rollback if memory spike started after release.",
                "Scale or adjust resource limits only after approval and blast-radius review.",
            ],
        },
        "readiness_probe_failure": {
            "title": "Readiness probe failure",
            "root_cause_hypothesis": f"{resource} is running but not becoming ready. The health endpoint, port/path, startup timing, or service dependency may be unhealthy.",
            "recommended_safe_action": "Inspect health endpoint, probe config, startup time, and dependencies. Rollback if the probe failure started after the latest deployment.",
            "safe_action_options": [
                "Check readiness probe path, port, initialDelaySeconds, and timeoutSeconds.",
                "Check dependency health and startup time.",
                "Rollback after approval if latest release caused the readiness failure.",
            ],
        },
        "networking_or_selector": {
            "title": "Service routing / endpoint failure",
            "root_cause_hypothesis": f"{resource} has routing or endpoint issues. The Service selector may not match pod labels, or all selected pods are unready.",
            "recommended_safe_action": "Compare Service selectors to Deployment labels. Patch labels/selectors only after approval and verification plan.",
            "safe_action_options": [
                "Compare Service selector labels with pod template labels.",
                "Check endpoints and notReadyAddresses.",
                "Patch selector/labels only after approval.",
            ],
        },
        "rollout_failure": {
            "title": "Deployment rollout failure",
            "root_cause_hypothesis": f"{resource} is not reaching desired availability. Related pod failures, image errors, config issues, or probe failures may be blocking rollout.",
            "recommended_safe_action": "Inspect related pods and events. Rollback after approval if the latest deployment is unhealthy.",
            "safe_action_options": [
                "Check rollout status and ReplicaSet events.",
                "Identify newest ReplicaSet pod failures.",
                "Rollback to previous revision after approval.",
            ],
        },
        "scheduling_or_capacity": {
            "title": "Scheduling or capacity issue",
            "root_cause_hypothesis": f"{resource} has pods that are pending. Causes may include image pull failure, resource pressure, node selectors, taints, affinity, or PVC binding.",
            "recommended_safe_action": "Inspect scheduling events, node capacity, resource requests, PVCs, and image waiting reason before remediation.",
            "safe_action_options": [
                "Check pod events for FailedScheduling or image pull messages.",
                "Review node capacity, PVCs, tolerations, and affinity.",
                "Scale or adjust placement only after approval.",
            ],
        },
    }
    return profiles.get(category, {
        "title": "Unknown Kubernetes failure",
        "root_cause_hypothesis": f"{resource} has abnormal Kubernetes symptoms, but SafeOps needs more evidence before choosing a root cause.",
        "recommended_safe_action": "Collect more logs, events, rollout history, and CI/CD context before remediation.",
        "safe_action_options": ["Collect more evidence", "Ask engineer to classify", "Add this pattern to the scenario library"],
    })


def merge_unique(items: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def highest_severity(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "low"
    return max((f.get("severity", "low") for f in findings), key=lambda s: SEVERITY_RANK.get(s, 0))


def group_key(finding: Dict[str, Any]) -> Tuple[str, str]:
    return finding.get("namespace", "default"), finding.get("group_resource") or finding.get("name", "unknown")


def evidence_chain_for(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    chain = []
    for f in findings:
        ev = f.get("evidence", {}) or {}
        item = {
            "kind": f.get("kind"),
            "namespace": f.get("namespace"),
            "name": f.get("name"),
            "reason": f.get("reason"),
            "category": f.get("category"),
            "message": f.get("message"),
        }
        if f.get("kind") == "Deployment":
            item["deployment_status"] = {
                "desired_replicas": ev.get("desired_replicas"),
                "updated_replicas": ev.get("updated_replicas"),
                "available_replicas": ev.get("available_replicas"),
                "unavailable_replicas": ev.get("unavailable_replicas"),
            }
        if f.get("kind") == "Pod":
            item["pod_status"] = {
                "phase": ev.get("pod_phase"),
                "ready": ev.get("pod_ready"),
                "container": ev.get("container"),
                "restart_count": ev.get("restart_count"),
                "node_name": ev.get("node_name"),
            }
            if ev.get("container_env_summary_no_values"):
                item["container_summary_no_secret_values"] = ev.get("container_env_summary_no_values")
        if f.get("kind") == "Service":
            item["service_status"] = {
                "selector": ev.get("service_selector"),
                "ready_endpoint_count": ev.get("ready_endpoint_count"),
                "not_ready_endpoint_count": ev.get("not_ready_endpoint_count"),
            }
        events = ev.get("high_signal_events") or []
        if events:
            item["events"] = events[:5]
        logs = ev.get("sanitized_logs_tail")
        if logs:
            item["sanitized_logs_tail"] = logs[-2000:]
        chain.append(item)
    return chain


def group_related_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for finding in findings:
        grouped.setdefault(group_key(finding), []).append(finding)

    roots: List[Dict[str, Any]] = []
    for index, ((namespace, resource), group_findings) in enumerate(grouped.items(), start=1):
        # Sort details so causal pod errors appear before rollout symptoms when possible.
        group_findings.sort(key=lambda f: (
            0 if f.get("category") == "image_or_registry" else 1 if f.get("kind") == "Pod" else 2,
            f.get("kind", ""),
            f.get("name", ""),
        ))
        primary_category = choose_primary_category(group_findings)
        profile = root_incident_profile(primary_category, resource)
        reasons = merge_unique(f.get("reason", "") for f in group_findings)
        categories = merge_unique(f.get("category", "") for f in group_findings)
        affected_resources = [
            {
                "kind": f.get("kind"),
                "namespace": f.get("namespace"),
                "name": f.get("name"),
                "reason": f.get("reason"),
                "category": f.get("category"),
            }
            for f in group_findings
        ]
        verification_plan = merge_unique(step for f in group_findings for step in f.get("verification_plan", []))
        prevention_ideas = merge_unique(idea for f in group_findings for idea in f.get("prevention_ideas", []))
        root = {
            "incident_id": f"root_{namespace}_{resource}_{primary_category}_{index}",
            "detected_at": now_iso(),
            "source": "kubernetes",
            "namespace": namespace,
            "affected_workload": resource,
            "severity": highest_severity(group_findings),
            "title": profile["title"],
            "primary_category": primary_category,
            "all_categories": categories,
            "reasons": reasons,
            "root_cause_hypothesis": profile["root_cause_hypothesis"],
            "recommended_safe_action": profile["recommended_safe_action"],
            "safe_action_options": profile["safe_action_options"],
            "approval_required": True,
            "execute_allowed_by_detector": False,
            "blast_radius_estimate": {
                "namespace": namespace,
                "primary_workload": resource,
                "scope": "single Kubernetes workload/service group unless dependency evidence says otherwise",
            },
            "verification_plan": verification_plan or [
                f"kubectl -n {namespace} rollout status deployment/{resource}",
                "related pods become Ready",
                "alerts and error rate recover if observability is connected",
            ],
            "prevention_ideas": prevention_ideas,
            "evidence_pack": {
                "raw_finding_count": len(group_findings),
                "affected_resources": affected_resources,
                "evidence_chain": evidence_chain_for(group_findings),
                "human_note": "Grouped root incident created from multiple Kubernetes symptoms to reduce alert noise and preserve evidence.",
            },
        }
        roots.append(root)
    roots.sort(key=lambda r: (SEVERITY_SORT.get(r.get("severity", "low"), 9), r.get("namespace", ""), r.get("affected_workload", "")))
    return roots


def load_cluster_state(namespace: str, context: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    nsa = ns_args(namespace)
    state: Dict[str, List[Dict[str, Any]]] = {}
    for label, resource in [
        ("pods", "pods"),
        ("deployments", "deployments"),
        ("services", "services"),
        ("endpoints", "endpoints"),
        ("events", "events"),
    ]:
        try:
            data = kubectl_json(["get", resource] + nsa, context=context)
            state[label] = data.get("items", []) or []
        except RuntimeError as exc:
            state[label] = []
            print(f"warning: could not read {resource}: {exc}", file=sys.stderr)
    return state


def summarize(root_incidents: List[Dict[str, Any]], raw_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_severity: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    by_namespace: Dict[str, int] = {}
    for inc in root_incidents:
        by_severity[inc["severity"]] = by_severity.get(inc["severity"], 0) + 1
        by_category[inc["primary_category"]] = by_category.get(inc["primary_category"], 0) + 1
        by_namespace[inc["namespace"]] = by_namespace.get(inc["namespace"], 0) + 1
    raw_by_kind: Dict[str, int] = {}
    for f in raw_findings:
        raw_by_kind[f["kind"]] = raw_by_kind.get(f["kind"], 0) + 1
    return {
        "total_incidents": len(root_incidents),
        "root_incidents": len(root_incidents),
        "raw_findings": len(raw_findings),
        "by_severity": by_severity,
        "by_category": by_category,
        "by_namespace": by_namespace,
        "raw_findings_by_kind": raw_by_kind,
    }


def markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# SafeOps Real Kubernetes Incident Evidence Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Namespace scope: `{report['namespace_scope']}`",
        f"Kube context: `{report.get('kube_context') or 'current'}`",
        "Mode: `read_only_detection_with_grouped_evidence_pack`",
        "",
        "## Summary",
        "",
        f"Root incidents detected: **{report['summary']['root_incidents']}**",
        f"Raw Kubernetes findings grouped: **{report['summary']['raw_findings']}**",
        "",
        f"By severity: `{json.dumps(report['summary']['by_severity'], sort_keys=True)}`",
        f"By category: `{json.dumps(report['summary']['by_category'], sort_keys=True)}`",
        "",
    ]
    if not report["root_incidents"]:
        lines += ["No active abnormal Kubernetes incidents detected in this scan.", ""]
        return "\n".join(lines)

    lines += ["## Grouped Root Incidents", ""]
    for inc in report["root_incidents"]:
        lines += [
            f"### {inc['severity'].upper()} · {inc['title']} · {inc['namespace']}/{inc['affected_workload']}",
            "",
            f"- Incident ID: `{inc['incident_id']}`",
            f"- Primary category: `{inc['primary_category']}`",
            f"- Grouped reasons: `{', '.join(inc.get('reasons', []))}`",
            f"- Raw findings grouped: `{inc['evidence_pack']['raw_finding_count']}`",
            f"- Root-cause hypothesis: {inc['root_cause_hypothesis']}",
            f"- Recommended safe action: {inc['recommended_safe_action']}",
            f"- Approval required: `{inc['approval_required']}`",
            f"- Detector can execute action: `{inc['execute_allowed_by_detector']}`",
            "",
            "#### Safe action options",
        ]
        for option in inc.get("safe_action_options", []):
            lines.append(f"- {option}")
        lines += ["", "#### Evidence chain"]
        for item in inc.get("evidence_pack", {}).get("evidence_chain", []):
            lines.append(f"- `{item.get('kind')}` `{item.get('namespace')}/{item.get('name')}` reason=`{item.get('reason')}` category=`{item.get('category')}`")
            msg = item.get("message")
            if msg:
                lines.append(f"  - message: {msg}")
            dep = item.get("deployment_status")
            if dep:
                lines.append(f"  - deployment status: `{json.dumps(dep, sort_keys=True)}`")
            pod = item.get("pod_status")
            if pod:
                lines.append(f"  - pod status: `{json.dumps(pod, sort_keys=True)}`")
            svc = item.get("service_status")
            if svc:
                lines.append(f"  - service status: `{json.dumps(svc, sort_keys=True)}`")
            events = item.get("events") or []
            for event in events[:3]:
                lines.append(f"  - event `{event.get('reason')}`: {event.get('message')}")
            logs = item.get("sanitized_logs_tail")
            if logs:
                lines += ["", "  Sanitized logs tail:", "", "  ```text"]
                lines += ["  " + line for line in logs[-2000:].splitlines()]
                lines.append("  ```")
        lines += ["", "#### Verification plan"]
        for step in inc.get("verification_plan", []):
            lines.append(f"- {step}")
        lines += ["", "#### Prevention ideas"]
        for idea in inc.get("prevention_ideas", []):
            lines.append(f"- {idea}")
        lines.append("")

    lines += [
        "## Raw Findings",
        "",
        "These are the underlying Kubernetes symptoms grouped into root incidents. They are kept for auditability and debugging.",
        "",
    ]
    for f in report.get("raw_findings", []):
        lines.append(f"- `{f['severity']}` `{f['kind']}` `{f['namespace']}/{f['name']}` reason=`{f['reason']}` category=`{f['category']}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect and group real Kubernetes incidents with read-only kubectl evidence collection.")
    parser.add_argument("-n", "--namespace", default="all", help="Namespace to scan, or 'all' for all namespaces. Default: all")
    parser.add_argument("--context", default=None, help="Optional kube context.")
    parser.add_argument("--out", default="/tmp/safeops-demo/real-k8s-incidents.json", help="JSON output path.")
    parser.add_argument("--human-report", default="/tmp/safeops-demo/real-k8s-incidents.md", help="Markdown report output path.")
    parser.add_argument("--include-logs", action="store_true", help="Include sanitized pod logs tail for failed containers.")
    parser.add_argument("--logs-tail", type=int, default=80, help="Number of log lines to read when --include-logs is set.")
    args = parser.parse_args()

    code, out, err = run_cmd(["kubectl", "version", "--client"], timeout=10)
    if code != 0:
        print("kubectl is required but not available.", file=sys.stderr)
        print(err, file=sys.stderr)
        return 2

    try:
        state = load_cluster_state(args.namespace, args.context)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    raw_findings: List[Dict[str, Any]] = []
    raw_findings.extend(
        detect_pod_incidents(
            state.get("pods", []),
            state.get("events", []),
            context=args.context,
            include_logs=args.include_logs,
            logs_tail=args.logs_tail,
        )
    )
    raw_findings.extend(detect_deployment_incidents(state.get("deployments", []), state.get("events", [])))
    raw_findings.extend(detect_service_endpoint_incidents(state.get("services", []), state.get("endpoints", [])))

    raw_findings.sort(key=lambda i: (SEVERITY_SORT.get(i.get("severity", "low"), 9), i.get("namespace", ""), i.get("name", "")))
    root_incidents = group_related_findings(raw_findings)

    report = {
        "schema_version": "safeops.real_k8s_incident_report.v2",
        "generated_at": now_iso(),
        "namespace_scope": args.namespace,
        "kube_context": args.context,
        "mode": "read_only_detection_with_grouped_evidence_pack",
        "cluster_snapshot_counts": {k: len(v) for k, v in state.items()},
        "summary": summarize(root_incidents, raw_findings),
        "root_incidents": root_incidents,
        "raw_findings": raw_findings,
        "safety_note": "This detector is read-only. It does not execute remediation actions. All recommended actions require policy validation and human approval before execution.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True))

    md_path = Path(args.human_report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_report(report))

    print("SafeOps real Kubernetes incident scan complete.")
    print(f"Root incidents detected: {report['summary']['root_incidents']}")
    print(f"Raw findings grouped: {report['summary']['raw_findings']}")
    print(f"JSON report: {out_path}")
    print(f"Markdown report: {md_path}")
    if root_incidents:
        print("Top root incidents:")
        for inc in root_incidents[:10]:
            print(
                f"- {inc['severity'].upper()} {inc['namespace']}/{inc['affected_workload']} "
                f"title={inc['title']} category={inc['primary_category']} raw_findings={inc['evidence_pack']['raw_finding_count']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
