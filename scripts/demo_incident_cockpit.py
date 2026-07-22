#!/usr/bin/env python3
"""Generate a polished SafeOps Incident Cockpit HTML report.

The cockpit is still a single local HTML file, but it uses a Tabler-based
admin-dashboard layout via CDN plus local fallback styles. No npm install,
frontend build, or cloud account is required.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
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
PREVENTION_DIR = OUT_DIR / "prevention-pr"


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


def first_value(*values: Any, default: Any = "unknown") -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


def percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "unknown"


def esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def truncate(value: Any, length: int = 120) -> str:
    text = str(value or "")
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "…"


def status_tone(status: Any) -> str:
    if isinstance(status, bool):
        return "success" if status else "danger"
    normalized = str(status or "").strip().lower()
    if normalized in {"healthy", "passed", "pass", "true", "executed", "closed_loop_completed", "approved", "allowed", "valid", "success", "high-correlation"}:
        return "success"
    if normalized in {"failed", "unhealthy", "false", "rejected", "denied", "blocked", "error", "invalid"}:
        return "danger"
    if normalized in {"waiting", "pending", "unknown", "warning", "warn"}:
        return "warning"
    return "info"


def badge(label: Any, status: Any | None = None) -> str:
    tone = status_tone(label if status is None else status)
    return f'<span class="badge bg-{tone}-lt text-{tone}">{esc(label)}</span>'


def card(title: str, body: str, width: str = "col-12") -> str:
    return f"""
      <div class=\"{esc(width)}\">
        <div class=\"card safeops-card h-100\">
          <div class=\"card-header\"><h3 class=\"card-title\">{esc(title)}</h3></div>
          <div class=\"card-body\">{body}</div>
        </div>
      </div>
    """


def kv_table(rows: list[tuple[str, Any]]) -> str:
    html_rows = []
    for label, value in rows:
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) if value else "none"
        html_rows.append(
            f"<tr><th class=\"text-muted fw-semibold\">{esc(label)}</th><td>{esc(value)}</td></tr>"
        )
    return '<div class="table-responsive"><table class="table table-vcenter table-sm mb-0 safeops-kv">' + "".join(html_rows) + "</table></div>"


def code_block(value: Any) -> str:
    return f'<pre class="safeops-code"><code>{esc(value)}</code></pre>'


def command_line(remediation: dict[str, Any] | None) -> str:
    command = get_nested(remediation, ["execution", "kubectl", "command"], [])
    if isinstance(command, list) and command:
        return " ".join(str(part) for part in command)
    return get_nested(remediation, ["execution", "message"], "No command found")


def build_metric(label: str, value: Any, icon: str, tone: str = "primary", helper: str = "") -> str:
    return f"""
      <div class=\"col-sm-6 col-lg-3\">
        <div class=\"card safeops-metric h-100\">
          <div class=\"card-body\">
            <div class=\"d-flex align-items-center\">
              <span class=\"avatar bg-{esc(tone)}-lt text-{esc(tone)} me-3\"><i class=\"ti ti-{esc(icon)}\"></i></span>
              <div>
                <div class=\"text-muted text-uppercase safeops-label\">{esc(label)}</div>
                <div class=\"h2 mb-0\">{value}</div>
                <div class=\"text-muted small\">{esc(helper)}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    """


def build_timeline(steps: list[tuple[str, str, Any, str]]) -> str:
    items = []
    for title, detail, status, icon in steps:
        tone = status_tone(status)
        items.append(
            f"""
            <div class=\"safeops-step\">
              <div class=\"safeops-step-icon bg-{tone}-lt text-{tone}\"><i class=\"ti ti-{esc(icon)}\"></i></div>
              <div class=\"safeops-step-content\">
                <div class=\"fw-bold\">{esc(title)} {badge(status)}</div>
                <div class=\"text-muted\">{esc(detail)}</div>
              </div>
            </div>
            """
        )
    return '<div class="safeops-timeline">' + "".join(items) + "</div>"


