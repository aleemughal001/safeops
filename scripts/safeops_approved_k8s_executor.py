#!/usr/bin/env python3
"""SafeOps approved Kubernetes executor.

Consumes a real Kubernetes remediation plan and an approval decision record.
Executes only typed, allowlisted Kubernetes actions after policy validation.

Milestone 25 scope:
- No arbitrary shell execution.
- Only supports kubernetes_rollout_undo for Deployment resources.
- Uses kubectl with argument arrays, never shell=True.
- Writes JSON and Markdown execution/audit records.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_PLAN = "/tmp/safeops-demo/real-k8s-remediation-plan.json"
DEFAULT_DECISION = "/tmp/safeops-demo/real-k8s-approval-decision.json"
DEFAULT_JSON_OUT = "/tmp/safeops-demo/real-k8s-execution-record.json"
DEFAULT_MD_OUT = "/tmp/safeops-demo/real-k8s-execution-record.md"

SAFE_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


@dataclass
class CommandResult:
    command: List[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass
class ExecutionRecord:
    execution_id: str
    plan_id: str
    incident_id: str
    namespace: str
    resource: str
    action_id: str
    action_type: str
    decision: str
    approver: str
    policy_allowed: bool
    execution_status: str
    detector_can_execute: bool
    command_preview: str
    command_executed: List[str] = field(default_factory=list)
    precheck: Optional[CommandResult] = None
    execution_result: Optional[CommandResult] = None
    verification_result: Optional[CommandResult] = None
    verification_status: str = "not_run"
    safety_notes: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def write_json(path: str, data: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def iter_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from iter_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_dicts(item)


def first_nonempty(*values: Any) -> str:
    for value in values:
        if value not in (None, "", "unknown"):
            return str(value)
    return ""


def extract_plans(plan_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    value = plan_doc.get("remediation_plans")
    if isinstance(value, list):
        return [p for p in value if isinstance(p, dict)]
    value = plan_doc.get("plans")
    if isinstance(value, list):
        return [p for p in value if isinstance(p, dict)]
    return []


def extract_decision(decision_doc: Dict[str, Any]) -> Tuple[str, str, str]:
    """Return decision, approver, request_id from flexible decision JSON."""
    best: Optional[Dict[str, Any]] = None
    for item in iter_dicts(decision_doc):
        decision = safe_str(item.get("decision") or item.get("status") or "").lower()
        if decision in {"approve", "approved", "reject", "rejected", "expired"}:
            best = item
            break
    if not best:
        return "", "", ""
    decision = safe_str(best.get("decision") or best.get("status") or "").lower()
    if decision == "approved":
        decision = "approve"
    if decision == "rejected":
        decision = "reject"
    approver = first_nonempty(
        best.get("approver"),
        best.get("approved_by"),
        best.get("decided_by"),
        best.get("user"),
        "unknown",
    )
    request_id = first_nonempty(best.get("request_id"), best.get("approval_request_id"), best.get("id"))
    return decision, approver, request_id


def choose_action(plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Choose the safest supported write action from the plan.

    For Milestone 25 we intentionally support only rollback-deployment.
    Other write actions remain planned but not executable.
    """
    options = plan.get("action_options") or plan.get("actions") or []
    if not isinstance(options, list):
        return None
    for option in options:
        if not isinstance(option, dict):
            continue
        action_id = safe_str(option.get("action_id") or option.get("id"))
        action_type = safe_str(option.get("action_type") or option.get("type"))
        if action_id == "rollback-deployment" and action_type == "kubernetes_rollout_undo":
            return option
    return None


def normalize_resource(resource: str) -> str:
    resource = resource.strip()
    for prefix in ("deployment/", "Deployment/", "deploy/", "deployment.apps/"):
        if resource.startswith(prefix):
            return resource.split("/", 1)[1]
    if "/" in resource:
        return resource.split("/", 1)[1]
    return resource


def policy_check(namespace: str, deployment: str, action_type: str) -> Tuple[bool, List[str]]:
    notes = [
        "Executor accepts only structured, typed actions from a remediation plan.",
        "Arbitrary shell commands are not accepted or executed.",
        "Execution requires an approval decision plus policy validation.",
    ]
    allowed_namespaces = [x.strip() for x in os.environ.get("SAFEOPS_ALLOWED_NAMESPACES", "demo").split(",") if x.strip()]
    if namespace not in allowed_namespaces:
        notes.append(f"Denied: namespace {namespace!r} is not in SAFEOPS_ALLOWED_NAMESPACES={allowed_namespaces}.")
        return False, notes
    if action_type != "kubernetes_rollout_undo":
        notes.append(f"Denied: unsupported action_type {action_type!r}.")
        return False, notes
    if not SAFE_NAME_RE.match(namespace):
        notes.append(f"Denied: unsafe namespace name {namespace!r}.")
        return False, notes
    if not SAFE_NAME_RE.match(deployment):
        notes.append(f"Denied: unsafe deployment name {deployment!r}.")
        return False, notes
    notes.append("Allowed: action is kubernetes_rollout_undo on a single deployment in an allowed namespace.")
    return True, notes


