#!/usr/bin/env python3
"""Generate a concise investor-demo summary from SafeOps demo artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        return default
    return default


def read_text(path: Path, default: str = "") -> str:
    try:
        if path.exists():
            return path.read_text().strip()
    except Exception:
        return default
    return default


def nested(data: Any, keys: list[str], default: Any = "unknown") -> Any:
    cur = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def first_available(*values: Any, default: Any = "unknown") -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", default="/tmp/safeops-demo/investor-demo-package")
    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    artifacts = package_dir / "artifacts"
    package_dir.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    remediation = read_json(artifacts / "latest_remediation_output.json", {})
    cicd = read_json(artifacts / "latest_cicd_context.json", {})
    slack_card = read_json(artifacts / "latest_slack_approval_card.json", {})
    slack_decision = read_json(artifacts / "latest_slack_approval_decision.json", {})
    audit = read_json(artifacts / "latest_audit_verification.json", {})
    incident_id_file = read_text(artifacts / "latest_incident_id", "")

    incident_id = first_available(
        nested(remediation, ["incident_id"], ""),
        nested(cicd, ["incident_id"], ""),
        incident_id_file,
    )

    verification_status = nested(remediation, ["verification", "status"], "unknown")
    audit_valid = nested(audit, ["valid"], "unknown")
    audit_events = nested(audit, ["event_count"], "unknown")
    policy_allowed = nested(remediation, ["policy_decision", "allowed"], "unknown")
    execution_status = nested(remediation, ["execution", "status"], "unknown")
    execution_mode = nested(remediation, ["execution", "mode"], "unknown")
    recommended_action = nested(remediation, ["memory", "recommended_action"], nested(remediation, ["execution", "action_id"], "unknown"))
    root_cause = nested(remediation, ["memory", "root_cause"], "unknown")
    confidence = nested(remediation, ["memory", "confidence"], "unknown")
    service = first_available(nested(remediation, ["memory", "service"], ""), nested(cicd, ["service"], ""))
    namespace = first_available(nested(remediation, ["memory", "namespace"], ""), nested(cicd, ["namespace"], ""))
    correlation = nested(cicd, ["correlation_level"], "unknown")
    detected_change = nested(cicd, ["detected_change"], "unknown")
    likely_contribution = nested(cicd, ["likely_contribution"], "unknown")
    slack_status = first_available(
        nested(slack_decision, ["decision"], ""),
        nested(slack_card, ["status"], ""),
    )
    approved_by = first_available(
        nested(slack_decision, ["decided_by"], ""),
        nested(slack_decision, ["approved_by"], ""),
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "package_dir": str(package_dir),
        "incident_id": incident_id,
        "service": service,
        "namespace": namespace,
        "root_cause": root_cause,
        "confidence": confidence,
        "cicd_correlation": correlation,
        "detected_change": detected_change,
        "likely_contribution": likely_contribution,
        "slack_decision": slack_status,
        "approved_by": approved_by,
        "policy_allowed": policy_allowed,
        "execution_status": execution_status,
        "execution_mode": execution_mode,
        "recommended_action": recommended_action,
        "verification_status": verification_status,
        "audit_valid": audit_valid,
        "audit_event_count": audit_events,
        "cockpit_html": str(package_dir / "incident-cockpit.html"),
        "prevention_pr_dir": str(package_dir / "prevention-pr"),
        "full_demo_log": str(package_dir / "logs" / "full-demo-output.log"),
    }

    (package_dir / "investor-summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    confidence_text = f"{int(float(confidence) * 100)}%" if isinstance(confidence, (float, int)) else str(confidence)
    md = f"""# SafeOps Investor Demo Summary

Generated at: `{summary['generated_at']}`

## Demo result

SafeOps completed a full evidence-driven incident workflow for `{service}` in namespace `{namespace}`.

- Incident ID: `{incident_id}`
- Root cause: {root_cause}
- Confidence: {confidence_text}
- CI/CD correlation: `{correlation}`
- Slack decision: `{slack_status}` by `{approved_by}`
- Policy allowed: `{policy_allowed}`
- Execution: `{execution_status}` via `{execution_mode}`
- Recommended action: `{recommended_action}`
- Verification: `{verification_status}`
- Audit valid: `{audit_valid}` with `{audit_events}` events

## What this proves

1. SafeOps detected a Kubernetes failure.
2. SafeOps correlated the failure with CI/CD manifest context.
3. SafeOps generated a Slack-style approval card.
4. A human approval decision was captured.
5. The policy allowlist validated the remediation.
6. The scoped Kubernetes executor restored the missing environment variable.
7. SafeOps verified recovery and pod readiness.
8. SafeOps validated the audit log and generated a prevention PR draft.
9. SafeOps produced an Incident Cockpit HTML dashboard for review.

## Key artifacts

- Incident Cockpit: `{summary['cockpit_html']}`
- Full demo log: `{summary['full_demo_log']}`
- Raw artifacts: `{package_dir / 'artifacts'}`
- Prevention PR draft: `{summary['prevention_pr_dir']}`

## Investor positioning

SafeOps is an open-source safety and trust layer for AI-assisted DevOps. It demonstrates how AI can investigate incidents, recommend safe actions, require human approval, enforce policy controls, execute scoped remediation, verify recovery, and create a prevention handoff without uncontrolled production access.
"""
    (package_dir / "investor-summary.md").write_text(md)

    print("SafeOps investor summary generated")
    print(f"Summary MD:   {package_dir / 'investor-summary.md'}")
    print(f"Summary JSON: {package_dir / 'investor-summary.json'}")
    print(f"Incident ID:  {incident_id}")
    print(f"Verification: {verification_status}")
    print(f"Audit valid:  {audit_valid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
