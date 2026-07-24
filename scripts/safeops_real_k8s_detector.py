#!/usr/bin/env python3
"""SafeOps real Kubernetes incident detector.

Read-only detector for real Kubernetes clusters. It inspects live cluster state,
classifies common workload/release failures, collects sanitized evidence, and
writes JSON + Markdown reports that can be reviewed by engineers.

No production changes are made by this script.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
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
            # Redact anything that looks like key=value on a sensitive line.
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
        return {"kind": "Pod", "name": meta(pod, "name", "unknown")}
    owner = owners[0]
    owner_kind = owner.get("kind", "Unknown")
    owner_name = owner.get("name", "unknown")
    inferred_deployment = None
    if owner_kind == "ReplicaSet":
        # Deployment-managed ReplicaSets usually end in a generated hash.
        inferred_deployment = re.sub(r"-[a-f0-9]{8,10}$", "", owner_name)
    return {
        "kind": owner_kind,
        "name": owner_name,
        "inferred_deployment": inferred_deployment or "",
    }


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
            "hypothesis": "The pod is pending, often due to scheduling constraints, insufficient resources, node selectors, taints, or PVC issues.",
            "recommended_action": "Inspect scheduling events, resource requests, node capacity, tolerations, affinity, and PVC state.",
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


def detect_pod_incidents(
    pods: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    context: Optional[str],
    include_logs: bool,
    logs_tail: int,
) -> List[Dict[str, Any]]:
    incidents: List[Dict[str, Any]] = []
    for pod in pods:
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
                if reason in ABNORMAL_WAITING_REASONS or restart_count >= 3:
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
                "incident_id": f"real_{namespace}_{pod_name}_{reason}_{len(incidents)+1}",
                "detected_at": now_iso(),
                "source": "kubernetes",
                "kind": "Pod",
                "namespace": namespace,
                "name": pod_name,
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
        progressing_bad = any(
            c.get("type") == "Progressing" and c.get("status") == "False" for c in conditions
        )
        available_bad = desired and available < desired
        if unavailable > 0 or progressing_bad or available_bad:
            msg = "; ".join(
                f"{c.get('type')}={c.get('status')} {c.get('reason') or ''} {c.get('message') or ''}" for c in conditions
            )
            classification = classify_from_reason("DeploymentUnavailable", msg)
            incidents.append(
                {
                    "incident_id": f"real_{namespace}_{name}_DeploymentUnavailable_{len(incidents)+1}",
                    "detected_at": now_iso(),
                    "source": "kubernetes",
                    "kind": "Deployment",
                    "namespace": namespace,
                    "name": name,
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
                    "incident_id": f"real_{namespace}_{name}_ServiceNoEndpoints_{len(incidents)+1}",
                    "detected_at": now_iso(),
                    "source": "kubernetes",
                    "kind": "Service",
                    "namespace": namespace,
                    "name": name,
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


def summarize(incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_severity: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    by_kind: Dict[str, int] = {}
    for inc in incidents:
        by_severity[inc["severity"]] = by_severity.get(inc["severity"], 0) + 1
        by_category[inc["category"]] = by_category.get(inc["category"], 0) + 1
        by_kind[inc["kind"]] = by_kind.get(inc["kind"], 0) + 1
    return {
        "total_incidents": len(incidents),
        "by_severity": by_severity,
        "by_category": by_category,
        "by_kind": by_kind,
    }


def markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# SafeOps Real Kubernetes Incident Detection Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Namespace scope: `{report['namespace_scope']}`",
        f"Kube context: `{report.get('kube_context') or 'current'}`",
        "",
        "## Summary",
        "",
        f"Total incidents detected: **{report['summary']['total_incidents']}**",
        "",
        f"By severity: `{json.dumps(report['summary']['by_severity'], sort_keys=True)}`",
        f"By category: `{json.dumps(report['summary']['by_category'], sort_keys=True)}`",
        "",
    ]
    if not report["incidents"]:
        lines += ["No abnormal Kubernetes incidents detected in this scan.", ""]
        return "\n".join(lines)

    lines += ["## Incidents", ""]
    for inc in report["incidents"]:
        lines += [
            f"### {inc['severity'].upper()} · {inc['kind']} · {inc['namespace']}/{inc['name']}",
            "",
            f"- Reason: `{inc['reason']}`",
            f"- Category: `{inc['category']}`",
            f"- Hypothesis: {inc['root_cause_hypothesis']}",
            f"- Recommended safe action: {inc['recommended_safe_action']}",
            f"- Approval required: `{inc['approval_required']}`",
            "- Verification plan:",
        ]
        for step in inc.get("verification_plan", []):
            lines.append(f"  - {step}")
        lines += ["- Prevention ideas:"]
        for idea in inc.get("prevention_ideas", []):
            lines.append(f"  - {idea}")
        events = inc.get("evidence", {}).get("high_signal_events", [])
        if events:
            lines += ["- Evidence events:"]
            for event in events[:5]:
                lines.append(f"  - `{event.get('reason')}`: {event.get('message')}")
        logs = inc.get("evidence", {}).get("sanitized_logs_tail")
        if logs:
            lines += ["", "Sanitized logs tail:", "", "```text", logs[-2000:], "```"]
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect real Kubernetes incidents with read-only kubectl evidence collection.")
    parser.add_argument("-n", "--namespace", default="all", help="Namespace to scan, or 'all' for all namespaces. Default: all")
    parser.add_argument("--context", default=None, help="Optional kube context.")
    parser.add_argument("--out", default="/tmp/safeops-demo/real-k8s-incidents.json", help="JSON output path.")
    parser.add_argument("--human-report", default="/tmp/safeops-demo/real-k8s-incidents.md", help="Markdown report output path.")
    parser.add_argument("--include-logs", action="store_true", help="Include sanitized pod logs tail for failed containers.")
    parser.add_argument("--logs-tail", type=int, default=80, help="Number of log lines to read when --include-logs is set.")
    args = parser.parse_args()

    # Quick dependency check.
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

    incidents: List[Dict[str, Any]] = []
    incidents.extend(
        detect_pod_incidents(
            state.get("pods", []),
            state.get("events", []),
            context=args.context,
            include_logs=args.include_logs,
            logs_tail=args.logs_tail,
        )
    )
    incidents.extend(detect_deployment_incidents(state.get("deployments", []), state.get("events", [])))
    incidents.extend(detect_service_endpoint_incidents(state.get("services", []), state.get("endpoints", [])))

    # Highest severity first, then namespace/name for stable output.
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    incidents.sort(key=lambda i: (sev_order.get(i.get("severity", "low"), 9), i.get("namespace", ""), i.get("name", "")))

    report = {
        "schema_version": "safeops.real_k8s_incident_report.v1",
        "generated_at": now_iso(),
        "namespace_scope": args.namespace,
        "kube_context": args.context,
        "mode": "read_only_detection",
        "cluster_snapshot_counts": {k: len(v) for k, v in state.items()},
        "summary": summarize(incidents),
        "incidents": incidents,
        "safety_note": "This detector is read-only. It does not execute remediation actions. All recommended actions require policy validation and human approval before execution.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True))

    md_path = Path(args.human_report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_report(report))

    print(f"SafeOps real Kubernetes incident scan complete.")
    print(f"Incidents detected: {report['summary']['total_incidents']}")
    print(f"JSON report: {out_path}")
    print(f"Markdown report: {md_path}")
    if incidents:
        print("Top incidents:")
        for inc in incidents[:10]:
            print(f"- {inc['severity'].upper()} {inc['kind']} {inc['namespace']}/{inc['name']} reason={inc['reason']} category={inc['category']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
