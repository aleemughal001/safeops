#!/usr/bin/env python3
"""Generate approval-ready remediation plans from real Kubernetes evidence packs.

This script is intentionally read-only. It reads the grouped incident evidence
created by safeops_real_k8s_detector.py and produces JSON/Markdown remediation
plans that can later be sent through policy, human approval, and a scoped
executor.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_INPUT = "/tmp/safeops-demo/real-k8s-incidents.json"
DEFAULT_JSON_OUT = "/tmp/safeops-demo/real-k8s-remediation-plan.json"
DEFAULT_MD_OUT = "/tmp/safeops-demo/real-k8s-remediation-plan.md"


@dataclass
class ActionOption:
    action_id: str
    title: str
    action_type: str
    command_preview: str
    risk: str
    requires_approval: bool
    requires_policy_check: bool
    execution_status: str
    rationale: str
    rollback_plan: str


@dataclass
class RemediationPlan:
    plan_id: str
    incident_id: str
    title: str
    namespace: str
    resource: str
    category: str
    severity: str
    confidence: float
    blast_radius: str
    approval_required: bool
    policy_check_required: bool
    detector_can_execute: bool
    recommended_strategy: str
    action_options: List[ActionOption]
    verification_plan: List[str]
    prevention_plan: List[str]
    evidence_summary: List[str]
    safety_notes: List[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Evidence report not found: {path}")
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON evidence report: {path}: {exc}") from exc


def write_json(path: str, payload: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def value_from_any(d: Dict[str, Any], keys: Iterable[str], default: Any = "") -> Any:
    for key in keys:
        if key in d and d[key] not in (None, ""):
            return d[key]
    return default


def get_root_incidents(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in (
        "root_incidents",
        "grouped_root_incidents",
        "grouped_incidents",
        "incidents",
    ):
        value = evidence.get(key)
        if isinstance(value, list):
            return value
    return []


def stringify_resource(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        namespace = obj.get("namespace") or obj.get("ns") or ""
        name = obj.get("name") or obj.get("resource") or obj.get("deployment") or ""
        if namespace and name:
            return f"{namespace}/{name}"
        if name:
            return name
    return "unknown"


def parse_namespace_resource(incident: Dict[str, Any]) -> Tuple[str, str]:
    """Resolve namespace and deployment/resource from grouped K8s evidence.

    Grouped incidents may store the owning workload name under resource,
    group_resource, affected_service, name, raw_findings, evidence_chain,
    or only inside incident_id. The remediation plan must not generate
    deployment/unknown when the evidence already has checkout-api.
    """
    namespace = value_from_any(incident, ["namespace", "ns"], "")
    resource = value_from_any(
        incident,
        ["resource", "group_resource", "affected_service", "target", "deployment", "service", "name"],
        "",
    )

    if isinstance(resource, dict):
        resource = stringify_resource(resource)

    def try_obj(obj: Any) -> None:
        nonlocal namespace, resource
        if resource not in ("", None, "unknown"):
            return
        if not isinstance(obj, dict):
            return

        if not namespace:
            namespace = obj.get("namespace") or obj.get("ns") or namespace

        candidate = value_from_any(
            obj,
            ["group_resource", "resource", "affected_service", "target", "deployment", "service", "name"],
            "",
        )
        if isinstance(candidate, dict):
            candidate = stringify_resource(candidate)
        if candidate and candidate != "unknown":
            resource = str(candidate)

    # Direct arrays on grouped incidents.
    for key in ("affected_resources", "resources"):
        arr = incident.get(key)
        if isinstance(arr, list):
            for item in arr:
                if isinstance(item, dict) and str(item.get("kind", "")).lower() == "deployment":
                    try_obj(item)
            for item in arr:
                try_obj(item)

    # Nested raw findings/evidence entries often contain group_resource.
    for key in ("raw_findings", "findings", "grouped_findings", "evidence_chain", "evidence"):
        value = incident.get(key)
        if isinstance(value, list):
            for item in value:
                try_obj(item)
        elif isinstance(value, dict):
            try_obj(value)

    # Fallback for IDs like root_demo_checkout-api_image_or_registry_1.
    if resource in ("", None, "unknown"):
        incident_id = str(value_from_any(incident, ["incident_id", "id"], ""))
        parts = incident_id.split("_")
        if len(parts) >= 3 and parts[0] in {"root", "incident"}:
            namespace = namespace or parts[1]
            resource = parts[2]

    if isinstance(resource, str) and "/" in resource:
        left, right = resource.split("/", 1)
        namespace = namespace or left
        resource = right

    namespace = namespace or "default"
    resource = resource or "unknown"
    return namespace, resource


def normalize_deployment_name(resource: str) -> str:
    if resource.startswith("deployment/"):
        return resource.split("/", 1)[1]
    if resource.startswith("Deployment/"):
        return resource.split("/", 1)[1]
    return resource


def safe_slug(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")
    return text or "unknown"


def listify(value: Any) -> List[str]:
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(json.dumps(item, sort_keys=True))
            else:
                result.append(str(item))
        return result
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def extract_evidence_summary(incident: Dict[str, Any]) -> List[str]:
    summary: List[str] = []
    reasons = listify(incident.get("grouped_reasons") or incident.get("reasons"))
    if reasons:
        summary.append("Grouped reasons: " + ", ".join(reasons[:8]))

    chain = incident.get("evidence_chain") or incident.get("evidence") or []
    if isinstance(chain, list):
        for item in chain[:6]:
            if isinstance(item, dict):
                kind = item.get("kind") or item.get("resource_kind") or "Evidence"
                name = item.get("name") or item.get("resource") or item.get("pod") or "unknown"
                reason = item.get("reason") or item.get("category") or ""
                msg = (item.get("message") or item.get("summary") or "").replace("\n", " ")
                summary.append(f"{kind} {name} {reason}: {msg}".strip())
            else:
                summary.append(str(item))

    raw_count = value_from_any(incident, ["raw_findings_grouped", "raw_findings", "finding_count"], "")
    if raw_count:
        summary.append(f"Raw Kubernetes findings grouped: {raw_count}")

    return summary or ["Evidence pack available in source JSON report."]


def default_verification(namespace: str, deployment: str, incident: Dict[str, Any]) -> List[str]:
    existing = listify(incident.get("verification_plan"))
    base = [
        f"kubectl -n {namespace} rollout status deployment/{deployment}",
        "desired replicas equal available replicas",
        "related pods become Ready",
        "restart count stops increasing",
        "application health endpoint recovers if configured",
    ]
    seen = set()
    result = []
    for item in existing + base:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def default_prevention(category: str) -> List[str]:
    if category == "image_or_registry":
        return [
            "Add CI gate to verify image tag exists before deployment.",
            "Require immutable image tags or digest pinning for production.",
            "Validate imagePullSecrets and registry access during preflight checks.",
            "Fail deployment automatically when rollout exceeds progress deadline.",
        ]
    if category in {"config", "configuration", "environment"}:
        return [
            "Add required configuration validation before deployment.",
            "Add CI/CD gate for required environment variables and ConfigMap keys.",
            "Use schema validation for service configuration.",
        ]
    if category in {"rollout_failure", "readiness_probe_failure"}:
        return [
            "Add progressive delivery or canary checks before full rollout.",
            "Validate readiness/liveness probe path and timeout in CI or staging.",
            "Add deployment progress-deadline alert and rollback runbook.",
        ]
    return [
        "Add incident signature to SafeOps pattern library after engineer review.",
        "Add service-specific preflight check based on the verified root cause.",
    ]


def build_actions(category: str, namespace: str, deployment: str) -> List[ActionOption]:
    actions: List[ActionOption] = []

    if category == "image_or_registry":
        actions.append(
            ActionOption(
                action_id="inspect-image-publication",
                title="Inspect image build and registry publication",
                action_type="read_only_check",
                command_preview=(
                    "Check CI/CD image build result, pushed tag/digest, and registry permissions before retrying rollout."
                ),
                risk="low",
                requires_approval=False,
                requires_policy_check=False,
                execution_status="read_only_recommendation",
                rationale="Image pull failures are commonly caused by missing tags, unpublished images, or registry access problems.",
                rollback_plan="No production change is made by this check.",
            )
        )
        actions.append(
            ActionOption(
                action_id="rollback-deployment",
                title="Rollback deployment to previous revision",
                action_type="kubernetes_rollout_undo",
                command_preview=f"kubectl -n {namespace} rollout undo deployment/{deployment}",
                risk="medium",
                requires_approval=True,
                requires_policy_check=True,
                execution_status="approval_required_not_executed",
                rationale="Rollback is often the safest first remediation when the latest image cannot be pulled.",
                rollback_plan="Roll forward again after the correct image tag is published and verified.",
            )
        )
        actions.append(
            ActionOption(
                action_id="restore-known-good-image",
                title="Set deployment image back to a known-good tag",
                action_type="kubernetes_set_image",
                command_preview=f"kubectl -n {namespace} set image deployment/{deployment} <container>=<known-good-image>",
                risk="medium",
                requires_approval=True,
                requires_policy_check=True,
                execution_status="approval_required_not_executed",
                rationale="A known-good image restores service while the failed image publication is investigated.",
                rollback_plan="Reapply the intended image only after CI/CD and registry checks pass.",
            )
        )
        return actions

    if category in {"rollout_failure", "readiness_probe_failure"}:
        actions.append(
            ActionOption(
                action_id="inspect-rollout-health",
                title="Inspect rollout health and pod readiness evidence",
                action_type="read_only_check",
                command_preview=f"kubectl -n {namespace} describe deployment/{deployment}",
                risk="low",
                requires_approval=False,
                requires_policy_check=False,
                execution_status="read_only_recommendation",
                rationale="Collect rollout events and pod readiness details before changing production state.",
                rollback_plan="No production change is made by this check.",
            )
        )
        actions.append(
            ActionOption(
                action_id="rollback-deployment",
                title="Rollback deployment after approval",
                action_type="kubernetes_rollout_undo",
                command_preview=f"kubectl -n {namespace} rollout undo deployment/{deployment}",
                risk="medium",
                requires_approval=True,
                requires_policy_check=True,
                execution_status="approval_required_not_executed",
                rationale="Rollback can restore the last known-good revision when the new rollout is unhealthy.",
                rollback_plan="Roll forward after correcting probes, image, or configuration.",
            )
        )
        return actions

    if category in {"config", "configuration", "environment"}:
        actions.append(
            ActionOption(
                action_id="inspect-config-diff",
                title="Inspect configuration and recent deployment diff",
                action_type="read_only_check",
                command_preview=f"kubectl -n {namespace} get deployment/{deployment} -o yaml",
                risk="low",
                requires_approval=False,
                requires_policy_check=False,
                execution_status="read_only_recommendation",
                rationale="Configuration failures should be proven by current manifests, events, and recent deployment changes.",
                rollback_plan="No production change is made by this check.",
            )
        )
        actions.append(
            ActionOption(
                action_id="restore-required-config",
                title="Restore required configuration after approval",
                action_type="kubernetes_config_patch",
                command_preview=f"kubectl -n {namespace} patch deployment/{deployment} <validated-config-patch>",
                risk="medium",
                requires_approval=True,
                requires_policy_check=True,
                execution_status="approval_required_not_executed",
                rationale="A scoped config patch can restore the missing setting without broader production access.",
                rollback_plan="Revert the patch or rollback deployment if verification fails.",
            )
        )
        return actions

    actions.append(
        ActionOption(
            action_id="manual-engineer-review",
            title="Manual engineer review required",
            action_type="manual_review",
            command_preview="No automated command proposed for this incident category yet.",
            risk="unknown",
            requires_approval=True,
            requires_policy_check=True,
            execution_status="manual_review_required",
            rationale="SafeOps has evidence but does not yet have an allowlisted remediation template for this category.",
            rollback_plan="Engineer should select or define a safe rollback plan before execution.",
        )
    )
    return actions


def build_plan(incident: Dict[str, Any], index: int) -> RemediationPlan:
    namespace, resource = parse_namespace_resource(incident)
    deployment = normalize_deployment_name(resource)
    category = value_from_any(incident, ["primary_category", "category"], "unknown")
    severity = value_from_any(incident, ["severity"], "medium")
    title = value_from_any(incident, ["title", "summary"], category.replace("_", " ").title())
    incident_id = value_from_any(incident, ["incident_id", "id"], f"incident-{index}")
    safe_options = build_actions(str(category), namespace, deployment)

    approval_required = bool(value_from_any(incident, ["approval_required"], True))
    recommended_strategy = value_from_any(
        incident,
        ["recommended_safe_action", "recommendation"],
        safe_options[0].title if safe_options else "Manual review required.",
    )

    return RemediationPlan(
        plan_id=f"plan_{safe_slug(namespace)}_{safe_slug(deployment)}_{safe_slug(str(category))}_{index}",
        incident_id=str(incident_id),
        title=str(title),
        namespace=namespace,
        resource=deployment,
        category=str(category),
        severity=str(severity),
        confidence=float(value_from_any(incident, ["confidence"], 0.75)),
        blast_radius=f"Namespace {namespace}; deployment/service {deployment}; no cluster-wide action proposed.",
        approval_required=approval_required,
        policy_check_required=True,
        detector_can_execute=False,
        recommended_strategy=str(recommended_strategy),
        action_options=safe_options,
        verification_plan=default_verification(namespace, deployment, incident),
        prevention_plan=listify(incident.get("prevention_ideas")) or default_prevention(str(category)),
        evidence_summary=extract_evidence_summary(incident),
        safety_notes=[
            "This remediation plan is read-only and approval-ready; it does not execute actions.",
            "All production-changing actions require policy validation and human approval.",
            "No arbitrary shell execution is allowed; only typed allowlisted actions may be executed later.",
        ],
    )


def as_jsonable(plan: RemediationPlan) -> Dict[str, Any]:
    data = asdict(plan)
    data["action_options"] = [asdict(action) for action in plan.action_options]
    return data


def render_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# SafeOps Real Kubernetes Remediation Plan")
    lines.append("")
    meta = payload.get("metadata", {})
    lines.append(f"Generated: `{meta.get('generated_at', '')}`")
    lines.append(f"Source evidence: `{meta.get('source_evidence', '')}`")
    lines.append(f"Mode: `{meta.get('mode', '')}`")
    lines.append("")
    summary = payload.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"Remediation plans generated: **{summary.get('plans_generated', 0)}**")
    lines.append(f"Approval-required plans: **{summary.get('approval_required_plans', 0)}**")
    lines.append(f"Detector can execute actions: **{summary.get('detector_can_execute_anything', False)}**")
    lines.append("")

    plans = payload.get("remediation_plans", [])
    if not plans:
        lines.append("No active root incidents were found. No remediation plan is required.")
        lines.append("")
        return "\n".join(lines)

    for i, plan in enumerate(plans, start=1):
        lines.append(f"## Plan {i}: {plan.get('title', 'Untitled')}")
        lines.append("")
        lines.append(f"- Plan ID: `{plan.get('plan_id')}`")
        lines.append(f"- Incident ID: `{plan.get('incident_id')}`")
        lines.append(f"- Severity: `{plan.get('severity')}`")
        lines.append(f"- Category: `{plan.get('category')}`")
        lines.append(f"- Target: `{plan.get('namespace')}/{plan.get('resource')}`")
        lines.append(f"- Blast radius: {plan.get('blast_radius')}")
        lines.append(f"- Approval required: `{plan.get('approval_required')}`")
        lines.append(f"- Policy check required: `{plan.get('policy_check_required')}`")
        lines.append(f"- Detector can execute: `{plan.get('detector_can_execute')}`")
        lines.append("")
        lines.append("### Recommended strategy")
        lines.append("")
        lines.append(str(plan.get("recommended_strategy", "")))
        lines.append("")
        lines.append("### Action options")
        lines.append("")
        for action in plan.get("action_options", []):
            lines.append(f"#### {action.get('title')}")
            lines.append(f"- Action type: `{action.get('action_type')}`")
            lines.append(f"- Risk: `{action.get('risk')}`")
            lines.append(f"- Requires approval: `{action.get('requires_approval')}`")
            lines.append(f"- Requires policy check: `{action.get('requires_policy_check')}`")
            lines.append(f"- Execution status: `{action.get('execution_status')}`")
            lines.append(f"- Command preview: `{action.get('command_preview')}`")
            lines.append(f"- Rationale: {action.get('rationale')}")
            lines.append(f"- Rollback plan: {action.get('rollback_plan')}")
            lines.append("")
        lines.append("### Verification plan")
        lines.append("")
        for item in plan.get("verification_plan", []):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("### Evidence summary")
        lines.append("")
        for item in plan.get("evidence_summary", []):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("### Prevention plan")
        lines.append("")
        for item in plan.get("prevention_plan", []):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("### Safety notes")
        lines.append("")
        for item in plan.get("safety_notes", []):
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def build_payload(evidence: Dict[str, Any], source_path: str) -> Dict[str, Any]:
    root_incidents = get_root_incidents(evidence)
    plans = [build_plan(incident, i) for i, incident in enumerate(root_incidents, start=1)]
    plan_payloads = [as_jsonable(plan) for plan in plans]
    return {
        "schema": "safeops_real_k8s_remediation_plan_v1",
        "metadata": {
            "generated_at": utc_now(),
            "source_evidence": source_path,
            "mode": "approval_ready_plan_no_execution",
            "read_only": True,
        },
        "summary": {
            "root_incidents_seen": len(root_incidents),
            "plans_generated": len(plan_payloads),
            "approval_required_plans": sum(1 for p in plan_payloads if p.get("approval_required")),
            "policy_required_plans": sum(1 for p in plan_payloads if p.get("policy_check_required")),
            "detector_can_execute_anything": False,
        },
        "remediation_plans": plan_payloads,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SafeOps remediation plans from real K8s grouped incidents.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to real-k8s-incidents.json")
    parser.add_argument("--json-out", default=DEFAULT_JSON_OUT, help="Path for generated remediation plan JSON")
    parser.add_argument("--md-out", default=DEFAULT_MD_OUT, help="Path for generated remediation plan Markdown")
    args = parser.parse_args()

    evidence = load_json(args.input)
    payload = build_payload(evidence, args.input)
    write_json(args.json_out, payload)
    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload) + "\n")

    print("SafeOps real Kubernetes remediation plan generated.")
    print(f"Plans generated: {payload['summary']['plans_generated']}")
    print(f"Approval required plans: {payload['summary']['approval_required_plans']}")
    print(f"JSON plan: {args.json_out}")
    print(f"Markdown plan: {args.md_out}")
    if payload["summary"]["plans_generated"]:
        print("Top plans:")
        for plan in payload["remediation_plans"][:5]:
            print(
                f"- {plan['severity'].upper()} {plan['namespace']}/{plan['resource']} "
                f"category={plan['category']} approval_required={plan['approval_required']}"
            )


if __name__ == "__main__":
    main()
