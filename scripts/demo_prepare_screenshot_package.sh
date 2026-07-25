#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="${SAFEOPS_ARTIFACT_DIR:-/tmp/safeops-demo}"
TS="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="$ARTIFACT_DIR/safeops-screenshot-package-$TS"

mkdir -p "$OUT_DIR"

cat > "$OUT_DIR/README.md" <<README
# SafeOps Demo Screenshot Package

Generated at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

This package helps prepare visual evidence for an investor/customer demo.

## Screenshots to capture

1. GitHub README top demo section
2. One-command real SafeOps loop final summary
3. Investor evidence bundle output
4. Real Kubernetes cockpit dashboard
5. Execution record
6. Tamper-evident audit trail
7. Release-candidate report

## Main demo commands

\`\`\`bash
./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
./scripts/demo_create_investor_bundle.sh demo aleemughal001
./scripts/demo_release_candidate_check.sh
\`\`\`

## Expected proof points

- Final cluster state: healthy
- Open root incidents after recovery: 0
- Executed allowlisted actions: 1
- Verified healthy actions: 1
- Audit verification valid: True
- Result: PASSED
README

cat > "$OUT_DIR/files-to-open.txt" <<EOF2
Open these files after running the demo:

$ARTIFACT_DIR/real-k8s-incidents.md
$ARTIFACT_DIR/real-k8s-remediation-plan.md
$ARTIFACT_DIR/real-k8s-approval-request.md
$ARTIFACT_DIR/real-k8s-approval-decision.md
$ARTIFACT_DIR/real-k8s-execution-record.md
$ARTIFACT_DIR/real-k8s-audit-trail.md
$ARTIFACT_DIR/safeops-release-candidate-report.md
EOF2

for f in \
  "$ARTIFACT_DIR/real-k8s-incidents.md" \
  "$ARTIFACT_DIR/real-k8s-remediation-plan.md" \
  "$ARTIFACT_DIR/real-k8s-approval-request.md" \
  "$ARTIFACT_DIR/real-k8s-approval-decision.md" \
  "$ARTIFACT_DIR/real-k8s-execution-record.md" \
  "$ARTIFACT_DIR/real-k8s-audit-trail.md" \
  "$ARTIFACT_DIR/safeops-release-candidate-report.md"
do
  if [ -f "$f" ]; then
    cp "$f" "$OUT_DIR/"
  fi
done

python3 - <<PY
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

out_dir = Path("$OUT_DIR")
zip_path = out_dir.with_suffix(".zip")

with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
    for path in sorted(out_dir.rglob("*")):
        if path.is_file():
            zf.write(path, path.relative_to(out_dir.parent))

print(zip_path)
PY

echo
echo "SafeOps screenshot package prepared."
echo "Package directory: $OUT_DIR"
echo "Package zip: $OUT_DIR.zip"
echo
echo "Open checklist:"
echo "  less $OUT_DIR/README.md"