def build_verification(remediation: dict[str, Any] | None) -> str:
    checks = get_nested(remediation, ["verification", "checks"], [])
    if not isinstance(checks, list) or not checks:
        return '<div class="text-muted">No verification checks found.</div>'

    rows = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        rows.append(
            f"""
            <tr>
              <td><span class=\"fw-semibold\">{esc(check.get('name', 'unknown'))}</span></td>
              <td>{badge(check.get('status', 'unknown'))}</td>
              <td class=\"text-muted\">{esc(check.get('detail', ''))}</td>
            </tr>
            """
        )
    return f"""
      <div class=\"table-responsive\">
        <table class=\"table table-vcenter table-sm mb-0\">
          <thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    """


def build_evidence(remediation: dict[str, Any] | None) -> str:
    evidence = get_nested(remediation, ["memory", "evidence"], [])
    if not isinstance(evidence, list) or not evidence:
        evidence = get_nested(remediation, ["evidence"], [])
    if not isinstance(evidence, list) or not evidence:
        return '<div class="text-muted">No evidence items found.</div>'

    rows = []
    for idx, item in enumerate(evidence[:20], start=1):
        if not isinstance(item, dict):
            continue
        source = item.get("source", "unknown")
        summary = item.get("summary", "")
        raw_ref = item.get("raw_ref", "")
        tone = "danger" if "BackOff" in str(summary) or "Error" in str(summary) or "missing" in str(summary).lower() else "secondary"
        rows.append(
            f"""
            <tr>
              <td class=\"text-muted\">{idx}</td>
              <td>{badge(source, tone)}</td>
              <td>{esc(summary)}</td>
              <td class=\"text-muted\"><code>{esc(raw_ref)}</code></td>
            </tr>
            """
        )
    more = ""
    if len(evidence) > 20:
        more = f'<div class="text-muted small mt-2">Showing 20 of {len(evidence)} evidence items.</div>'
    return f"""
      <div class=\"table-responsive\">
        <table class=\"table table-vcenter table-sm mb-0\">
          <thead><tr><th>#</th><th>Source</th><th>Evidence summary</th><th>Raw ref</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
      {more}
    """


def build_prevention() -> str:
    files = [
        ("PR title", PREVENTION_DIR / "PR_TITLE.txt"),
        ("PR body", PREVENTION_DIR / "PR_BODY.md"),
        ("Required env policy", PREVENTION_DIR / ".safeops/prevention/checkout-api-required-env.yaml"),
        ("CI required-env check", PREVENTION_DIR / "ci/check_required_env.py"),
        ("GitHub Actions guardrail", PREVENTION_DIR / ".github/workflows/safeops-required-env-check.yml"),
    ]
    rows = []
    for label, path in files:
        status = "available" if path.exists() else "missing"
        rows.append((label, f"{path} ({status})"))
    return kv_table(rows)


