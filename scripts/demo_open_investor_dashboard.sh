#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="/tmp/safeops-demo/investor-demo-package"
HTML_FILE="$PACKAGE_DIR/incident-cockpit.html"

if [[ ! -f "$HTML_FILE" ]]; then
  echo "Incident cockpit not found: $HTML_FILE"
  echo "Run: DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh"
  exit 1
fi

echo "Serving SafeOps investor dashboard from: $PACKAGE_DIR"
echo "Open: http://127.0.0.1:8088/incident-cockpit.html"
python3 -m http.server 8088 --directory "$PACKAGE_DIR"
