#!/usr/bin/env python3
"""Generate a clean SafeOps CLI report from the latest demo run.

The demo intentionally emits raw JSON/Python-dict data for debugging. This script
turns the latest collector/remediation output plus live Kubernetes status into a
short, presentation-friendly incident report.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from urllib.error import URLError

TMP = Path("/tmp/safeops-demo")
COLLECTOR_OUTPUT = TMP / "latest_collector_output.txt"
REMEDIATION_OUTPUT = TMP / "latest_remediation_output.json"
INCIDENT_FILE = TMP / "latest_incident_id"


def run_cmd(cmd: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as exc:  # pragma: no cover - CLI resilience
        return 1, "", str(exc)


def load_latest_incident() -> dict[str, Any]:
    if not COLLECTOR_OUTPUT.exists():
        return {}

    # The collector prints a Python dict on one line. It can contain old incident
    # IDs inside similar_incidents, so parse the top-level object rather than grep.
    for line in COLLECTOR_OUTPUT.read_text(errors="replace").splitlines():
        text = line.strip()
        if text.startswith("{'incident_id':"):
            try:
                value = ast.literal_eval(text)
                if isinstance(value, dict):
                    return value
            except Exception:
                continue
    return {}


def load_remediation() -> dict[str, Any]:
    if not REMEDIATION_OUTPUT.exists():
        return {}
    try:
        return json.loads(REMEDIATION_OUTPUT.read_text(errors="replace"))
    except json.JSONDecodeError:
        return {}


def fetch_audit() -> dict[str, Any]:
    try:
        with urlopen("http://localhost:8000/audit-log/verify", timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def fmt_bool(value: bool | None) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "UNKNOWN"


def main() -> int:
    incident = load_latest_incident()
    remediation = load_remediation()
    audit = fetch_audit()

    incident_id = (
        incident.get("incident_id")
        or remediation.get("incident_id")
        or (INCIDENT_FILE.read_text().strip() if INCIDENT_FILE.exists() else "unknown")
    )

    service = incident.get("service") or remediation.get("execution", {}).get("service") or "checkout-api"
    namespace = incident.get("namespace") or remediation.get("execution", {}).get("namespace") or "demo"
    root_cause = incident.get("root_cause", "unknown")
    confidence = incident.get("confidence")
    confidence_text = f"{confidence * 100:.0f}%" if isinstance(confidence, (int, float)) else "unknown"

    recommendation = incident.get("recommended_action", {}) if isinstance(incident.get("recommended_action"), dict) else {}
    action_id = recommendation.get("action_id") or remediation.get("execution", {}).get("action_id") or "unknown"
    risk = recommendation.get("risk_level", "unknown")
    blast_radius = recommendation.get("blast_radius", "unknown")

    execution = remediation.get("execution", {}) if isinstance(remediation.get("execution"), dict) else {}
    verification = remediation.get("verification", {}) if isinstance(remediation.get("verification"), dict) else {}
    policy = remediation.get("policy_decision", {}) if isinstance(remediation.get("policy_decision"), dict) else {}

    rc_pods, pods, pods_err = run_cmd(["kubectl", "-n", namespace, "get", "pods", "--no-headers"], timeout=20)
    rc_env, env, env_err = run_cmd([
        "kubectl", "-n", namespace, "get", "deployment", service,
        "-o", "jsonpath={.spec.template.spec.containers[0].env}",
    ], timeout=20)

    print()
    print("SafeOps Incident Report")
    print("=" * 24)
    print(f"Incident ID:        {incident_id}")
    print(f"Service:            {service}")
    print(f"Namespace:          {namespace}")
    print(f"Root cause:         {root_cause}")
    print(f"Confidence:         {confidence_text}")
    print()

    print("Recommendation")
    print("-" * 14)
    print(f"Action:             {action_id}")
    print(f"Risk:               {risk}")
    print(f"Blast radius:       {blast_radius}")
    params = recommendation.get("parameters") or execution.get("parameters") or {}
    if isinstance(params, dict) and params:
        env_name = params.get("env_name")
        env_value = params.get("env_value")
        if env_name and env_value:
            print(f"Config restored:    {env_name}={env_value}")
    print()

    print("Approval / Policy")
    print("-" * 17)
    print(f"Policy allowed:     {fmt_bool(policy.get('allowed'))}")
    print(f"Reason:             {policy.get('reason', 'unknown')}")
    print()

    print("Execution")
    print("-" * 9)
    print(f"Status:             {execution.get('status', 'unknown')}")
    print(f"Mode:               {execution.get('mode', 'unknown')}")
    print(f"Message:            {execution.get('message', 'unknown')}")
    kubectl = execution.get("kubectl", {}) if isinstance(execution.get("kubectl"), dict) else {}
    command = kubectl.get("command")
    if command:
        print(f"Command:            {' '.join(command)}")
    print()

    print("Verification")
    print("-" * 12)
    print(f"Overall:            {verification.get('status', 'unknown')}")
    for check in verification.get("checks", []) if isinstance(verification.get("checks"), list) else []:
        name = check.get("name", "check")
        status = check.get("status", "unknown")
        detail = check.get("detail", "")
        print(f"- {name}: {status} — {detail}")
    print()

    print("Live Kubernetes State")
    print("-" * 21)
    if rc_pods == 0 and pods:
        print(pods)
    else:
        print(f"Unable to read pods: {pods_err or 'unknown error'}")
    print(f"Deployment env:     {env if rc_env == 0 and env else 'unknown'}")
    print()

    print("Audit")
    print("-" * 5)
    if audit:
        print(f"Audit valid:        {fmt_bool(audit.get('valid'))}")
        print(f"Event count:        {audit.get('event_count', 'unknown')}")
        print(f"Audit path:         {audit.get('audit_log_path', 'unknown')}")
    else:
        print("Audit valid:        UNKNOWN (backend not reachable or audit endpoint unavailable)")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
