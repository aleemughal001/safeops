#!/usr/bin/env python3
"""Insert or refresh the SafeOps real-demo section in README.md.

This script is intentionally conservative:
- It preserves all existing README content.
- It replaces only the marked SafeOps demo block when present.
- It creates README.md.bak before writing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

START = "<!-- SAFEOPS_REAL_DEMO_START -->"
END = "<!-- SAFEOPS_REAL_DEMO_END -->"

SECTION = f"""{START}

## SafeOps real Kubernetes demo

SafeOps is an open-source safety layer for AI-assisted DevOps remediation. The current demo shows a real Kubernetes deployment failure, generates evidence, creates an approval-ready remediation plan, records approval, executes only an allowlisted recovery action, verifies recovery, and produces a tamper-evident audit trail.

**Latest stable demo tag:** `v2.8-investor-evidence-bundle`

### One-command recovery demo

```bash
./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
```

This command runs the full real SafeOps loop:

```text
reset healthy workload
→ inject bad-image rollout failure
→ detect and group the Kubernetes incident
→ generate evidence and remediation plan
→ create approval request and approval decision
→ execute allowlisted rollback only after approval
→ verify the deployment recovered
→ generate and verify tamper-evident audit trail
→ print executive summary
```

Expected final summary:

```text
SafeOps Real Loop Executive Summary
Final cluster state: healthy
Open root incidents after recovery: 0
Executed allowlisted actions: 1
Verified healthy actions: 1
Blocked actions: 0
Audit verification valid: True
Result: PASSED
```

### Investor/customer evidence bundle

```bash
./scripts/demo_create_investor_bundle.sh demo aleemughal001
```

This creates a shareable bundle under `/tmp/safeops-demo/` with:

```text
executive summary
incident evidence report
remediation plan
approval request
approval decision
execution record
tamper-evident audit trail
final cluster state
SHA-256 manifest
zip archive
```

Typical output:

```text
SafeOps investor demo evidence bundle created.
Files packaged: 16
Demo result: PASSED
Audit verification valid: True
Executed allowlisted actions: 1
```

### What the demo proves

- SafeOps can detect a real Kubernetes rollout failure.
- SafeOps groups noisy symptoms into one root incident.
- SafeOps generates evidence-backed remediation plans.
- SafeOps requires human approval before real changes.
- SafeOps executes only typed, allowlisted actions.
- SafeOps verifies recovery after execution.
- SafeOps produces tamper-evident audit records for trust and governance.

### Safety boundaries

SafeOps does **not** run arbitrary shell commands in this demo. The approved executor is limited to safe typed Kubernetes actions, such as rollback, and it records the result for audit review.

{END}
"""


def insert_after_title(readme: str, section: str) -> str:
    lines = readme.splitlines()
    if not lines:
        return section.strip() + "\n"

    # Prefer placing after the first Markdown H1 and any immediate badges/blank lines.
    insert_at = 1
    if lines[0].startswith("# "):
        insert_at = 1
        while insert_at < len(lines) and (
            lines[insert_at].strip() == "" or lines[insert_at].lstrip().startswith("[") or lines[insert_at].lstrip().startswith("!")
        ):
            insert_at += 1
    else:
        insert_at = 0

    return "\n".join(lines[:insert_at]) + "\n\n" + section.strip() + "\n\n" + "\n".join(lines[insert_at:]) + "\n"


def update_readme(path: Path) -> str:
    original = path.read_text(encoding="utf-8") if path.exists() else "# SafeOps\n"
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(original, encoding="utf-8")

    if START in original and END in original:
        before = original.split(START, 1)[0].rstrip()
        after = original.split(END, 1)[1].lstrip()
        updated = before + "\n\n" + SECTION.strip() + "\n\n" + after
    else:
        updated = insert_after_title(original, SECTION)

    path.write_text(updated, encoding="utf-8")
    return f"Updated {path} and wrote backup {backup} at {datetime.now(timezone.utc).isoformat()}"


def main() -> int:
    path = Path("README.md")
    print(update_readme(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
