#!/usr/bin/env python3
"""Generate a SafeOps fresh-clone validation report."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_FILES = [
    "README.md",
    "scripts/ci_smoke_test.sh",
    "scripts/demo_run_real_safeops_loop.sh",
    "scripts/demo_create_investor_bundle.sh",
    "scripts/demo_release_candidate_check.sh",
    "scripts/demo_prepare_screenshot_package.sh",
    "docs/public-demo-release-candidate.md",
    "docs/demo-screenshots-guide.md",
]

REQUIRED_README_MARKERS = [
    "SafeOps real Kubernetes demo",
    "./scripts/demo_run_real_safeops_loop.sh",
    "./scripts/demo_create_investor_bundle.sh",
    "v2.8-investor-evidence-bundle",
]

EXPECTED_TAGS = [
    "v2.8-investor-evidence-bundle",
    "v2.9-readme-demo-upgrade",
    "v3.0-public-demo-rc",
    "v3.1-demo-screenshot-package",
]


def run_git_tags(repo: Path) -> List[str]:
    result = subprocess.run(
        ["git", "tag", "--list"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def build_report(clone_dir: Path, ci_output: Path, source_repo: Path) -> Dict[str, Any]:
    readme_text = read_text(clone_dir / "README.md")
    ci_text = read_text(ci_output)
    tags = set(run_git_tags(clone_dir))

    missing_files = [f for f in REQUIRED_FILES if not (clone_dir / f).exists()]
    missing_markers = [m for m in REQUIRED_README_MARKERS if m not in readme_text]
    missing_tags = [t for t in EXPECTED_TAGS if t not in tags]

    ci_passed = "== SafeOps CI smoke test complete ==" in ci_text and "All checks passed." in ci_text
    clone_created = clone_dir.exists() and (clone_dir / ".git").exists()

    checks = {
        "clone_created": clone_created,
        "ci_smoke_test_passed": ci_passed,
        "missing_required_files": missing_files,
        "missing_readme_markers": missing_markers,
        "missing_expected_tags": missing_tags,
    }

    ready = clone_created and ci_passed and not missing_files and not missing_markers and not missing_tags

    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=clone_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    ).stdout.strip()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready": ready,
        "source_repo": str(source_repo),
        "clone_dir": str(clone_dir),
        "clone_head": head,
        "ci_output": str(ci_output),
        "checks": checks,
    }


def write_markdown(report: Dict[str, Any], out: Path) -> None:
    checks = report["checks"]
    lines = [
        "# SafeOps Fresh Clone Validation Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Status: `{'ready' if report['ready'] else 'not ready'}`",
        f"Source repo: `{report['source_repo']}`",
        f"Clone dir: `{report['clone_dir']}`",
        f"Clone HEAD: `{report['clone_head']}`",
        "",
        "## Checks",
        "",
        f"- Clone created: `{checks['clone_created']}`",
        f"- CI smoke test passed: `{checks['ci_smoke_test_passed']}`",
        f"- Missing required files: `{len(checks['missing_required_files'])}`",
        f"- Missing README markers: `{len(checks['missing_readme_markers'])}`",
        f"- Missing expected tags: `{len(checks['missing_expected_tags'])}`",
        "",
    ]

    for key, title in [
        ("missing_required_files", "Missing required files"),
        ("missing_readme_markers", "Missing README markers"),
        ("missing_expected_tags", "Missing expected tags"),
    ]:
        items = checks[key]
        if items:
            lines.extend([f"## {title}", ""])
            lines.extend([f"- `{item}`" for item in items])
            lines.append("")

    lines.extend([
        "## CI output",
        "",
        f"Full CI output: `{report['ci_output']}`",
        "",
        "## Result",
        "",
        "This fresh clone is ready for the public demo." if report["ready"] else "This fresh clone is not ready yet.",
        "",
    ])
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SafeOps fresh-clone validation report.")
    parser.add_argument("--clone-dir", required=True)
    parser.add_argument("--ci-output", required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    args = parser.parse_args()

    report = build_report(Path(args.clone_dir), Path(args.ci_output), Path(args.source_repo))
    json_path = Path(args.json_out)
    markdown_path = Path(args.markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, markdown_path)

    print("SafeOps fresh clone validation report generated.")
    print(f"Fresh clone ready: {report['ready']}")
    print(f"Missing required files: {len(report['checks']['missing_required_files'])}")
    print(f"Missing README markers: {len(report['checks']['missing_readme_markers'])}")
    print(f"Missing expected tags: {len(report['checks']['missing_expected_tags'])}")
    print(f"CI smoke test passed: {report['checks']['ci_smoke_test_passed']}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
