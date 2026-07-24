#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-demo}"
OUT_DIR="${SAFEOPS_DEMO_OUT:-/tmp/safeops-demo}"
JSON_REPORT="$OUT_DIR/real-k8s-incidents.json"
MD_REPORT="$OUT_DIR/real-k8s-incidents.md"
HTML_REPORT="$OUT_DIR/real-k8s-cockpit.html"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$OUT_DIR"

"$REPO_ROOT/scripts/demo_detect_real_k8s_incidents.sh" "$NAMESPACE"
python3 "$REPO_ROOT/scripts/safeops_real_k8s_cockpit.py" --input "$JSON_REPORT" --out "$HTML_REPORT"

echo ""
echo "SafeOps real Kubernetes cockpit ready."
echo "Namespace scanned: $NAMESPACE"
echo "JSON evidence: $JSON_REPORT"
echo "Markdown evidence: $MD_REPORT"
echo "HTML cockpit: $HTML_REPORT"
echo ""
echo "Open with:"
echo "  ./scripts/demo_open_real_k8s_cockpit.sh"
