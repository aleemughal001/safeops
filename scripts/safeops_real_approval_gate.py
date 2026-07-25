#!/usr/bin/env python3
"""SafeOps real remediation approval gate.

Reads a SafeOps real Kubernetes remediation-plan JSON file and produces an
approval-ready request package. Optionally records a local approve/reject
choice as an audit-ready decision artifact.

This tool is intentionally read-only with respect to Kubernetes. It does not
execute remediation actions.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PLAN = "/tmp/safeops-demo/real-k8s-remediation-plan.json"
DEFAULT_REQUEST_JSON = "/tmp/safeops-demo/real-k8s-approval-request.json"
DEFAULT_REQUEST_MD = "/tmp/safeops-demo/real-k8s-approval-request.md"
DEFAULT_DECISION_JSON = "/tmp/safeops-demo/real-k8s-approval-decision.json"
DEFAULT_DECISION_MD = "/tmp/safeops-demo/real-k8s-approval-decision.md"


@dataclass
class ApprovalRequest:
    request_id: str
    status: str
    incident_id: str
    plan_id: str
    title: str
    namespace: str
    resource: str
    category: str
    severity: str
    approval_required: bool
    policy_check_required: bool
    detector_can_execute: bool
    expires_at: str
    blast_radius: str
    recommended_strategy: str
    action_options: List[Dict[str, Any]] = field(default_factory=list)
    verification_plan: List[str] = field(default_factory=list)
    safety_notes: List[str] = field(default_factory=list)
    evidence_summary: List[str] = field(default_factory=list)


@dataclass
class ApprovalDecision:
    decision_id: str
    request_id: str
    plan_id: str
    incident_id: str
    decision: str
    approver: str
    decided_at: str
    reason: str
    execution_allowed: bool
    execution_status: str
    safety_notes: List[str]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def slug(text: Any) -> str:
    s = str(text or "unknown").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "unknown"


def load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {
            "schema": "safeops_real_k8s_remediation_plan_v1",
            "metadata": {"missing_input": str(path)},
            "summary": {"plans_generated": 0, "approval_required_plans": 0},
            "remediation_plans": [],
        }
    return json.loads(p.read_text())


def write_json(path: str, data: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def plan_action_summary(action: Dict[str, Any]) -> str:
    title = action.get("title") or action.get("action_id") or "Action"
    risk = action.get("risk", "unknown")
    requires_approval = action.get("requires_approval", False)
    command = action.get("command_preview", "No command preview")
    return f"{title} | risk={risk} | approval_required={requires_approval} | `{command}`"


def build_requests(plan_data: Dict[str, Any], ttl_minutes: int) -> List[ApprovalRequest]:
    generated_at = utc_now()
    expires = iso(generated_at + timedelta(minutes=ttl_minutes))
    requests: List[ApprovalRequest] = []

    for index, plan in enumerate(plan_data.get("remediation_plans", []) or [], start=1):
        if not plan.get("approval_required", False):
            continue

        namespace = plan.get("namespace") or "default"
        resource = plan.get("resource") or "unknown"
        plan_id = plan.get("plan_id") or f"plan_{slug(namespace)}_{slug(resource)}_{index}"
        incident_id = plan.get("incident_id") or "unknown_incident"
        category = plan.get("category") or "unknown"
        request_id = f"approval_{slug(namespace)}_{slug(resource)}_{slug(category)}_{index}"

        requests.append(
            ApprovalRequest(
                request_id=request_id,
                status="pending_approval",
                incident_id=incident_id,
                plan_id=plan_id,
                title=plan.get("title") or "SafeOps remediation approval request",
                namespace=namespace,
                resource=resource,
                category=category,
                severity=plan.get("severity") or "unknown",
                approval_required=True,
                policy_check_required=bool(plan.get("policy_check_required", True)),
                detector_can_execute=bool(plan.get("detector_can_execute", False)),
                expires_at=expires,
                blast_radius=plan.get("blast_radius") or f"Namespace {namespace}; resource {resource}",
                recommended_strategy=plan.get("recommended_strategy") or "Review SafeOps remediation options.",
                action_options=plan.get("action_options") or [],
                verification_plan=plan.get("verification_plan") or [],
                safety_notes=plan.get("safety_notes") or [],
                evidence_summary=plan.get("evidence_summary") or [],
            )
        )
    return requests


def request_report_md(payload: Dict[str, Any]) -> str:
    requests = payload.get("approval_requests", []) or []
    summary = payload.get("summary", {})
    lines: List[str] = []
    lines.append("# SafeOps Real Kubernetes Approval Gate")
    lines.append("")
    lines.append("This approval gate is read-only. It prepares approval requests from remediation plans and records decisions. It does not execute Kubernetes actions.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Plans seen: `{summary.get('plans_seen', 0)}`")
    lines.append(f"- Approval requests generated: `{summary.get('approval_requests_generated', 0)}`")
    lines.append(f"- Execution allowed by this tool: `{summary.get('execution_allowed_by_approval_gate', False)}`")
    lines.append("")

    if not requests:
        lines.append("## No approval required")
        lines.append("")
        lines.append("No remediation plans currently require approval.")
        lines.append("")
        return "\n".join(lines) + "\n"

    for req in requests:
        lines.append(f"## Approval Request: {req.get('title')}")
        lines.append("")
        lines.append(f"- Request ID: `{req.get('request_id')}`")
        lines.append(f"- Status: `{req.get('status')}`")
        lines.append(f"- Incident ID: `{req.get('incident_id')}`")
        lines.append(f"- Plan ID: `{req.get('plan_id')}`")
        lines.append(f"- Target: `{req.get('namespace')}/{req.get('resource')}`")
        lines.append(f"- Severity: `{req.get('severity')}`")
        lines.append(f"- Category: `{req.get('category')}`")
        lines.append(f"- Approval required: `{req.get('approval_required')}`")
        lines.append(f"- Policy check required: `{req.get('policy_check_required')}`")
        lines.append(f"- Detector can execute: `{req.get('detector_can_execute')}`")
        lines.append(f"- Expires at: `{req.get('expires_at')}`")
        lines.append(f"- Blast radius: {req.get('blast_radius')}")
        lines.append("")
        lines.append("### Recommended strategy")
        lines.append("")
        lines.append(req.get("recommended_strategy") or "Review remediation plan.")
        lines.append("")
        lines.append("### Approval options")
        lines.append("")
        lines.append("Approve only if the target, blast radius, command previews, and verification plan are acceptable.")
        lines.append("")
        lines.append("```bash")
        lines.append(f"python3 scripts/safeops_real_approval_gate.py --decision approve --approver <name> --request-id {req.get('request_id')}")
        lines.append(f"python3 scripts/safeops_real_approval_gate.py --decision reject --approver <name> --request-id {req.get('request_id')} --reason \"reason here\"")
        lines.append("```")
        lines.append("")
        lines.append("### Action options")
        lines.append("")
        for action in req.get("action_options", []):
            lines.append(f"- {plan_action_summary(action)}")
        lines.append("")
        lines.append("### Evidence summary")
        lines.append("")
        for item in req.get("evidence_summary", []) or ["Evidence is available in the linked incident evidence pack."]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("### Verification plan")
        lines.append("")
        for step in req.get("verification_plan", []) or ["Verify workload recovery after approved execution."]:
            lines.append(f"- {step}")
        lines.append("")
        lines.append("### Safety notes")
        lines.append("")
        for note in req.get("safety_notes", []) or []:
            lines.append(f"- {note}")
        lines.append("- This approval gate does not execute the plan.")
        lines.append("- Production-changing actions still require policy validation before execution.")
        lines.append("")
    return "\n".join(lines) + "\n"


def decision_report_md(payload: Dict[str, Any]) -> str:
    decisions = payload.get("approval_decisions", []) or []
    summary = payload.get("summary", {})
    lines: List[str] = []
    lines.append("# SafeOps Approval Decision Record")
    lines.append("")
    lines.append("This file records local approval/rejection decisions. It does not execute Kubernetes actions.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Decisions recorded: `{summary.get('decisions_recorded', 0)}`")
    lines.append(f"- Approved decisions: `{summary.get('approved_decisions', 0)}`")
    lines.append(f"- Rejected decisions: `{summary.get('rejected_decisions', 0)}`")
    lines.append(f"- Execution allowed by this tool: `{summary.get('execution_allowed_by_approval_gate', False)}`")
    lines.append("")

    if not decisions:
        lines.append("No approval decisions recorded.")
        lines.append("")
        return "\n".join(lines) + "\n"

    for dec in decisions:
        lines.append(f"## Decision: {dec.get('decision')}")
        lines.append("")
        lines.append(f"- Decision ID: `{dec.get('decision_id')}`")
        lines.append(f"- Request ID: `{dec.get('request_id')}`")
        lines.append(f"- Incident ID: `{dec.get('incident_id')}`")
        lines.append(f"- Plan ID: `{dec.get('plan_id')}`")
        lines.append(f"- Approver: `{dec.get('approver')}`")
        lines.append(f"- Decided at: `{dec.get('decided_at')}`")
        lines.append(f"- Reason: {dec.get('reason')}")
        lines.append(f"- Execution allowed by this approval gate: `{dec.get('execution_allowed')}`")
        lines.append(f"- Execution status: `{dec.get('execution_status')}`")
        lines.append("")
        lines.append("### Safety notes")
        lines.append("")
        for note in dec.get("safety_notes", []) or []:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines) + "\n"


def select_request(requests: List[ApprovalRequest], request_id: str) -> Optional[ApprovalRequest]:
    if not requests:
        return None
    if request_id:
        for req in requests:
            if req.request_id == request_id:
                return req
        return None
    return requests[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SafeOps approval requests and decision records from remediation plans.")
    parser.add_argument("--input", default=DEFAULT_PLAN, help="Remediation plan JSON input")
    parser.add_argument("--json-out", default=DEFAULT_REQUEST_JSON, help="Approval request JSON output")
    parser.add_argument("--md-out", default=DEFAULT_REQUEST_MD, help="Approval request Markdown output")
    parser.add_argument("--decision-json-out", default=DEFAULT_DECISION_JSON, help="Approval decision JSON output")
    parser.add_argument("--decision-md-out", default=DEFAULT_DECISION_MD, help="Approval decision Markdown output")
    parser.add_argument("--ttl-minutes", type=int, default=30, help="Approval request expiry in minutes")
    parser.add_argument("--decision", choices=["approve", "reject"], help="Record an approval decision instead of request-only mode")
    parser.add_argument("--request-id", default="", help="Specific approval request ID to decide; defaults to first pending request")
    parser.add_argument("--approver", default="local-demo-user", help="Approver identity recorded in the decision")
    parser.add_argument("--reason", default="Local demo decision.", help="Reason stored in decision record")
    args = parser.parse_args()

    plan_data = load_json(args.input)
    plans = plan_data.get("remediation_plans", []) or []
    requests = build_requests(plan_data, args.ttl_minutes)

    request_payload: Dict[str, Any] = {
        "schema": "safeops_real_k8s_approval_request_v1",
        "metadata": {
            "generated_at": iso(utc_now()),
            "mode": "approval_request_no_execution",
            "read_only": True,
            "source_plan": args.input,
        },
        "summary": {
            "plans_seen": len(plans),
            "approval_requests_generated": len(requests),
            "execution_allowed_by_approval_gate": False,
        },
        "approval_requests": [asdict(req) for req in requests],
    }

    write_json(args.json_out, request_payload)
    Path(args.md_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md_out).write_text(request_report_md(request_payload))

    print("SafeOps approval gate request package generated.")
    print(f"Approval requests generated: {len(requests)}")
    print(f"JSON request: {args.json_out}")
    print(f"Markdown request: {args.md_out}")

    if not args.decision:
        if requests:
            print("Top approval requests:")
            for req in requests[:5]:
                print(f"- {req.severity.upper()} {req.namespace}/{req.resource} request_id={req.request_id} status={req.status}")
        return 0

    selected = select_request(requests, args.request_id)
    if not selected:
        decision_payload = {
            "schema": "safeops_real_k8s_approval_decision_v1",
            "metadata": {
                "generated_at": iso(utc_now()),
                "mode": "approval_decision_no_execution",
                "read_only": True,
                "source_request": args.json_out,
            },
            "summary": {
                "decisions_recorded": 0,
                "approved_decisions": 0,
                "rejected_decisions": 0,
                "execution_allowed_by_approval_gate": False,
            },
            "approval_decisions": [],
            "error": "No matching approval request found.",
        }
        write_json(args.decision_json_out, decision_payload)
        Path(args.decision_md_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.decision_md_out).write_text(decision_report_md(decision_payload))
        print("No matching approval request found. Decision not recorded.")
        return 2

    decision_id = f"decision_{slug(selected.request_id)}_{slug(args.decision)}"
    approved = args.decision == "approve"
    decision = ApprovalDecision(
        decision_id=decision_id,
        request_id=selected.request_id,
        plan_id=selected.plan_id,
        incident_id=selected.incident_id,
        decision=args.decision,
        approver=args.approver,
        decided_at=iso(utc_now()),
        reason=args.reason,
        execution_allowed=False,
        execution_status="approved_but_not_executed" if approved else "rejected_not_executed",
        safety_notes=[
            "This approval gate records the human decision only; it does not execute remediation.",
            "An executor milestone must still validate policy before any Kubernetes action can run.",
            "No arbitrary shell execution is allowed.",
        ],
    )

    decision_payload = {
        "schema": "safeops_real_k8s_approval_decision_v1",
        "metadata": {
            "generated_at": iso(utc_now()),
            "mode": "approval_decision_no_execution",
            "read_only": True,
            "source_request": args.json_out,
        },
        "summary": {
            "decisions_recorded": 1,
            "approved_decisions": 1 if approved else 0,
            "rejected_decisions": 0 if approved else 1,
            "execution_allowed_by_approval_gate": False,
        },
        "approval_decisions": [asdict(decision)],
    }
    write_json(args.decision_json_out, decision_payload)
    Path(args.decision_md_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.decision_md_out).write_text(decision_report_md(decision_payload))

    print("SafeOps approval decision recorded.")
    print(f"Decision: {args.decision}")
    print(f"Approver: {args.approver}")
    print("Execution handoff created: True")
    print("Executor will enforce approval policy and action allowlist.")
    print(f"Decision JSON: {args.decision_json_out}")
    print(f"Decision Markdown: {args.decision_md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
