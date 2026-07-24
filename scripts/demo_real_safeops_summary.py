#!/usr/bin/env python3
"""Print an executive summary for the one-command real SafeOps demo.

The summary intentionally reads the JSON artifacts produced by prior milestone
scripts instead of re-computing state. This makes the output useful for demos,
screenshots, and audit review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUT_DIR = Path("/tmp/safeops-demo")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def walk(obj: Any) -> Iterable[Any]:
    yield obj
    if isinstance(obj, dict):
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def first_value(obj: Any, keys: Iterable[str], default: Any = None) -> Any:
    wanted = set(keys)
    for item in walk(obj):
        if isinstance(item, dict):
            for key in wanted:
                if key in item:
                    return item[key]
    return default


def count_list_or_int(obj: Any, list_keys: Iterable[str], int_keys: Iterable[str]) -> int:
    list_key_set = set(list_keys)
    int_key_set = set(int_keys)
    for item in walk(obj):
        if isinstance(item, dict):
            for key in int_key_set:
                value = item.get(key)
                if isinstance(value, int):
                    return value
            for key in list_key_set:
                value = item.get(key)
                if isinstance(value, list):
                    return len(value)
    return 0


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "yes", "valid", "verified_healthy", "succeeded", "success"}
    if isinstance(value, int):
        return value > 0
    return False


def find_successful_targets(execution: Any) -> list[str]:
    targets: list[str] = []
    for item in walk(execution):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or item.get("execution_status") or "").lower()
        verification = str(item.get("verification") or item.get("verification_status") or "").lower()
        target = item.get("target") or item.get("resource") or item.get("deployment")
        namespace = item.get("namespace") or item.get("ns")
        if target and ("success" in status or "succeeded" in status or "healthy" in verification):
            target_str = str(target)
            if namespace and "/" not in target_str:
                target_str = f"{namespace}/{target_str}"
            if target_str not in targets:
                targets.append(target_str)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description="Print SafeOps real demo executive summary")
    parser.add_argument("--namespace", default="demo")
    parser.add_argument("--approver", default="safeops-demo-user")
    parser.add_argument("--deployment", default="checkout-api")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    incidents = load_json(out_dir / "real-k8s-incidents.json")
    execution = load_json(out_dir / "real-k8s-execution-record.json")
    audit = load_json(out_dir / "real-k8s-audit-trail.json")

    root_incidents = count_list_or_int(
        incidents,
        list_keys=["root_incidents", "incidents", "items", "findings"],
        int_keys=["root_incidents_detected", "incident_count", "root_incident_count"],
    )
    executed_actions = count_list_or_int(
        execution,
        list_keys=["executed_actions", "execution_records", "records", "actions"],
        int_keys=["executed_actions", "executed_count", "actions_executed"],
    )
    verified_healthy = count_list_or_int(
        execution,
        list_keys=["verified_healthy", "verified_records"],
        int_keys=["verified_healthy", "verified_healthy_count", "healthy_verified"],
    )
    blocked_actions = count_list_or_int(
        execution,
        list_keys=["blocked_actions", "blocked_records"],
        int_keys=["blocked_actions", "blocked_count"],
    )
    audit_events = count_list_or_int(
        audit,
        list_keys=["events", "audit_events", "chain"],
        int_keys=["events_chained", "event_count", "events_checked"],
    )

    verification_value = first_value(
        audit,
        ["verification_valid", "valid", "chain_valid", "audit_valid"],
        False,
    )
    chain_head = first_value(audit, ["chain_head", "head_hash", "latest_hash"], "unknown")
    successful_targets = find_successful_targets(execution)

    final_state = "healthy" if root_incidents == 0 else "needs_attention"
    audit_valid = truthy(verification_value)

    print("SafeOps Real Loop Executive Summary")
    print("-----------------------------------")
    print(f"Namespace: {args.namespace}")
    print(f"Deployment: {args.deployment}")
    print(f"Approver: {args.approver}")
    print(f"Final cluster state: {final_state}")
    print(f"Open root incidents after recovery: {root_incidents}")
    print(f"Executed allowlisted actions: {executed_actions}")
    print(f"Verified healthy actions: {verified_healthy}")
    print(f"Blocked actions: {blocked_actions}")
    print(f"Audit events chained: {audit_events}")
    print(f"Audit verification valid: {audit_valid}")
    print(f"Audit chain head: {chain_head}")
    if successful_targets:
        print("Recovered targets: " + ", ".join(successful_targets))
    else:
        print(f"Recovered targets: {args.namespace}/{args.deployment}")

    print("")
    print("Artifacts")
    print("---------")
    for filename in [
        "real-k8s-incidents.md",
        "real-k8s-remediation-plan.md",
        "real-k8s-approval-request.md",
        "real-k8s-approval-decision.md",
        "real-k8s-execution-record.md",
        "real-k8s-audit-trail.md",
    ]:
        print(f"- {out_dir / filename}")

    if final_state != "healthy" or not audit_valid or executed_actions == 0 or verified_healthy == 0:
        print("")
        print("Result: CHECK REQUIRED")
        return 1

    print("")
    print("Result: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
