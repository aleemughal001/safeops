#!/usr/bin/env python3
"""Generate an engineer-ready SafeOps cockpit from real Kubernetes evidence packs.

Reads the JSON produced by scripts/safeops_real_k8s_detector.py and renders a
single-file HTML cockpit. This is intentionally static and dependency-free so it
works in local demos, CI artifacts, and customer POCs without a web build step.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def badge(text: Any, tone: str = "muted") -> str:
    return f'<span class="badge {esc(tone)}">{esc(text)}</span>'


def severity_tone(severity: str) -> str:
    return {
        "critical": "danger",
        "high": "danger",
        "medium": "warning",
        "low": "info",
        "info": "muted",
    }.get((severity or "").lower(), "muted")


def load_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"report not found: {path}")
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("report JSON must be an object")
    return data


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{round((numerator / denominator) * 100)}%"


def kv(label: str, value: Any) -> str:
    return f"""
    <div class="kv">
      <div class="kv-label">{esc(label)}</div>
      <div class="kv-value">{esc(value)}</div>
    </div>
    """


def list_items(items: Iterable[Any]) -> str:
    values = [x for x in items if x]
    if not values:
        return '<p class="empty-small">No items recorded.</p>'
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in values) + "</ul>"


def render_summary(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {}) or {}
    root = int(summary.get("root_incidents") or summary.get("total_incidents") or 0)
    raw = int(summary.get("raw_findings") or 0)
    by_sev = summary.get("by_severity", {}) or {}
    by_cat = summary.get("by_category", {}) or {}
    counts = report.get("cluster_snapshot_counts", {}) or {}
    mode = report.get("mode", "unknown")
    scope = report.get("namespace_scope", "unknown")
    context = report.get("kube_context") or "current"
    generated = report.get("generated_at", "unknown")

    status_class = "healthy" if root == 0 else "active"
    status_text = "No active incidents" if root == 0 else f"{root} active root incident{'s' if root != 1 else ''}"

    severity_badges = " ".join(
        badge(f"{sev}: {count}", severity_tone(sev)) for sev, count in sorted(by_sev.items(), key=lambda item: SEVERITY_ORDER.get(item[0], 99))
    ) or badge("none", "success")
    category_badges = " ".join(badge(f"{cat}: {count}", "info") for cat, count in sorted(by_cat.items())) or badge("none", "success")

    return f"""
    <section class="hero {status_class}">
      <div>
        <p class="eyebrow">SafeOps Real Kubernetes Cockpit</p>
        <h1>{esc(status_text)}</h1>
        <p class="subtitle">Read-only incident grouping from live Kubernetes evidence. Built for engineer review before any remediation is approved.</p>
      </div>
      <div class="hero-side">
        <div class="big-number">{root}</div>
        <div class="big-label">root incidents</div>
      </div>
    </section>

    <section class="grid metrics">
      <div class="card metric"><div class="metric-label">Root incidents</div><div class="metric-value">{root}</div></div>
      <div class="card metric"><div class="metric-label">Raw findings grouped</div><div class="metric-value">{raw}</div></div>
      <div class="card metric"><div class="metric-label">Namespace scope</div><div class="metric-value small">{esc(scope)}</div></div>
      <div class="card metric"><div class="metric-label">Kube context</div><div class="metric-value small">{esc(context)}</div></div>
    </section>

    <section class="grid two">
      <div class="card">
        <h2>Scan metadata</h2>
        {kv('Generated at', generated)}
        {kv('Mode', mode)}
        {kv('Pods scanned', counts.get('pods', 0))}
        {kv('Deployments scanned', counts.get('deployments', 0))}
        {kv('Services scanned', counts.get('services', 0))}
        {kv('Events scanned', counts.get('events', 0))}
      </div>
      <div class="card">
        <h2>Incident distribution</h2>
        <div class="badge-row">{severity_badges}</div>
        <div class="badge-row">{category_badges}</div>
        <p class="note">Raw Kubernetes symptoms are grouped into root incidents so engineers see one diagnosis instead of alert noise.</p>
      </div>
    </section>
    """


def render_evidence_item(item: Dict[str, Any]) -> str:
    events = item.get("events") or []
    event_html = ""
    if events:
        event_html = '<div class="subsection-title">High-signal events</div>' + "".join(
            f"""
            <div class="event">
              <span class="event-reason">{esc(ev.get('reason'))}</span>
              <span>{esc(ev.get('message'))}</span>
            </div>
            """
            for ev in events[:4]
        )

    detail_blocks: List[str] = []
    for key, label in [
        ("pod_status", "Pod status"),
        ("deployment_status", "Deployment status"),
        ("service_status", "Service status"),
    ]:
        if item.get(key):
            detail_blocks.append(
                f"<details><summary>{esc(label)}</summary><pre>{esc(json.dumps(item.get(key), indent=2, sort_keys=True))}</pre></details>"
            )
    if item.get("sanitized_logs_tail"):
        detail_blocks.append(f"<details><summary>Sanitized logs tail</summary><pre>{esc(item.get('sanitized_logs_tail'))}</pre></details>")

    return f"""
    <div class="evidence-item">
      <div class="evidence-head">
        <strong>{esc(item.get('kind'))}: {esc(item.get('namespace'))}/{esc(item.get('name'))}</strong>
        <span>{badge(item.get('reason'), 'warning')} {badge(item.get('category'), 'info')}</span>
      </div>
      <p>{esc(item.get('message'))}</p>
      {event_html}
      {''.join(detail_blocks)}
    </div>
    """


def render_incident(incident: Dict[str, Any], index: int) -> str:
    severity = (incident.get("severity") or "info").lower()
    evidence_pack = incident.get("evidence_pack", {}) or {}
    evidence_chain = evidence_pack.get("evidence_chain", []) or []
    affected_resources = evidence_pack.get("affected_resources", []) or []
    reasons = incident.get("reasons", []) or []
    raw_count = evidence_pack.get("raw_finding_count", 0)

    evidence_html = "".join(render_evidence_item(item) for item in evidence_chain) or '<p class="empty-small">No evidence chain available.</p>'

    return f"""
    <article class="incident-card severity-{esc(severity)}">
      <div class="incident-topline">
        <div>
          <p class="eyebrow">Root incident #{index}</p>
          <h2>{esc(incident.get('title'))}</h2>
          <p class="resource">{esc(incident.get('namespace'))}/{esc(incident.get('affected_workload'))}</p>
        </div>
        <div class="incident-badges">
          {badge(severity.upper(), severity_tone(severity))}
          {badge(incident.get('primary_category'), 'info')}
          {badge(f'{raw_count} raw findings', 'muted')}
        </div>
      </div>

      <div class="grid three compact">
        <div class="mini"><span>Incident ID</span><strong>{esc(incident.get('incident_id'))}</strong></div>
        <div class="mini"><span>Approval required</span><strong>{esc(incident.get('approval_required'))}</strong></div>
        <div class="mini"><span>Detector can execute</span><strong>{esc(incident.get('execute_allowed_by_detector'))}</strong></div>
      </div>

      <div class="section-block">
        <h3>Root-cause hypothesis</h3>
        <p>{esc(incident.get('root_cause_hypothesis'))}</p>
      </div>

      <div class="section-block highlight">
        <h3>Recommended safe action</h3>
        <p>{esc(incident.get('recommended_safe_action'))}</p>
      </div>

      <div class="grid two">
        <div class="section-block">
          <h3>Grouped reasons</h3>
          <div class="badge-row">{" ".join(badge(reason, 'warning') for reason in reasons) or badge('none', 'muted')}</div>
        </div>
        <div class="section-block">
          <h3>Affected resources</h3>
          <div class="badge-row">{" ".join(badge(res, 'muted') for res in affected_resources) or badge('unknown', 'muted')}</div>
        </div>
      </div>

      <div class="grid two">
        <div class="section-block">
          <h3>Safe action options</h3>
          {list_items(incident.get('safe_action_options', []))}
        </div>
        <div class="section-block">
          <h3>Verification plan</h3>
          {list_items(incident.get('verification_plan', []))}
        </div>
      </div>

      <div class="section-block">
        <h3>Evidence chain</h3>
        {evidence_html}
      </div>

      <div class="section-block">
        <h3>Prevention ideas</h3>
        {list_items(incident.get('prevention_ideas', []))}
      </div>
    </article>
    """


def render_empty_state() -> str:
    return """
    <section class="card empty-state">
      <div class="empty-icon">✓</div>
      <h2>No active abnormal Kubernetes incidents detected</h2>
      <p>The detector found no grouped root incidents in this scan. This is the expected result for a healthy namespace.</p>
    </section>
    """


def render_raw_findings(report: Dict[str, Any]) -> str:
    raw = report.get("raw_findings", []) or []
    if not raw:
        return """
        <section class="card">
          <h2>Raw Kubernetes findings</h2>
          <p class="empty-small">No raw findings in this scan.</p>
        </section>
        """
    rows = "".join(
        f"""
        <tr>
          <td>{esc(f.get('severity'))}</td>
          <td>{esc(f.get('kind'))}</td>
          <td>{esc(f.get('namespace'))}/{esc(f.get('name'))}</td>
          <td>{esc(f.get('reason'))}</td>
          <td>{esc(f.get('category'))}</td>
        </tr>
        """
        for f in raw
    )
    return f"""
    <section class="card">
      <h2>Raw Kubernetes findings</h2>
      <p class="note">Kept for auditability. Root incidents above are the engineer-facing grouped view.</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Severity</th><th>Kind</th><th>Resource</th><th>Reason</th><th>Category</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>
    """


def render_html(report: Dict[str, Any]) -> str:
    root_incidents = sorted(
        report.get("root_incidents", []) or [],
        key=lambda inc: (SEVERITY_ORDER.get((inc.get("severity") or "info").lower(), 99), inc.get("namespace", ""), inc.get("affected_workload", "")),
    )
    incidents_html = "".join(render_incident(inc, i + 1) for i, inc in enumerate(root_incidents)) if root_incidents else render_empty_state()
    safety_note = report.get("safety_note", "This cockpit is read-only and does not execute remediation actions.")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SafeOps Real Kubernetes Cockpit</title>
  <style>
    :root {{
      --bg: #0b1120; --panel: #111827; --panel-2: #162033; --text: #e5e7eb; --muted: #9ca3af;
      --line: #293548; --blue: #60a5fa; --green: #34d399; --yellow: #fbbf24; --red: #f87171; --cyan: #22d3ee;
      --shadow: 0 24px 80px rgba(0,0,0,.35);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at top left, #162447 0, var(--bg) 42%); color: var(--text); }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 18px 54px; }}
    .topbar {{ display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 18px; }}
    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .logo {{ width: 38px; height: 38px; display: grid; place-items: center; border-radius: 12px; background: linear-gradient(135deg, var(--blue), var(--cyan)); color: #07111f; font-weight: 900; }}
    .brand-title {{ font-size: 15px; color: var(--muted); }}
    .brand-title strong {{ display: block; color: var(--text); font-size: 20px; }}
    .timestamp {{ color: var(--muted); font-size: 13px; text-align: right; }}
    .hero {{ display: flex; justify-content: space-between; gap: 20px; padding: 30px; border-radius: 22px; box-shadow: var(--shadow); margin-bottom: 18px; border: 1px solid rgba(255,255,255,.08); }}
    .hero.healthy {{ background: linear-gradient(135deg, rgba(16,185,129,.20), rgba(17,24,39,.95)); }}
    .hero.active {{ background: linear-gradient(135deg, rgba(251,191,36,.22), rgba(17,24,39,.95)); }}
    .eyebrow {{ margin: 0 0 8px; color: var(--cyan); text-transform: uppercase; letter-spacing: .12em; font-size: 12px; font-weight: 800; }}
    h1 {{ margin: 0; font-size: clamp(28px, 5vw, 48px); line-height: 1.05; }}
    h2 {{ margin: 0 0 12px; font-size: 22px; }}
    h3 {{ margin: 0 0 10px; font-size: 15px; color: #dbeafe; }}
    p {{ color: #d1d5db; line-height: 1.55; }}
    .subtitle {{ max-width: 760px; margin-bottom: 0; }}
    .hero-side {{ min-width: 150px; text-align: center; padding: 16px; border-radius: 18px; background: rgba(255,255,255,.06); }}
    .big-number {{ font-size: 54px; font-weight: 900; }}
    .big-label {{ color: var(--muted); font-size: 13px; }}
    .grid {{ display: grid; gap: 16px; }}
    .metrics {{ grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 16px; }}
    .two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .compact {{ margin: 14px 0; }}
    .card, .incident-card, .section-block {{ background: rgba(17,24,39,.88); border: 1px solid var(--line); border-radius: 18px; padding: 18px; }}
    .card {{ margin-bottom: 16px; }}
    .metric-label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .metric-value {{ font-size: 34px; font-weight: 900; margin-top: 5px; }}
    .metric-value.small {{ font-size: 18px; overflow-wrap: anywhere; }}
    .kv {{ display: flex; justify-content: space-between; gap: 14px; border-bottom: 1px solid rgba(255,255,255,.06); padding: 8px 0; }}
    .kv-label {{ color: var(--muted); }}
    .kv-value {{ text-align: right; overflow-wrap: anywhere; }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
    .badge {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 5px 9px; font-size: 12px; font-weight: 800; border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.06); color: var(--text); }}
    .badge.success {{ background: rgba(16,185,129,.16); color: #a7f3d0; }}
    .badge.warning {{ background: rgba(251,191,36,.16); color: #fde68a; }}
    .badge.danger {{ background: rgba(248,113,113,.18); color: #fecaca; }}
    .badge.info {{ background: rgba(96,165,250,.18); color: #bfdbfe; }}
    .badge.muted {{ color: #d1d5db; }}
    .note, .empty-small {{ color: var(--muted); font-size: 14px; }}
    .incident-card {{ margin: 18px 0; border-left: 5px solid var(--blue); }}
    .incident-card.severity-critical, .incident-card.severity-high {{ border-left-color: var(--red); }}
    .incident-card.severity-medium {{ border-left-color: var(--yellow); }}
    .incident-topline {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }}
    .resource {{ margin-top: -4px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .incident-badges {{ display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }}
    .mini {{ background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; padding: 12px; min-width: 0; }}
    .mini span {{ color: var(--muted); font-size: 12px; display: block; margin-bottom: 6px; }}
    .mini strong {{ overflow-wrap: anywhere; }}
    .highlight {{ background: rgba(96,165,250,.10); border-color: rgba(96,165,250,.35); }}
    ul {{ margin-top: 0; padding-left: 20px; }}
    li {{ margin: 7px 0; color: #d1d5db; }}
    .evidence-item {{ border: 1px solid rgba(255,255,255,.09); background: rgba(255,255,255,.035); border-radius: 14px; padding: 14px; margin: 12px 0; }}
    .evidence-head {{ display: flex; justify-content: space-between; gap: 10px; align-items: center; }}
    .subsection-title {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; margin: 12px 0 6px; }}
    .event {{ padding: 8px 0; border-top: 1px solid rgba(255,255,255,.06); color: #d1d5db; }}
    .event-reason {{ color: var(--yellow); font-weight: 800; margin-right: 8px; }}
    details {{ margin-top: 10px; }}
    summary {{ cursor: pointer; color: #bfdbfe; font-weight: 700; }}
    pre {{ white-space: pre-wrap; overflow-x: auto; background: #050b16; border: 1px solid rgba(255,255,255,.08); padding: 12px; border-radius: 12px; color: #d1d5db; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,.08); text-align: left; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .empty-state {{ text-align: center; padding: 42px 18px; }}
    .empty-icon {{ width: 72px; height: 72px; display: grid; place-items: center; margin: 0 auto 14px; border-radius: 50%; background: rgba(16,185,129,.16); color: #a7f3d0; font-size: 42px; }}
    footer {{ color: var(--muted); font-size: 13px; margin-top: 24px; text-align: center; }}
    @media (max-width: 860px) {{ .metrics, .two, .three {{ grid-template-columns: 1fr; }} .hero, .incident-topline {{ flex-direction: column; }} .hero-side {{ width: 100%; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="topbar">
      <div class="brand"><div class="logo">SO</div><div class="brand-title"><strong>SafeOps</strong>Real Kubernetes Evidence Cockpit</div></div>
      <div class="timestamp">Rendered: {esc(now_iso())}<br>Schema: {esc(report.get('schema_version'))}</div>
    </header>

    {render_summary(report)}
    {incidents_html}
    {render_raw_findings(report)}

    <section class="card">
      <h2>Safety boundary</h2>
      <p>{esc(safety_note)}</p>
      <div class="badge-row">{badge('read-only detector', 'success')} {badge('approval required', 'warning')} {badge('no arbitrary shell execution', 'danger')}</div>
    </section>

    <footer>SafeOps Cockpit generated from /tmp/safeops-demo/real-k8s-incidents.json</footer>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a SafeOps HTML cockpit from a real Kubernetes incident evidence JSON report.")
    parser.add_argument("--input", default="/tmp/safeops-demo/real-k8s-incidents.json", help="Input JSON evidence report.")
    parser.add_argument("--out", default="/tmp/safeops-demo/real-k8s-cockpit.html", help="Output HTML cockpit path.")
    args = parser.parse_args()

    report = load_report(Path(args.input))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(report))
    print(f"SafeOps real Kubernetes cockpit generated: {out}")
    print(f"Input evidence report: {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
