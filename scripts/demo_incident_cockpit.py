#!/usr/bin/env python3
"""Generate a local SafeOps Incident Cockpit HTML report from demo artifacts.

This script intentionally uses only local demo files from /tmp/safeops-demo and,
when available, the local SafeOps backend audit verification endpoint. It does
not require cloud credentials or any external network access.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

OUT_DIR = Path(os.environ.get("SAFEOPS_DEMO_OUT_DIR", "/tmp/safeops-demo"))
HTML_FILE = OUT_DIR / "incident-cockpit.html"
REMEDIATION_FILE = OUT_DIR / "latest_remediation_output.json"
CICD_FILE = OUT_DIR / "latest_cicd_context.json"
SLACK_CARD_FILE = OUT_DIR / "latest_slack_approval_card.json"
SLACK_DECISION_FILE = OUT_DIR / "latest_slack_approval_decision.json"
AUDIT_FILE = OUT_DIR / "latest_audit_verification.json"


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"_error": f"Invalid JSON in {path}: {exc}"}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def fetch_audit_verification() -> dict[str, Any] | None:
    url = os.environ.get("SAFEOPS_BACKEND_AUDIT_VERIFY_URL", "http://localhost:8000/audit-log/verify")
    try:
        with urllib.request.urlopen(url, timeout=5) as response:  # nosec B310 - local demo endpoint only
            payload = json.loads(response.read().decode("utf-8"))
            write_json(AUDIT_FILE, payload)
            return payload
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return read_json(AUDIT_FILE)


def get_nested(payload: dict[str, Any] | None, path: list[str], default: Any = "") -> Any:
    current: Any = payload or {}
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "unknown"


def esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def status_class(status: Any) -> str:
    normalized = str(status or "").lower()
    if normalized in {"healthy", "passed", "pass", "true", "executed", "closed_loop_completed", "approved", "allowed"}:
        return "ok"
    if normalized in {"failed", "unhealthy", "false", "rejected", "denied", "blocked"}:
        return "bad"
    return "warn"


def badge(label: str, status: Any) -> str:
    return f'<span class="badge {status_class(status)}">{esc(label)}</span>'


def row(label: str, value: Any) -> str:
    return f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>"


def section(title: str, body: str) -> str:
    return f"""
    <section class="card">
      <h2>{esc(title)}</h2>
      {body}
    </section>
    """


def command_line(remediation: dict[str, Any] | None) -> str:
    command = get_nested(remediation, ["execution", "kubectl", "command"], [])
    if isinstance(command, list) and command:
        return " ".join(str(part) for part in command)
    return get_nested(remediation, ["execution", "message"], "No command found")


def build_verification(remediation: dict[str, Any] | None) -> str:
    checks = get_nested(remediation, ["verification", "checks"], [])
    if not isinstance(checks, list) or not checks:
        return "<p class='muted'>No verification checks found.</p>"
    items = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        name = check.get("name", "unknown")
        status = check.get("status", "unknown")
        detail = check.get("detail", "")
        items.append(
            f"<li><strong>{esc(name)}</strong> {badge(status, status)}<br><span class='muted'>{esc(detail)}</span></li>"
        )
    return "<ul class='checklist'>" + "\n".join(items) + "</ul>"


def build_evidence(remediation: dict[str, Any] | None) -> str:
    evidence = get_nested(remediation, ["memory", "evidence"], [])
    if not isinstance(evidence, list) or not evidence:
        evidence = get_nested(remediation, ["evidence"], [])
    if not isinstance(evidence, list) or not evidence:
        return "<p class='muted'>No evidence items found.</p>"

    items = []
    for item in evidence[:12]:
        if not isinstance(item, dict):
            continue
        source = item.get("source", "unknown")
        summary = item.get("summary", "")
        raw_ref = item.get("raw_ref", "")
        items.append(
            "<li>"
            f"<strong>{esc(source)}</strong>"
            f"<p>{esc(summary)}</p>"
            f"<span class='muted'>{esc(raw_ref)}</span>"
            "</li>"
        )
    more = ""
    if len(evidence) > 12:
        more = f"<p class='muted'>Showing 12 of {len(evidence)} evidence items.</p>"
    return "<ul class='evidence'>" + "\n".join(items) + "</ul>" + more


def build_raw_links() -> str:
    files = [
        ("Remediation JSON", REMEDIATION_FILE),
        ("CI/CD Context JSON", CICD_FILE),
        ("Slack Card JSON", SLACK_CARD_FILE),
        ("Slack Decision JSON", SLACK_DECISION_FILE),
        ("Audit Verification JSON", AUDIT_FILE),
    ]
    lis = []
    for label, path in files:
        exists = path.exists()
        suffix = "available" if exists else "missing"
        lis.append(f"<li><strong>{esc(label)}:</strong> <code>{esc(path)}</code> <span class='muted'>({suffix})</span></li>")
    return "<ul>" + "\n".join(lis) + "</ul>"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    remediation = read_json(REMEDIATION_FILE)
    cicd = read_json(CICD_FILE)
    slack_card = read_json(SLACK_CARD_FILE)
    slack_decision = read_json(SLACK_DECISION_FILE)
    audit = fetch_audit_verification()

    incident_id = get_nested(remediation, ["incident_id"], get_nested(cicd, ["incident_id"], "unknown"))
    service = get_nested(remediation, ["memory", "service"], get_nested(cicd, ["service"], "unknown"))
    namespace = get_nested(remediation, ["memory", "namespace"], get_nested(cicd, ["namespace"], "unknown"))
    root_cause = get_nested(remediation, ["memory", "root_cause"], "unknown")
    confidence = percent(get_nested(remediation, ["memory", "confidence"], ""))
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    policy_allowed = get_nested(remediation, ["policy_decision", "allowed"], "unknown")
    execution_status = get_nested(remediation, ["execution", "status"], "unknown")
    verification_status = get_nested(remediation, ["verification", "status"], "unknown")
    audit_valid = get_nested(audit, ["valid"], "unknown")
    slack_action = get_nested(slack_decision, ["decision"], get_nested(slack_decision, ["action"], "unknown"))
    cicd_level = get_nested(cicd, ["correlation_level"], "unknown")

    summary_table = "<table>" + "".join([
        row("Incident ID", incident_id),
        row("Service", service),
        row("Namespace", namespace),
        row("Root cause", root_cause),
        row("Confidence", confidence),
        row("Generated at", generated_at),
    ]) + "</table>"

    cicd_table = "<table>" + "".join([
        row("Provider", get_nested(cicd, ["provider"], "unknown")),
        row("Repository", get_nested(cicd, ["repository"], "unknown")),
        row("Branch", get_nested(cicd, ["branch"], "unknown")),
        row("Commit", get_nested(cicd, ["commit_sha"], "unknown")),
        row("Correlation", get_nested(cicd, ["correlation_level"], "unknown")),
        row("Detected change", get_nested(cicd, ["detected_change"], "unknown")),
        row("Likely contribution", get_nested(cicd, ["likely_contribution"], "unknown")),
    ]) + "</table>"

    slack_table = "<table>" + "".join([
        row("Channel", get_nested(slack_card, ["channel"], "#safeops-approvals")),
        row("Decision", slack_action),
        row("Approved by", get_nested(slack_decision, ["decided_by"], get_nested(slack_decision, ["approved_by"], "unknown"))),
        row("Decision time", get_nested(slack_decision, ["decided_at"], get_nested(slack_decision, ["timestamp"], "unknown"))),
        row("Message status", get_nested(slack_card, ["status"], "unknown")),
    ]) + "</table>"

    policy_table = "<table>" + "".join([
        row("Policy allowed", policy_allowed),
        row("Reason", get_nested(remediation, ["policy_decision", "reason"], "unknown")),
        row("Action", get_nested(remediation, ["policy_decision", "action_id"], "unknown")),
        row("Risk level", get_nested(remediation, ["policy_decision", "risk_level"], "unknown")),
        row("Blast radius", get_nested(remediation, ["recommended_action", "blast_radius"], "checkout-api in namespace demo only")),
    ]) + "</table>"

    execution_table = "<table>" + "".join([
        row("Execution status", execution_status),
        row("Mode", get_nested(remediation, ["execution", "mode"], "unknown")),
        row("Message", get_nested(remediation, ["execution", "message"], "unknown")),
        row("Started", get_nested(remediation, ["execution", "started_at"], "unknown")),
        row("Finished", get_nested(remediation, ["execution", "finished_at"], "unknown")),
    ]) + "</table>" + f"<pre>{esc(command_line(remediation))}</pre>"

    audit_table = "<table>" + "".join([
        row("Audit valid", audit_valid),
        row("Event count", get_nested(audit, ["event_count"], "unknown")),
        row("Latest hash", get_nested(audit, ["latest_hash"], "unknown")),
        row("Audit path", get_nested(audit, ["audit_log_path"], "/tmp/safeops/audit-log.jsonl")),
        row("Issues", get_nested(audit, ["issues"], [])),
    ]) + "</table>"

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SafeOps Incident Cockpit — {esc(incident_id)}</title>
  <style>
    :root {{
      --bg: #f7f8fb;
      --card: #ffffff;
      --text: #172033;
      --muted: #667085;
      --line: #e5e7eb;
      --ok: #0f7a43;
      --ok-bg: #e7f7ee;
      --warn: #996500;
      --warn-bg: #fff4d6;
      --bad: #b42318;
      --bad-bg: #fee4e2;
      --accent: #244eea;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    header {{ background: linear-gradient(135deg, #101828, #1d2b53); color: white; padding: 34px 42px; }}
    header h1 {{ margin: 0 0 8px; font-size: 34px; }}
    header p {{ margin: 0; color: #d0d5dd; max-width: 900px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 18px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 22px; box-shadow: 0 10px 28px rgba(16,24,40,0.05); grid-column: span 12; }}
    .half {{ grid-column: span 6; }}
    .third {{ grid-column: span 4; }}
    h2 {{ margin: 0 0 14px; font-size: 19px; }}
    .metric-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 18px; }}
    .metric {{ background: #f9fafb; border: 1px solid var(--line); border-radius: 14px; padding: 14px; min-width: 160px; }}
    .metric .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .metric .value {{ font-weight: 700; font-size: 18px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); padding: 10px 8px; }}
    th {{ width: 210px; color: var(--muted); font-weight: 600; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #101828; color: #f9fafb; padding: 14px; border-radius: 12px; overflow-x: auto; }}
    .badge {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 5px 10px; font-weight: 700; font-size: 12px; }}
    .ok {{ background: var(--ok-bg); color: var(--ok); }}
    .warn {{ background: var(--warn-bg); color: var(--warn); }}
    .bad {{ background: var(--bad-bg); color: var(--bad); }}
    .muted {{ color: var(--muted); }}
    .checklist, .evidence {{ padding-left: 20px; }}
    .checklist li, .evidence li {{ margin-bottom: 14px; }}
    .evidence p {{ margin: 6px 0; }}
    footer {{ color: var(--muted); text-align: center; padding: 28px; }}
    @media (max-width: 900px) {{ .half, .third {{ grid-column: span 12; }} header {{ padding: 28px; }} main {{ padding: 18px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>SafeOps Incident Cockpit</h1>
    <p>Evidence-driven incident summary for Kubernetes failure, CI/CD correlation, Slack approval, policy-gated remediation, verification, audit, memory, and prevention handoff.</p>
    <div class="metric-row">
      <div class="metric"><div class="label">Incident</div><div class="value">{esc(incident_id)}</div></div>
      <div class="metric"><div class="label">CI/CD</div><div class="value">{badge(cicd_level, cicd_level)}</div></div>
      <div class="metric"><div class="label">Slack</div><div class="value">{badge(slack_action, slack_action)}</div></div>
      <div class="metric"><div class="label">Execution</div><div class="value">{badge(execution_status, execution_status)}</div></div>
      <div class="metric"><div class="label">Verification</div><div class="value">{badge(verification_status, verification_status)}</div></div>
      <div class="metric"><div class="label">Audit</div><div class="value">{badge(str(audit_valid), audit_valid)}</div></div>
    </div>
  </header>
  <main>
    <div class="grid">
      {section("Incident Summary", summary_table)}
      {section("CI/CD Correlation", cicd_table).replace('class="card"', 'class="card half"')}
      {section("Slack Approval", slack_table).replace('class="card"', 'class="card half"')}
      {section("Policy Decision", policy_table).replace('class="card"', 'class="card half"')}
      {section("Executed Remediation", execution_table).replace('class="card"', 'class="card half"')}
      {section("Verification", build_verification(remediation)).replace('class="card"', 'class="card half"')}
      {section("Audit", audit_table).replace('class="card"', 'class="card half"')}
      {section("Kubernetes Evidence", build_evidence(remediation))}
      {section("Raw Demo Artifacts", build_raw_links())}
    </div>
  </main>
  <footer>Generated locally by SafeOps demo tooling. No external services required.</footer>
</body>
</html>
"""

    HTML_FILE.write_text(html_doc)
    print("SafeOps Incident Cockpit generated")
    print(f"HTML: {HTML_FILE}")
    print(f"Incident ID: {incident_id}")
    print(f"Verification: {verification_status}")
    print(f"Audit valid: {audit_valid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