def build_raw_artifacts() -> str:
    files = [
        ("Incident Cockpit HTML", HTML_FILE),
        ("Remediation JSON", REMEDIATION_FILE),
        ("CI/CD Context JSON", CICD_FILE),
        ("Slack Card JSON", SLACK_CARD_FILE),
        ("Slack Decision JSON", SLACK_DECISION_FILE),
        ("Audit Verification JSON", AUDIT_FILE),
        ("Prevention PR directory", PREVENTION_DIR),
    ]
    cards = []
    for label, path in files:
        exists = True if label == "Incident Cockpit HTML" else path.exists()
        tone = "success" if exists else "warning"
        cards.append(
            f"""
            <div class=\"col-md-6 col-xl-4\">
              <div class=\"border rounded p-3 h-100\">
                <div class=\"d-flex align-items-center mb-2\">
                  <i class=\"ti ti-file-description me-2 text-{tone}\"></i>
                  <span class=\"fw-semibold\">{esc(label)}</span>
                  <span class=\"ms-auto\">{badge('available' if exists else 'missing', exists)}</span>
                </div>
                <code class=\"text-muted small\">{esc(path)}</code>
              </div>
            </div>
            """
        )
    return '<div class="row g-3">' + "".join(cards) + "</div>"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    remediation = read_json(REMEDIATION_FILE)
    cicd = read_json(CICD_FILE)
    slack_card = read_json(SLACK_CARD_FILE)
    slack_decision = read_json(SLACK_DECISION_FILE)
    audit = fetch_audit_verification()

    incident_id = first_value(get_nested(remediation, ["incident_id"], None), get_nested(cicd, ["incident_id"], None))
    service = first_value(get_nested(remediation, ["memory", "service"], None), get_nested(cicd, ["service"], None))
    namespace = first_value(get_nested(remediation, ["memory", "namespace"], None), get_nested(cicd, ["namespace"], None))
    root_cause = first_value(get_nested(remediation, ["memory", "root_cause"], None), get_nested(slack_card, ["root_cause_summary"], None))
    confidence = percent(get_nested(remediation, ["memory", "confidence"], ""))
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    policy_allowed = get_nested(remediation, ["policy_decision", "allowed"], "unknown")
    execution_status = get_nested(remediation, ["execution", "status"], "unknown")
    verification_status = get_nested(remediation, ["verification", "status"], "unknown")
    audit_valid = get_nested(audit, ["valid"], "unknown")
    slack_action = first_value(get_nested(slack_decision, ["decision"], None), get_nested(slack_decision, ["action"], None))
    cicd_level = get_nested(cicd, ["correlation_level"], "unknown")
    approved_by = first_value(
        get_nested(slack_decision, ["decided_by"], None),
        get_nested(slack_decision, ["approved_by"], None),
        get_nested(remediation, ["approval", "details", "approved_by"], None),
    )

    command = command_line(remediation)
    short_command = truncate(command, 94)

    incident_summary = kv_table([
        ("Incident ID", incident_id),
        ("Service", service),
        ("Namespace", namespace),
        ("Root cause", root_cause),
        ("Confidence", confidence),
        ("Generated at", generated_at),
    ])

    cicd_table = kv_table([
        ("Provider", get_nested(cicd, ["provider"], "unknown")),
        ("Repository", get_nested(cicd, ["repository"], "unknown")),
        ("Branch", get_nested(cicd, ["branch"], "unknown")),
        ("Commit", get_nested(cicd, ["commit_sha"], "unknown")),
        ("Commit subject", get_nested(cicd, ["commit_subject"], "unknown")),
        ("Correlation", cicd_level),
        ("Detected change", get_nested(cicd, ["detected_change"], "unknown")),
        ("Likely contribution", get_nested(cicd, ["likely_contribution"], "unknown")),
    ])

    approval_table = kv_table([
        ("Channel", get_nested(slack_card, ["channel"], "#safeops-approvals")),
        ("Decision", slack_action),
        ("Approved by", approved_by),
        ("Decision time", first_value(get_nested(slack_decision, ["decided_at"], None), get_nested(slack_decision, ["timestamp"], None))),
        ("Risk level", get_nested(slack_card, ["recommended_action", "risk_level"], "low")),
        ("Blast radius", get_nested(slack_card, ["recommended_action", "blast_radius"], "checkout-api in namespace demo only")),
    ])

    policy_table = kv_table([
        ("Policy allowed", policy_allowed),
        ("Reason", get_nested(remediation, ["policy_decision", "reason"], "unknown")),
        ("Action", first_value(get_nested(remediation, ["policy_decision", "action_id"], None), get_nested(remediation, ["execution", "action_id"], None))),
        ("Resource", get_nested(remediation, ["policy_decision", "resource"], "deployment")),
        ("Risk level", get_nested(remediation, ["policy_decision", "risk_level"], "low")),
    ])

    execution_table = kv_table([
        ("Execution status", execution_status),
        ("Mode", get_nested(remediation, ["execution", "mode"], "unknown")),
        ("Message", get_nested(remediation, ["execution", "message"], "unknown")),
        ("Started", get_nested(remediation, ["execution", "started_at"], "unknown")),
        ("Finished", get_nested(remediation, ["execution", "finished_at"], "unknown")),
    ]) + code_block(command)

    audit_table = kv_table([
        ("Audit valid", audit_valid),
        ("Event count", get_nested(audit, ["event_count"], "unknown")),
        ("Latest hash", get_nested(audit, ["latest_hash"], "unknown")),
        ("Audit path", get_nested(audit, ["audit_log_path"], "/tmp/safeops/audit-log.jsonl")),
        ("Issues", get_nested(audit, ["issues"], [])),
    ])

    timeline = build_timeline([
        ("Kubernetes failure detected", f"{service} in namespace {namespace}", "passed", "alert-triangle"),
        ("CI/CD correlated", str(get_nested(cicd, ["detected_change"], "Deployment context collected.")), cicd_level, "git-branch"),
        ("Human approval captured", f"{approved_by} approved via Slack simulation", slack_action, "message-check"),
        ("Policy allowed action", str(get_nested(remediation, ["policy_decision", "reason"], "Policy checked.")), policy_allowed, "shield-check"),
        ("Remediation executed", short_command, execution_status, "terminal-2"),
        ("Recovery verified", "Rollout, environment, and pod readiness checks passed.", verification_status, "heartbeat"),
        ("Audit validated", "Tamper-evident audit chain verified.", audit_valid, "file-check"),
        ("Prevention package generated", "Local prevention PR draft is available for CI/CD guardrail review.", PREVENTION_DIR.exists(), "git-pull-request"),
    ])

    flow_card = card("End-to-end Flow", timeline, "col-12")

    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>SafeOps Incident Cockpit — {esc(incident_id)}</title>
  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0-beta20/dist/css/tabler.min.css\">
  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.28.1/dist/tabler-icons.min.css\">
  <style>
    :root {{
      --safeops-bg: #f3f6fb;
      --safeops-navy: #0f172a;
      --safeops-blue: #2563eb;
      --safeops-card-shadow: 0 14px 38px rgba(15, 23, 42, 0.08);
    }}
    body {{ background: var(--safeops-bg); }}
    .safeops-shell {{ min-height: 100vh; }}
    .safeops-sidebar {{ background: linear-gradient(180deg, #0f172a 0%, #111827 100%); color: #dbeafe; }}
    .safeops-sidebar .navbar-brand {{ color: #fff; letter-spacing: .02em; }}
    .safeops-sidebar .nav-link {{ color: #cbd5e1; border-radius: 10px; margin: 2px 8px; }}
    .safeops-sidebar .nav-link:hover, .safeops-sidebar .nav-link.active {{ color: #fff; background: rgba(37, 99, 235, .22); }}
    .safeops-hero {{ background: radial-gradient(circle at top left, rgba(37, 99, 235, .22), transparent 32%), linear-gradient(135deg, #0f172a, #1e3a8a); color: #fff; border-radius: 22px; padding: 28px; box-shadow: var(--safeops-card-shadow); }}
    .safeops-card, .safeops-metric {{ border: 0; box-shadow: var(--safeops-card-shadow); border-radius: 18px; }}
    .safeops-card .card-header {{ border-bottom: 1px solid rgba(98, 105, 118, .12); background: transparent; }}
    .safeops-label {{ font-size: .72rem; letter-spacing: .08em; }}
    .safeops-code {{ background: #0b1120; color: #e5e7eb; border-radius: 14px; padding: 14px 16px; white-space: pre-wrap; word-break: break-word; margin-top: 14px; }}
    .safeops-kv th {{ width: 170px; }}
    .safeops-timeline {{ position: relative; padding-left: 0; }}
    .safeops-step {{ display: flex; gap: 14px; position: relative; padding-bottom: 18px; }}
    .safeops-step:not(:last-child)::before {{ content: \"\"; position: absolute; left: 18px; top: 38px; bottom: 0; border-left: 2px dashed rgba(98, 105, 118, .22); }}
    .safeops-step-icon {{ z-index: 1; width: 38px; height: 38px; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center; font-size: 20px; flex: 0 0 38px; }}
    .safeops-step-content {{ padding-top: 2px; }}
    .safeops-pill {{ border: 1px solid rgba(255,255,255,.20); color: #dbeafe; border-radius: 999px; padding: 6px 10px; display: inline-flex; align-items: center; gap: 6px; }}
    .table td, .table th {{ vertical-align: top; }}
    code {{ white-space: normal; }}
    @media (max-width: 991px) {{ .safeops-sidebar {{ display: none; }} .safeops-hero {{ border-radius: 0; }} }}
  </style>
</head>
<body>
  <div class=\"page safeops-shell\">
    <aside class=\"navbar navbar-vertical navbar-expand-lg safeops-sidebar\">
      <div class=\"container-fluid\">
        <h1 class=\"navbar-brand navbar-brand-autodark\">
          <i class=\"ti ti-shield-check me-2\"></i>SafeOps
        </h1>
        <div class=\"collapse navbar-collapse show\">
          <ul class=\"navbar-nav pt-lg-3\">
            <li class=\"nav-item\"><a class=\"nav-link active\" href=\"#overview\"><i class=\"ti ti-dashboard me-2\"></i>Overview</a></li>
            <li class=\"nav-item\"><a class=\"nav-link\" href=\"#timeline\"><i class=\"ti ti-route me-2\"></i>Demo Flow</a></li>
            <li class=\"nav-item\"><a class=\"nav-link\" href=\"#evidence\"><i class=\"ti ti-list-search me-2\"></i>Evidence</a></li>
            <li class=\"nav-item\"><a class=\"nav-link\" href=\"#prevention\"><i class=\"ti ti-git-pull-request me-2\"></i>Prevention</a></li>
            <li class=\"nav-item\"><a class=\"nav-link\" href=\"#artifacts\"><i class=\"ti ti-files me-2\"></i>Artifacts</a></li>
          </ul>
        </div>
      </div>
    </aside>

    <div class=\"page-wrapper\">
      <div class=\"page-body\">
        <div class=\"container-xl\">
          <section id=\"overview\" class=\"safeops-hero mb-4\">
            <div class=\"row align-items-center\">
              <div class=\"col-lg-8\">
                <div class=\"safeops-pill mb-3\"><i class=\"ti ti-lock-check\"></i>Policy-gated AI remediation demo</div>
                <h1 class=\"display-6 mb-2\">Incident Cockpit</h1>
                <p class=\"lead mb-3\">Kubernetes evidence, CI/CD correlation, approval, execution, verification, audit, and prevention in one reviewer-friendly dashboard.</p>
                <div class=\"d-flex flex-wrap gap-2\">
                  {badge('resolved' if str(verification_status).lower() == 'healthy' else verification_status, verification_status)}
                  {badge(cicd_level, cicd_level)}
                  {badge('audit valid' if audit_valid is True else audit_valid, audit_valid)}
                  {badge(confidence, 'success')}
                </div>
              </div>
              <div class=\"col-lg-4 mt-4 mt-lg-0\">
                <div class=\"bg-white text-dark rounded-4 p-3 shadow-sm\">
                  <div class=\"text-muted safeops-label text-uppercase\">Incident</div>
                  <div class=\"h3 mb-1\">{esc(incident_id)}</div>
                  <div class=\"text-muted\">{esc(service)} · namespace/{esc(namespace)}</div>
                </div>
              </div>
            </div>
          </section>

          <div class=\"row g-3 mb-4\">
            {build_metric('Verification', badge(verification_status), 'heartbeat', status_tone(verification_status), 'post-fix checks')}
            {build_metric('Audit', badge(audit_valid), 'file-check', status_tone(audit_valid), f"{esc(get_nested(audit, ['event_count'], 'unknown'))} events")}
            {build_metric('Approval', badge(slack_action), 'message-check', status_tone(slack_action), str(approved_by))}
            {build_metric('Confidence', esc(confidence), 'brain', 'primary', 'root-cause match')}
          </div>

          <div class=\"row g-3\">
            {card('Incident Summary', incident_summary, 'col-12')}
            {flow_card}
            <div id=\"timeline\"></div>
            {card('CI/CD Correlation', cicd_table, 'col-lg-6')}
            {card('Slack Approval', approval_table, 'col-lg-6')}
            {card('Policy Decision', policy_table, 'col-lg-6')}
            {card('Executed Remediation', execution_table, 'col-lg-6')}
            {card('Verification Checks', build_verification(remediation), 'col-lg-6')}
            {card('Audit Chain', audit_table, 'col-lg-6')}
            <div id=\"evidence\"></div>
            {card('Kubernetes Evidence', build_evidence(remediation), 'col-12')}
            <div id=\"prevention\"></div>
            {card('Prevention PR Package', build_prevention(), 'col-12')}
            <div id=\"artifacts\"></div>
            {card('Raw Demo Artifacts', build_raw_artifacts(), 'col-12')}
          </div>

          <div class=\"text-center text-muted my-4\">
            Generated locally by SafeOps demo tooling at {esc(generated_at)}. Tabler assets load from CDN for presentation styling; SafeOps data stays local.
          </div>
        </div>
      </div>
    </div>
  </div>
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
