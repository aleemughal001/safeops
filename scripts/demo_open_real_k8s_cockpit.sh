#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${SAFEOPS_DEMO_OUT:-/tmp/safeops-demo}"
HTML_REPORT="$OUT_DIR/real-k8s-cockpit.html"
PORT="${SAFEOPS_COCKPIT_PORT:-18081}"

if [[ ! -f "$HTML_REPORT" ]]; then
  echo "Missing cockpit file: $HTML_REPORT"
  echo "Generate it first with: ./scripts/demo_real_k8s_cockpit.sh demo"
  exit 1
fi

echo "Serving SafeOps real Kubernetes cockpit from: $OUT_DIR"
echo "Open this URL in Firefox: http://localhost:$PORT/real-k8s-cockpit.html"
echo "Press Ctrl+C to stop the server."
python3 -m http.server "$PORT" --directory "$OUT_DIR"
