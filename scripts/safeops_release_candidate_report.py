#!/usr/bin/env python3
"""Generate a SafeOps public demo release-candidate report.

This script is intentionally read-only. It checks that the repository contains
key demo, safety, audit, and investor-bundle assets and writes a concise
Markdown/JSON report suitable for a public demo release-candidate review.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path("/tmp/safeops-demo")
REPORT_JSON = OUT_DIR / "safeops-release-candidate-report.json"
REPORT_MD = OUT_DIR / "safeops-release-candidate-report.md"

REQUIRED_FILES: List[Tuple[str, str]] = [
    ("README.md", "GitHub landing page"),
    (".github/workflows/ci.yml", "GitHub Actions CI workflow"),
    ("docs/security-model.md", "security model"),
    ("docs/action-allowlist.md", "action allowlist"),
    ("docs/audit-log-schema.md", "audit schema"),
    ("docs/real-world-k8s-detector.md", "real Kubernetes detector docs"),
    ("docs/real-k8s-remediation-plan.md", "real remediation planner docs"),
    ("docs/real-remediation-approval-gate.md", "real approval gate docs"),
    ("docs/approved-real-k8s-executor.md", "approved executor docs"),
    ("docs/tamper-evident-real-audit-trail.md", "tamper-evident audit docs"),
    ("docs/one-command-real-safeops-demo.md", "one-command real demo docs"),
    ("docs/investor-demo-evidence-bundle.md", "investor evidence bundle docs"),
    ("scripts/demo_run_real_safeops_loop.sh", "one-command real loop"),
    ("scripts/demo_create_investor_bundle.sh", "investor evidence bundle command"),
    ("scripts/demo_execute_approved_real_fix.sh", "approved real executor flow"),
    ("scripts/demo_real_audit_trail.sh", "tamper-evident audit trail demo"),
]

RECOMMENDED_FILES: List[Tuple[str, str]] = [
    ("docs/demo-recording-checklist.md", "demo recording checklist"),
    ("docs/pitch-package.md", "pitch package"),
    ("docs/real-k8s-cockpit.md", "real Kubernetes cockpit docs"),
    ("examples/evidence-bundle/sample-investor-demo-evidence-bundle.md", "sample evidence bundle README"),
    ("examples/real-loop/sample-one-command-real-safeops-demo.md", "sample one-command demo output"),
    ("examples/audit-trail/sample-tamper-evident-audit-trail.md", "sample tamper-evident audit trail"),
]

EXPECTED_TAGS = [
    "v2.3-real-remediation-plan",
    "v2.4-approval-gate",
    "v2.5-approved-real-executor",
    "v2.6-tamper-evident-audit-trail",
    "v2.7-one-command-real-loop",
    "v2.8-investor-evidence-bundle",
    "v2.9-readme-demo-upgrade",
]


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError as exc:
        return 127, str(exc)


def file_check(items: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rel, label in items:
        path = ROOT / rel
        out.append({
            "path": rel,
            "label": label,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        })
    return out


def has_marker(readme: Path, marker: str) -> bool:
    if not readme.exists():
        return False
    return marker in readme.read_text(errors="replace")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    code, status = run(["git", "status", "--short"])
    working_tree_clean = code == 0 and status.strip() == ""

    _, branch = run(["git", "branch", "--show-current"])
    _, head = run(["git", "log", "-1", "--oneline", "--decorate"])
    _, tags_text = run(["git", "tag", "--list"])
    tags = set(tags_text.splitlines())

    required = file_check(REQUIRED_FILES)
    recommended = file_check(RECOMMENDED_FILES)
    missing_required = [x for x in required if not x["exists"]]
    missing_recommended = [x for x in recommended if not x["exists"]]
    missing_tags = [t for t in EXPECTED_TAGS if t not in tags]

    readme = ROOT / "README.md"
    readme_markers = {
        "real_demo_section": has_marker(readme, "SAFEOPS_REAL_DEMO_START"),
        "one_command_demo": has_marker(readme, "demo_run_real_safeops_loop.sh"),
        "investor_bundle_demo": has_marker(readme, "demo_create_investor_bundle.sh"),
        "latest_v2_8_tag": has_marker(readme, "v2.8-investor-evidence-bundle"),
    }

    rc_ready = (
        not missing_required
        and not missing_tags
        and all(readme_markers.values())
        and working_tree_clean
    )

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_candidate_ready": rc_ready,
        "branch": branch,
        "head": head,
        "working_tree_clean": working_tree_clean,
        "required_files": required,
        "recommended_files": recommended,
        "missing_required_files": missing_required,
        "missing_recommended_files": missing_recommended,
        "expected_tags": EXPECTED_TAGS,
        "missing_tags": missing_tags,
        "readme_markers": readme_markers,
        "recommended_demo_commands": [
            "./scripts/demo_run_real_safeops_loop.sh demo aleemughal001",
            "./scripts/demo_create_investor_bundle.sh demo aleemughal001",
        ],
        "safety_claims": [
            "Read-only evidence collection before remediation.",
            "Human approval is recorded before execution.",
            "Executor supports typed, allowlisted actions instead of arbitrary shell commands.",
            "Recovery is verified after action execution.",
            "Audit trail is hash-chained and tamper-evident.",
        ],
        "known_limitations": [
            "Prototype/local demo, not a production SaaS control plane yet.",
            "Single demo namespace and workload by default.",
            "Rollback is the only approved real Kubernetes action in the demo loop.",
            "No production multi-tenant auth, RBAC UI, billing, or hosted database yet.",
            "Slack/Teams and CI/CD integrations are simulated or file-backed in this demo stage.",
        ],
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    lines = [
        "# SafeOps Public Demo Release Candidate Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Branch: `{branch or 'unknown'}`",
        f"Head: `{head or 'unknown'}`",
        "",
        f"Release candidate ready: `{'YES' if rc_ready else 'NO'}`",
        f"Working tree clean: `{working_tree_clean}`",
        "",
        "## Required public-demo assets",
        "",
    ]
    for item in required:
        status_icon = "✅" if item["exists"] else "❌"
        lines.append(f"- {status_icon} `{item['path']}` — {item['label']}")

    lines += ["", "## Recommended supporting assets", ""]
    for item in recommended:
        status_icon = "✅" if item["exists"] else "⚠️"
        lines.append(f"- {status_icon} `{item['path']}` — {item['label']}")

    lines += ["", "## Expected tags", ""]
    for tag in EXPECTED_TAGS:
        status_icon = "✅" if tag in tags else "❌"
        lines.append(f"- {status_icon} `{tag}`")

    lines += ["", "## README demo markers", ""]
    for key, value in readme_markers.items():
        lines.append(f"- {'✅' if value else '❌'} `{key}`")

    lines += [
        "",
        "## Recommended demo commands",
        "",
        "```bash",
        "./scripts/demo_run_real_safeops_loop.sh demo aleemughal001",
        "./scripts/demo_create_investor_bundle.sh demo aleemughal001",
        "```",
        "",
        "## Safety claims this demo can support",
        "",
    ]
    for claim in report["safety_claims"]:
        lines.append(f"- {claim}")

    lines += ["", "## Known limitations", ""]
    for limitation in report["known_limitations"]:
        lines.append(f"- {limitation}")

    REPORT_MD.write_text("\n".join(lines) + "\n")

    print("SafeOps public demo release-candidate report generated.")
    print(f"Release candidate ready: {rc_ready}")
    print(f"Missing required files: {len(missing_required)}")
    print(f"Missing expected tags: {len(missing_tags)}")
    print(f"Working tree clean: {working_tree_clean}")
    print(f"JSON report: {REPORT_JSON}")
    print(f"Markdown report: {REPORT_MD}")
    return 0 if rc_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
