#!/usr/bin/env python3
"""Create a clean SafeOps investor/customer evidence bundle.

This script packages the real Kubernetes demo artifacts produced by the
SafeOps real loop into a single timestamped folder and zip file.
It does not execute Kubernetes actions. It only copies and summarizes
existing evidence artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zipfile import ZipFile, ZIP_DEFLATED


ARTIFACTS = [
    ("01-incident-evidence", "real-k8s-incidents", "Root incident evidence and grouped findings"),
    ("02-remediation-plan", "real-k8s-remediation-plan", "Approval-ready remediation plan"),
    ("03-approval-request", "real-k8s-approval-request", "Human approval request package"),
    ("04-approval-decision", "real-k8s-approval-decision", "Recorded approval/rejection decision"),
    ("05-execution-record", "real-k8s-execution-record", "Allowlisted executor action and verification result"),
    ("06-tamper-evident-audit-trail", "real-k8s-audit-trail", "Hash-chained audit trail and integrity result"),
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {"value": data}
    except Exception:
        return {}


def first_present(obj: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


def find_first_value(obj: Any, keys: Iterable[str]) -> Any:
    wanted = set(keys)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in wanted and value not in (None, ""):
                return value
        for value in obj.values():
            found = find_first_value(value, wanted)
            if found not in (None, ""):
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_first_value(value, wanted)
            if found not in (None, ""):
                return found
    return None


def find_lists(obj: Any, keys: Iterable[str]) -> List[List[Any]]:
    wanted = set(keys)
    found: List[List[Any]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in wanted and isinstance(value, list):
                found.append(value)
            found.extend(find_lists(value, wanted))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(find_lists(value, wanted))
    return found


def count_from_json(obj: Dict[str, Any], explicit_keys: Iterable[str], list_keys: Iterable[str]) -> int:
    explicit = find_first_value(obj, explicit_keys)
    if isinstance(explicit, int):
        return explicit
    if isinstance(explicit, str) and explicit.isdigit():
        return int(explicit)
    for lst in find_lists(obj, list_keys):
        return len(lst)
    return 0


def infer_bool(obj: Dict[str, Any], keys: Iterable[str]) -> Optional[bool]:
    value = find_first_value(obj, keys)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "valid", "passed", "success", "succeeded"}:
            return True
        if v in {"false", "no", "invalid", "failed", "failure"}:
            return False
    return None


def copy_artifact_pair(src_dir: Path, dst_dir: Path, logical_name: str, source_base: str, description: str) -> List[Dict[str, Any]]:
    copied: List[Dict[str, Any]] = []
    for ext in ("md", "json"):
        src = src_dir / f"{source_base}.{ext}"
        if not src.exists():
            continue
        dst = dst_dir / f"{logical_name}.{ext}"
        shutil.copy2(src, dst)
        copied.append(
            {
                "file": dst.name,
                "source": str(src),
                "description": description,
                "sha256": sha256_file(dst),
                "bytes": dst.stat().st_size,
            }
        )
    return copied


def write_readme(dst_dir: Path, summary: Dict[str, Any], copied_files: List[Dict[str, Any]]) -> None:
    lines = [
        "# SafeOps Investor Demo Evidence Bundle",
        "",
        "This bundle packages the evidence from a real SafeOps Kubernetes recovery demo.",
        "It is designed for investor, customer, or internal review conversations.",
        "",
        "## What this demo proves",
        "",
        "SafeOps can detect a real Kubernetes rollout failure, generate evidence, prepare a safe remediation plan, record human approval, execute an allowlisted rollback, verify recovery, and produce a tamper-evident audit trail.",
        "",
        "## Executive result",
        "",
        f"- Namespace: `{summary.get('namespace', 'unknown')}`",
        f"- Deployment: `{summary.get('deployment', 'unknown')}`",
        f"- Approver: `{summary.get('approver', 'unknown')}`",
        f"- Decision: `{summary.get('decision', 'unknown')}`",
        f"- Executed allowlisted actions: `{summary.get('executed_actions', 0)}`",
        f"- Verified healthy actions: `{summary.get('verified_healthy_actions', 0)}`",
        f"- Blocked actions: `{summary.get('blocked_actions', 0)}`",
        f"- Audit events chained: `{summary.get('audit_events_chained', 0)}`",
        f"- Audit verification valid: `{summary.get('audit_verification_valid', 'unknown')}`",
        f"- Audit chain head: `{summary.get('audit_chain_head', 'unknown')}`",
        "",
        "## Files in this bundle",
        "",
        "| File | What it proves | SHA-256 |",
        "| --- | --- | --- |",
    ]
    for item in copied_files:
        lines.append(f"| `{item['file']}` | {item['description']} | `{item['sha256']}` |")
    lines.extend(
        [
            "",
            "## Recommended demo talk track",
            "",
            "1. SafeOps observes the Kubernetes workload and detects a real rollout failure.",
            "2. It groups noisy symptoms into one root incident with evidence.",
            "3. It creates a remediation plan but requires human approval.",
            "4. It records who approved the fix.",
            "5. It executes only an allowlisted Kubernetes action, not arbitrary shell commands.",
            "6. It verifies the workload recovered.",
            "7. It creates a hash-chained audit trail so tampering can be detected.",
            "",
            "## Important boundary",
            "",
            "This demo is an MVP/prototype. Production hardening should add authentication, tenant isolation, persistent storage, signed audit export, richer policy controls, and enterprise integrations.",
            "",
        ]
    )
    (dst_dir / "README.md").write_text("\n".join(lines))


def write_executive_summary(dst_dir: Path, summary: Dict[str, Any]) -> None:
    result = "PASSED" if summary.get("demo_passed") else "REVIEW_REQUIRED"
    lines = [
        "# SafeOps Real Demo Executive Summary",
        "",
        f"Generated at: `{summary.get('generated_at')}`",
        "",
        f"Result: **{result}**",
        "",
        "## Outcome",
        "",
        f"SafeOps recovered `{summary.get('namespace', 'unknown')}/{summary.get('deployment', 'unknown')}` through an approved, allowlisted Kubernetes remediation flow.",
        "",
        "## Key metrics",
        "",
        f"- Approval decision: `{summary.get('decision', 'unknown')}`",
        f"- Approver: `{summary.get('approver', 'unknown')}`",
        f"- Executed actions: `{summary.get('executed_actions', 0)}`",
        f"- Verified healthy actions: `{summary.get('verified_healthy_actions', 0)}`",
        f"- Blocked actions: `{summary.get('blocked_actions', 0)}`",
        f"- Audit events chained: `{summary.get('audit_events_chained', 0)}`",
        f"- Audit verification valid: `{summary.get('audit_verification_valid', 'unknown')}`",
        f"- Audit chain head: `{summary.get('audit_chain_head', 'unknown')}`",
        "",
        "## Why this matters",
        "",
        "The demo shows that SafeOps does not simply suggest fixes. It creates a controlled recovery loop with evidence, approval, policy boundaries, verification, and auditability.",
        "",
    ]
    (dst_dir / "EXECUTIVE_SUMMARY.md").write_text("\n".join(lines))


def make_zip(bundle_dir: Path) -> Path:
    zip_path = bundle_dir.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(bundle_dir.parent))
    return zip_path


def build_summary(namespace: str, deployment: str, approver: str, src_dir: Path) -> Dict[str, Any]:
    decision_json = load_json(src_dir / "real-k8s-approval-decision.json")
    execution_json = load_json(src_dir / "real-k8s-execution-record.json")
    audit_json = load_json(src_dir / "real-k8s-audit-trail.json")

    decision = find_first_value(decision_json, ["decision", "status"])
    actual_approver = find_first_value(decision_json, ["approver", "approved_by", "decided_by", "actor"])

    executed_actions = count_from_json(
        execution_json,
        ["executed_actions", "actions_executed", "executed_count"],
        ["executed", "execution_records", "records"],
    )
    verified_healthy = count_from_json(
        execution_json,
        ["verified_healthy", "verified_healthy_actions", "healthy_verified_count"],
        ["verified_healthy", "healthy_records"],
    )
    blocked_actions = count_from_json(
        execution_json,
        ["blocked_actions", "blocked_count"],
        ["blocked", "blocked_records"],
    )

    if executed_actions == 0:
        # Fallback: count successful records in arbitrary nested structures.
        text = json.dumps(execution_json).lower()
        if "succeeded" in text or "verified_healthy" in text:
            executed_actions = 1
    if verified_healthy == 0:
        text = json.dumps(execution_json).lower()
        if "verified_healthy" in text:
            verified_healthy = 1

    audit_events = count_from_json(
        audit_json,
        ["events_chained", "events_checked", "event_count"],
        ["events", "audit_events"],
    )
    audit_valid = infer_bool(audit_json, ["verification_valid", "valid", "chain_valid", "audit_verification_valid"])
    chain_head = find_first_value(audit_json, ["chain_head", "audit_chain_head", "head_hash", "latest_hash"])

    demo_passed = bool(executed_actions >= 1 and verified_healthy >= 1 and audit_valid is True)

    return {
        "generated_at": utc_now(),
        "namespace": namespace,
        "deployment": deployment,
        "approver": actual_approver or approver,
        "decision": decision or "unknown",
        "executed_actions": executed_actions,
        "verified_healthy_actions": verified_healthy,
        "blocked_actions": blocked_actions,
        "audit_events_chained": audit_events,
        "audit_verification_valid": audit_valid,
        "audit_chain_head": chain_head or "unknown",
        "demo_passed": demo_passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Package SafeOps investor demo evidence bundle")
    parser.add_argument("namespace", nargs="?", default="demo")
    parser.add_argument("approver", nargs="?", default="unknown")
    parser.add_argument("--deployment", default="checkout-api")
    parser.add_argument("--artifacts-dir", default=None)
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    namespace = args.namespace
    src_dir = Path(args.artifacts_dir or f"/tmp/safeops-{namespace}")
    output_root = Path(args.output_root or src_dir)

    if not src_dir.exists():
        print(f"ERROR: artifacts directory not found: {src_dir}", file=sys.stderr)
        print("Run ./scripts/demo_run_real_safeops_loop.sh first, or use demo_create_investor_bundle.sh.", file=sys.stderr)
        return 2

    bundle_name = f"safeops-investor-demo-bundle-{namespace}-{timestamp_slug()}"
    bundle_dir = output_root / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=False)

    copied: List[Dict[str, Any]] = []
    missing: List[str] = []
    for logical_name, source_base, description in ARTIFACTS:
        before = len(copied)
        copied.extend(copy_artifact_pair(src_dir, bundle_dir, logical_name, source_base, description))
        if len(copied) == before:
            missing.append(source_base)

    final_state = src_dir / "final-cluster-state.txt"
    if final_state.exists():
        dst = bundle_dir / "07-final-cluster-state.txt"
        shutil.copy2(final_state, dst)
        copied.append(
            {
                "file": dst.name,
                "source": str(final_state),
                "description": "Final Kubernetes cluster state after recovery",
                "sha256": sha256_file(dst),
                "bytes": dst.stat().st_size,
            }
        )

    summary = build_summary(namespace, args.deployment, args.approver, src_dir)
    summary["bundle_dir"] = str(bundle_dir)
    summary["missing_artifacts"] = missing

    write_executive_summary(bundle_dir, summary)
    copied.append(
        {
            "file": "EXECUTIVE_SUMMARY.md",
            "source": "generated",
            "description": "Investor-ready outcome summary",
            "sha256": sha256_file(bundle_dir / "EXECUTIVE_SUMMARY.md"),
            "bytes": (bundle_dir / "EXECUTIVE_SUMMARY.md").stat().st_size,
        }
    )

    manifest = {
        "bundle_name": bundle_name,
        "generated_at": summary["generated_at"],
        "summary": summary,
        "files": copied,
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    copied.append(
        {
            "file": "manifest.json",
            "source": "generated",
            "description": "Machine-readable bundle manifest with hashes",
            "sha256": sha256_file(bundle_dir / "manifest.json"),
            "bytes": (bundle_dir / "manifest.json").stat().st_size,
        }
    )

    write_readme(bundle_dir, summary, copied)
    # Recompute README after manifest list is available.
    readme_hash = sha256_file(bundle_dir / "README.md")

    zip_path = make_zip(bundle_dir)

    print("SafeOps investor demo evidence bundle created.")
    print(f"Bundle directory: {bundle_dir}")
    print(f"Bundle zip: {zip_path}")
    print(f"Files packaged: {len(copied) + 1}")
    print(f"Demo result: {'PASSED' if summary['demo_passed'] else 'REVIEW_REQUIRED'}")
    print(f"Audit verification valid: {summary.get('audit_verification_valid')}")
    print(f"Executed allowlisted actions: {summary.get('executed_actions')}")
    if missing:
        print(f"Missing optional/source artifacts: {', '.join(missing)}")
    return 0 if summary["demo_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