def run_cmd(command: List[str], timeout: int = 90) -> CommandResult:
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        return CommandResult(command=command, returncode=proc.returncode, stdout=proc.stdout.strip(), stderr=proc.stderr.strip())
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command=command,
            returncode=124,
            stdout=(exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            stderr=f"Timed out after {timeout}s",
        )


def result_to_dict(result: Optional[CommandResult]) -> Optional[Dict[str, Any]]:
    if result is None:
        return None
    return asdict(result)


def record_to_dict(record: ExecutionRecord) -> Dict[str, Any]:
    data = asdict(record)
    data["precheck"] = result_to_dict(record.precheck)
    data["execution_result"] = result_to_dict(record.execution_result)
    data["verification_result"] = result_to_dict(record.verification_result)
    return data


def execute_plan(plan: Dict[str, Any], decision: str, approver: str, dry_run: bool) -> ExecutionRecord:
    namespace = first_nonempty(plan.get("namespace"), "default")
    deployment = normalize_resource(first_nonempty(plan.get("resource"), plan.get("deployment"), plan.get("target"), "unknown"))
    plan_id = first_nonempty(plan.get("plan_id"), plan.get("id"), "plan_unknown")
    incident_id = first_nonempty(plan.get("incident_id"), "incident_unknown")
    detector_can_execute = bool(plan.get("detector_can_execute", False))
    action = choose_action(plan)

    if action is None:
        return ExecutionRecord(
            execution_id=f"exec_{namespace}_{deployment}_no_supported_action",
            plan_id=plan_id,
            incident_id=incident_id,
            namespace=namespace,
            resource=deployment,
            action_id="none",
            action_type="unsupported",
            decision=decision or "missing",
            approver=approver or "unknown",
            policy_allowed=False,
            execution_status="blocked_no_supported_action",
            detector_can_execute=detector_can_execute,
            command_preview="No supported allowlisted action found in remediation plan.",
            safety_notes=["Milestone 25 supports only rollback-deployment / kubernetes_rollout_undo."],
        )

    action_id = safe_str(action.get("action_id") or action.get("id"))
    action_type = safe_str(action.get("action_type") or action.get("type"))
    command_preview = safe_str(action.get("command_preview"))
    allowed, notes = policy_check(namespace, deployment, action_type)

    record = ExecutionRecord(
        execution_id=f"exec_{namespace}_{deployment}_{action_id}",
        plan_id=plan_id,
        incident_id=incident_id,
        namespace=namespace,
        resource=deployment,
        action_id=action_id,
        action_type=action_type,
        decision=decision or "missing",
        approver=approver or "unknown",
        policy_allowed=allowed,
        execution_status="pending",
        detector_can_execute=detector_can_execute,
        command_preview=command_preview,
        safety_notes=notes,
    )

    if decision != "approve":
        record.execution_status = "blocked_not_approved"
        record.safety_notes.append("No write action executed because approval decision is not approve.")
        return record
    if not allowed:
        record.execution_status = "blocked_by_policy"
        record.safety_notes.append("No write action executed because policy validation failed.")
        return record

    precheck_cmd = ["kubectl", "-n", namespace, "get", "deployment", deployment]
    execute_cmd = ["kubectl", "-n", namespace, "rollout", "undo", f"deployment/{deployment}"]
    verify_cmd = ["kubectl", "-n", namespace, "rollout", "status", f"deployment/{deployment}", "--timeout=90s"]
    record.command_executed = execute_cmd

    record.precheck = run_cmd(precheck_cmd, timeout=30)
    if record.precheck.returncode != 0:
        record.execution_status = "blocked_precheck_failed"
        record.safety_notes.append("No write action executed because the target deployment precheck failed.")
        return record

    if dry_run:
        record.execution_status = "dry_run_policy_allowed_not_executed"
        record.verification_status = "dry_run_not_verified"
        record.safety_notes.append("Dry-run mode: policy passed but kubectl rollout undo was not executed.")
        return record

    record.execution_result = run_cmd(execute_cmd, timeout=60)
    if record.execution_result.returncode != 0:
        record.execution_status = "execution_failed"
        record.verification_status = "not_verified_execution_failed"
        return record

    record.verification_result = run_cmd(verify_cmd, timeout=100)
    if record.verification_result.returncode == 0:
        record.execution_status = "succeeded"
        record.verification_status = "verified_healthy"
    else:
        record.execution_status = "executed_verification_failed"
        record.verification_status = "verification_failed_manual_review_required"
    return record


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    summary = report.get("summary", {})
    lines.append("# SafeOps Approved Kubernetes Execution Record")
    lines.append("")
    lines.append("This record is generated after SafeOps consumes a remediation plan and an approval decision.")
    lines.append("Milestone 25 supports only approval-gated, policy-checked `kubectl rollout undo` for a single Deployment.")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Plans seen: `{summary.get('plans_seen', 0)}`")
    lines.append(f"- Execution records generated: `{summary.get('execution_records_generated', 0)}`")
    lines.append(f"- Executed actions: `{summary.get('executed_actions', 0)}`")
    lines.append(f"- Verified healthy: `{summary.get('verified_healthy', 0)}`")
    lines.append(f"- Blocked actions: `{summary.get('blocked_actions', 0)}`")
    lines.append("")

    records = report.get("execution_records", [])
    if not records:
        lines.append("No execution records were generated.")
        lines.append("")
        return "\n".join(lines)

    for idx, rec in enumerate(records, 1):
        lines.append(f"## Execution {idx}: `{rec.get('namespace')}/{rec.get('resource')}`")
        lines.append(f"- Execution ID: `{rec.get('execution_id')}`")
        lines.append(f"- Incident ID: `{rec.get('incident_id')}`")
        lines.append(f"- Plan ID: `{rec.get('plan_id')}`")
        lines.append(f"- Action: `{rec.get('action_id')}` / `{rec.get('action_type')}`")
        lines.append(f"- Decision: `{rec.get('decision')}` by `{rec.get('approver')}`")
        lines.append(f"- Policy allowed: `{rec.get('policy_allowed')}`")
        lines.append(f"- Execution status: `{rec.get('execution_status')}`")
        lines.append(f"- Verification status: `{rec.get('verification_status')}`")
        lines.append(f"- Command preview: `{rec.get('command_preview')}`")
        executed = rec.get("command_executed") or []
        if executed:
            lines.append(f"- Command executed: `{' '.join(executed)}`")
        lines.append("")
        lines.append("### Safety notes")
        for note in rec.get("safety_notes") or []:
            lines.append(f"- {note}")
        lines.append("")
        for section in ("precheck", "execution_result", "verification_result"):
            value = rec.get(section)
            if not value:
                continue
            lines.append(f"### {section}")
            lines.append(f"- Return code: `{value.get('returncode')}`")
            lines.append(f"- Command: `{' '.join(value.get('command') or [])}`")
            stdout = value.get("stdout") or ""
            stderr = value.get("stderr") or ""
            if stdout:
                lines.append("- stdout:")
                lines.append("```text")
                lines.append(stdout[:2500])
                lines.append("```")
            if stderr:
                lines.append("- stderr:")
                lines.append("```text")
                lines.append(stderr[:2500])
                lines.append("```")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute approved SafeOps Kubernetes remediation plans.")
    parser.add_argument("--plan", default=DEFAULT_PLAN)
    parser.add_argument("--decision", default=DEFAULT_DECISION)
    parser.add_argument("--json-out", default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", default=DEFAULT_MD_OUT)
    parser.add_argument("--dry-run", action="store_true", help="Validate policy but do not execute kubectl.")
    args = parser.parse_args()

    plan_doc = load_json(args.plan)
    decision_doc = load_json(args.decision)
    plans = extract_plans(plan_doc)
    decision, approver, request_id = extract_decision(decision_doc)

    records: List[ExecutionRecord] = []
    for plan in plans:
        # Only create execution records for approval-required plans.
        if bool(plan.get("approval_required", False)):
            records.append(execute_plan(plan, decision, approver, args.dry_run))

    report = {
        "schema": "safeops_approved_k8s_execution_record_v1",
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "approved_policy_checked_execution" if not args.dry_run else "dry_run_policy_check_only",
            "source_plan": args.plan,
            "source_decision": args.decision,
            "approval_request_id": request_id,
            "read_only": False if records and not args.dry_run else True,
            "arbitrary_shell_execution_allowed": False,
        },
        "summary": {
            "plans_seen": len(plans),
            "execution_records_generated": len(records),
            "executed_actions": sum(1 for r in records if r.execution_result is not None),
            "verified_healthy": sum(1 for r in records if r.verification_status == "verified_healthy"),
            "blocked_actions": sum(1 for r in records if r.execution_status.startswith("blocked") or r.execution_status.startswith("dry_run")),
        },
        "execution_records": [record_to_dict(r) for r in records],
    }

    write_json(args.json_out, report)
    Path(args.md_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md_out).write_text(render_markdown(report) + "\n")

    print("SafeOps approved Kubernetes executor complete.")
    print(f"Plans seen: {len(plans)}")
    print(f"Execution records generated: {len(records)}")
    print(f"Executed actions: {report['summary']['executed_actions']}")
    print(f"Verified healthy: {report['summary']['verified_healthy']}")
    print(f"Blocked actions: {report['summary']['blocked_actions']}")
    for record in records:
        print(
            f"- {record.execution_status.upper()} {record.namespace}/{record.resource} "
            f"action={record.action_id} verification={record.verification_status}"
        )
    print(f"JSON execution record: {args.json_out}")
    print(f"Markdown execution record: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
