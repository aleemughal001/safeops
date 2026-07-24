#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="${SAFEOPS_DEMO_OUT_DIR:-/tmp/safeops-demo}"
NAMESPACE="${1:-demo}"

mkdir -p "$OUT_DIR"

# Regenerate the latest read-only grouped Kubernetes evidence first.
"$SCRIPT_DIR/demo_detect_real_k8s_incidents.sh" "$NAMESPACE"

python3 "$SCRIPT_DIR/safeops_real_remediation_plan.py" \
  --input "$OUT_DIR/real-k8s-incidents.json" \
  --json-out "$OUT_DIR/real-k8s-remediation-plan.json" \
  --md-out "$OUT_DIR/real-k8s-remediation-plan.md"

cat <<EOF

SafeOps remediation planning ready.
Namespace scanned: $NAMESPACE
Evidence JSON: $OUT_DIR/real-k8s-incidents.json
Remediation JSON: $OUT_DIR/real-k8s-remediation-plan.json
Remediation Markdown: $OUT_DIR/real-k8s-remediation-plan.md

Open/read the plan:
  less $OUT_DIR/real-k8s-remediation-plan.md
EOF
