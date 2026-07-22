#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/demo_incident_cockpit.py"

HTML_FILE="/tmp/safeops-demo/incident-cockpit.html"
if [[ -f "$HTML_FILE" ]]; then
  echo
  echo "Open this file in your browser:"
  echo "  $HTML_FILE"
fi
