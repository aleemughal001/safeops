#!/usr/bin/env python3
"""Build and verify a tamper-evident audit trail for the real SafeOps K8s flow.

The audit chain intentionally uses only the Python standard library. It reads the
real artifacts produced by the detector, remediation planner, approval gate, and
approved executor, then writes a hash-chained audit log. Any change to a recorded
event breaks the chain. Any change to a source artifact can also be detected when
that artifact is still present on disk.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

JsonDict = Dict[str, Any]
ZERO_HASH = "0" * 64
SCHEMA_VERSION = "safeops.audit_chain.v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_payload(value: Any) -> str:
    return sha256_text(canonical_json(value))


def load_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    if not path.exists():
        return None, f"missing: {path}"
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as exc:
        return None, f"invalid json: {path}: {exc}"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def value_from_any(obj: Any, keys: Iterable[str], default: Any = "") -> Any:
    if not isinstance(obj, dict):
        return default
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in (
            "root_incidents",
            "incidents",
            "plans",
            "approval_requests",
            "decisions",
            "execution_records",
            "records",
            "events",
        ):
            if isinstance(value.get(key), list):
                return value[key]
    return [value]


def first_dict(value: Any) -> JsonDict:
    if isinstance(value, dict):
        for key in ("plans", "approval_requests", "decisions", "execution_records", "records"):
            items = value.get(key)
            if isinstance(items, list) and items and isinstance(items[0], dict):
                return items[0]
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def infer_count(value: Any, keys: Iterable[str]) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in keys:
            items = value.get(key)
            if isinstance(items, list):
                return len(items)
        for key in keys:
            number = value.get(key)
            if isinstance(number, int):
                return number
    return 0 if value in (None, {}) else 1


def summarize_incidents(payload: Any) -> JsonDict:
    items = as_list(payload)
    first = first_dict(payload)
    return {
        "root_incidents": infer_count(payload, ["root_incidents", "incidents", "root_incidents_detected"]),
        "raw_findings_grouped": value_from_any(payload, ["raw_findings_grouped", "raw_findings", "findings_grouped"], "unknown"),
        "namespace": value_from_any(first, ["namespace", "ns"], "unknown"),
        "resource": value_from_any(first, ["resource", "group_resource", "affected_service", "name"], "unknown"),
        "category": value_from_any(first, ["category", "incident_category"], "unknown"),
        "severity": value_from_any(first, ["severity"], "unknown"),
        "items_seen": len(items),
    }


def summarize_plan(payload: Any) -> JsonDict:
    first = first_dict(payload)
    return {
        "plans": infer_count(payload, ["plans", "plans_generated"]),
        "approval_required": value_from_any(first, ["approval_required"], "unknown"),
        "namespace": value_from_any(first, ["namespace", "ns"], "unknown"),
        "resource": value_from_any(first, ["resource", "target", "deployment", "name"], "unknown"),
        "category": value_from_any(first, ["category", "incident_category"], "unknown"),
        "recommended_action": value_from_any(first, ["recommended_action", "action", "safe_action"], "unknown"),
    }


def summarize_approval_request(payload: Any) -> JsonDict:
    first = first_dict(payload)
    return {
        "approval_requests": infer_count(payload, ["approval_requests", "requests", "approval_requests_generated"]),
        "request_id": value_from_any(first, ["request_id", "approval_request_id", "id"], "unknown"),
        "status": value_from_any(first, ["status"], "unknown"),
        "namespace": value_from_any(first, ["namespace", "ns"], "unknown"),
        "resource": value_from_any(first, ["resource", "target", "deployment", "name"], "unknown"),
    }


def summarize_approval_decision(payload: Any) -> JsonDict:
    first = first_dict(payload)
    return {
        "decision": value_from_any(first, ["decision", "status"], "unknown"),
        "approver": value_from_any(first, ["approver", "approved_by", "decided_by"], "unknown"),
        "execution_allowed_by_approval_gate": value_from_any(
            first, ["execution_allowed_by_approval_gate", "execution_allowed"], "unknown"
        ),
        "request_id": value_from_any(first, ["request_id", "approval_request_id"], "unknown"),
    }


def summarize_execution(payload: Any) -> JsonDict:
    first = first_dict(payload)
    records = as_list(payload)
    executed_actions = value_from_any(payload, ["executed_actions"], "unknown")
    verified_healthy = value_from_any(payload, ["verified_healthy"], "unknown")
    blocked_actions = value_from_any(payload, ["blocked_actions"], "unknown")
    return {
        "execution_records": infer_count(payload, ["execution_records", "records"]),
        "executed_actions": executed_actions,
        "verified_healthy": verified_healthy,
        "blocked_actions": blocked_actions,
        "namespace": value_from_any(first, ["namespace", "ns"], "unknown"),
        "resource": value_from_any(first, ["resource", "target", "deployment", "name"], "unknown"),
        "action": value_from_any(first, ["action", "action_type", "typed_action"], "unknown"),
        "status": value_from_any(first, ["status", "result"], "unknown"),
        "verification": value_from_any(first, ["verification", "verification_status"], "unknown"),
        "records_seen": len(records),
    }


def make_event(
    *,
    index: int,
    event_type: str,
    namespace: str,
    source_artifact: Path,
    payload: Any,
    payload_summary: JsonDict,
    prev_hash: str,
) -> JsonDict:
    payload_hash = hash_payload(payload)
    event = {
        "index": index,
        "event_id": f"audit-{index:04d}-{event_type}",
        "event_type": event_type,
        "timestamp_utc": now_utc(),
        "namespace": namespace,
        "source_artifact": str(source_artifact),
        "payload_hash": payload_hash,
        "payload_summary": payload_summary,
        "prev_hash": prev_hash,
    }
    event["event_hash"] = compute_event_hash(event)
    return event


def compute_event_hash(event: JsonDict) -> str:
    clean = copy.deepcopy(event)
    clean.pop("event_hash", None)
    return hash_payload(clean)


def build_audit_chain(namespace: str, artifacts: List[Tuple[str, Path, Any, JsonDict]]) -> JsonDict:
    events: List[JsonDict] = []
    prev_hash = ZERO_HASH
    for index, (event_type, path, payload, summary) in enumerate(artifacts, start=1):
        event = make_event(
            index=index,
            event_type=event_type,
            namespace=namespace,
            source_artifact=path,
            payload=payload,
            payload_summary=summary,
            prev_hash=prev_hash,
        )
        events.append(event)
        prev_hash = event["event_hash"]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": now_utc(),
        "namespace": namespace,
        "chain_head": prev_hash,
        "events": events,
        "verification": {
            "valid": True,
            "checked_events": len(events),
            "artifact_recheck": "not_run_at_generation_time",
        },
    }


def collect_artifacts(args: argparse.Namespace) -> Tuple[List[Tuple[str, Path, Any, JsonDict]], List[str]]:
    artifact_specs = [
        ("evidence_collected", Path(args.incident_json), summarize_incidents),
        ("remediation_plan_generated", Path(args.plan_json), summarize_plan),
        ("approval_requested", Path(args.approval_request_json), summarize_approval_request),
        ("approval_decision_recorded", Path(args.approval_decision_json), summarize_approval_decision),
        ("approved_execution_completed", Path(args.execution_json), summarize_execution),
    ]
    artifacts: List[Tuple[str, Path, Any, JsonDict]] = []
    warnings: List[str] = []
    for event_type, path, summarizer in artifact_specs:
        payload, error = load_json(path)
        if error:
            warnings.append(error)
            continue
        artifacts.append((event_type, path, payload, summarizer(payload)))
    return artifacts, warnings


def verify_audit_chain(audit: JsonDict, *, recheck_artifacts: bool = True) -> JsonDict:
    errors: List[str] = []
    warnings: List[str] = []
    events = audit.get("events", [])
    if not isinstance(events, list):
        return {"valid": False, "errors": ["events must be a list"], "warnings": warnings, "checked_events": 0}

    prev_hash = ZERO_HASH
    for expected_index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            errors.append(f"event {expected_index} is not an object")
            continue
        if event.get("index") != expected_index:
            errors.append(f"event index mismatch at position {expected_index}: got {event.get('index')}")
        if event.get("prev_hash") != prev_hash:
            errors.append(f"prev_hash mismatch at event {expected_index}")
        expected_hash = compute_event_hash(event)
        if event.get("event_hash") != expected_hash:
            errors.append(f"event_hash mismatch at event {expected_index} ({event.get('event_type', 'unknown')})")
        if recheck_artifacts:
            source = Path(str(event.get("source_artifact", "")))
            payload, error = load_json(source)
            if error:
                warnings.append(f"artifact recheck skipped for event {expected_index}: {error}")
            else:
                current_hash = hash_payload(payload)
                if current_hash != event.get("payload_hash"):
                    errors.append(f"payload_hash mismatch for source artifact at event {expected_index}: {source}")
        prev_hash = str(event.get("event_hash", ""))

    if audit.get("chain_head") != prev_hash:
        errors.append("chain_head does not match final event hash")

    return {
        "valid": not errors,
        "checked_events": len(events),
        "errors": errors,
        "warnings": warnings,
        "artifact_recheck": "enabled" if recheck_artifacts else "disabled",
    }


def write_markdown(audit: JsonDict, verification: JsonDict, path: Path) -> None:
    lines: List[str] = []
    lines.append("# SafeOps Tamper-Evident Real Audit Trail")
    lines.append("")
    lines.append(f"- Schema: `{audit.get('schema_version', SCHEMA_VERSION)}`")
    lines.append(f"- Namespace: `{audit.get('namespace', 'unknown')}`")
    lines.append(f"- Generated at UTC: `{audit.get('generated_at_utc', 'unknown')}`")
    lines.append(f"- Chain head: `{audit.get('chain_head', '')}`")
    lines.append(f"- Verification valid: `{verification.get('valid')}`")
    lines.append(f"- Events checked: `{verification.get('checked_events')}`")
    lines.append("")
    if verification.get("errors"):
        lines.append("## Verification errors")
        lines.append("")
        for error in verification.get("errors", []):
            lines.append(f"- {error}")
        lines.append("")
    if verification.get("warnings"):
        lines.append("## Verification warnings")
        lines.append("")
        for warning in verification.get("warnings", []):
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Audit events")
    lines.append("")
    lines.append("| # | Event | Source artifact | Payload hash | Previous hash | Event hash |")
    lines.append("|---:|---|---|---|---|---|")
    for event in audit.get("events", []):
        source = Path(str(event.get("source_artifact", ""))).name
        lines.append(
            "| {idx} | `{event_type}` | `{source}` | `{payload_hash}` | `{prev_hash}` | `{event_hash}` |".format(
                idx=event.get("index", ""),
                event_type=event.get("event_type", ""),
                source=source,
                payload_hash=str(event.get("payload_hash", ""))[:12] + "...",
                prev_hash=str(event.get("prev_hash", ""))[:12] + "...",
                event_hash=str(event.get("event_hash", ""))[:12] + "...",
            )
        )
    lines.append("")

    lines.append("## Event summaries")
    lines.append("")
    for event in audit.get("events", []):
        lines.append(f"### {event.get('index')}. {event.get('event_type')}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(event.get("payload_summary", {}), indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def generate(args: argparse.Namespace) -> int:
    artifacts, warnings = collect_artifacts(args)
    if not artifacts:
        print("SafeOps audit trail could not be generated: no readable source artifacts found.", file=sys.stderr)
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        return 2

    audit = build_audit_chain(args.namespace, artifacts)
    verification = verify_audit_chain(audit, recheck_artifacts=True)
    audit["verification"] = verification

    audit_json = Path(args.audit_json)
    audit_md = Path(args.audit_md)
    write_json(audit_json, audit)
    write_markdown(audit, verification, audit_md)

    print("SafeOps tamper-evident audit trail generated.")
    print(f"Events chained: {len(audit.get('events', []))}")
    print(f"Verification valid: {verification.get('valid')}")
    print(f"Chain head: {audit.get('chain_head')}")
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings:
            print(f"- {warning}")
    print(f"JSON audit trail: {audit_json}")
    print(f"Markdown audit trail: {audit_md}")
    return 0 if verification.get("valid") else 1


def verify(args: argparse.Namespace) -> int:
    audit_json = Path(args.audit_json)
    audit, error = load_json(audit_json)
    if error:
        print(f"SafeOps audit verification failed: {error}", file=sys.stderr)
        return 2
    verification = verify_audit_chain(audit, recheck_artifacts=not args.skip_artifact_recheck)

    audit["verification"] = verification
    if args.audit_md:
        write_markdown(audit, verification, Path(args.audit_md))

    print("SafeOps audit trail verification complete.")
    print(f"Verification valid: {verification.get('valid')}")
    print(f"Events checked: {verification.get('checked_events')}")
    print(f"Artifact recheck: {verification.get('artifact_recheck')}")
    for error in verification.get("errors", []):
        print(f"ERROR: {error}")
    for warning in verification.get("warnings", []):
        print(f"WARNING: {warning}")
    return 0 if verification.get("valid") else 1


def tamper_test(args: argparse.Namespace) -> int:
    source = Path(args.audit_json)
    audit, error = load_json(source)
    if error:
        print(f"SafeOps tamper test failed: {error}", file=sys.stderr)
        return 2
    tampered = copy.deepcopy(audit)
    events = tampered.get("events", [])
    if not events:
        print("SafeOps tamper test failed: audit trail has no events", file=sys.stderr)
        return 2
    summary = events[0].setdefault("payload_summary", {})
    summary["tampered_for_test"] = True

    target = Path(args.tampered_audit_json)
    write_json(target, tampered)
    verification = verify_audit_chain(tampered, recheck_artifacts=False)

    print("SafeOps tamper simulation complete.")
    print(f"Tampered audit JSON: {target}")
    print(f"Verification valid after tamper: {verification.get('valid')}")
    for error in verification.get("errors", []):
        print(f"Expected tamper detection: {error}")
    return 0 if not verification.get("valid") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or verify a SafeOps tamper-evident audit trail.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_paths(p: argparse.ArgumentParser) -> None:
        p.add_argument("--namespace", default="demo")
        p.add_argument("--incident-json", default="/tmp/safeops-demo/real-k8s-incidents.json")
        p.add_argument("--plan-json", default="/tmp/safeops-demo/real-k8s-remediation-plan.json")
        p.add_argument("--approval-request-json", default="/tmp/safeops-demo/real-k8s-approval-request.json")
        p.add_argument("--approval-decision-json", default="/tmp/safeops-demo/real-k8s-approval-decision.json")
        p.add_argument("--execution-json", default="/tmp/safeops-demo/real-k8s-execution-record.json")
        p.add_argument("--audit-json", default="/tmp/safeops-demo/real-k8s-audit-trail.json")
        p.add_argument("--audit-md", default="/tmp/safeops-demo/real-k8s-audit-trail.md")

    gen = sub.add_parser("generate", help="Generate a hash-chained audit trail from SafeOps artifacts.")
    add_common_paths(gen)
    gen.set_defaults(func=generate)

    ver = sub.add_parser("verify", help="Verify a hash-chained audit trail.")
    ver.add_argument("--audit-json", default="/tmp/safeops-demo/real-k8s-audit-trail.json")
    ver.add_argument("--audit-md", default="/tmp/safeops-demo/real-k8s-audit-trail.md")
    ver.add_argument("--skip-artifact-recheck", action="store_true")
    ver.set_defaults(func=verify)

    tamper = sub.add_parser("tamper-test", help="Create a tampered copy and prove verification fails.")
    tamper.add_argument("--audit-json", default="/tmp/safeops-demo/real-k8s-audit-trail.json")
    tamper.add_argument("--tampered-audit-json", default="/tmp/safeops-demo/real-k8s-audit-trail-tampered.json")
    tamper.set_defaults(func=tamper_test)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
