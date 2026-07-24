#!/usr/bin/env bash
set -euo pipefail

# Read-only real Kubernetes incident scan.
# Usage:
#   ./scripts/demo_detect_real_k8s_incidents.sh          # all namespaces
#   ./scripts/demo_detect_real_k8s_incidents.sh demo     # one namespace

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${SAFEOPS_OUT_DIR:-/tmp/safeops-demo}"
NAMESPACE="${1:-all}"

mkdir -p "$OUT_DIR"

python3 "$REPO_ROOT/scripts/safeops_real_k8s_detector.py" \
  --namespace "$NAMESPACE" \
  --include-logs \
  --out "$OUT_DIR/real-k8s-incidents.json" \
  --human-report "$OUT_DIR/real-k8s-incidents.md"

echo
echo "Open/read the engineer report:"
echo "  less $OUT_DIR/real-k8s-incidents.md"
echo
echo "JSON artifact:"
echo "  $OUT_DIR/real-k8s-incidents.json"
