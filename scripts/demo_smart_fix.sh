#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

INCIDENT_FILE="/tmp/safeops-demo/latest_incident_id"
OUTPUT_FILE="/tmp/safeops-demo/latest_remediation_output.json"

INCIDENT_ID="${1:-}"
if [ -z "$INCIDENT_ID" ]; then
  if [ ! -f "$INCIDENT_FILE" ]; then
    echo "ERROR: No incident ID provided and $INCIDENT_FILE does not exist."
    echo "Run ./scripts/demo_detect.sh first, or pass an incident ID."
    exit 1
  fi
  INCIDENT_ID="$(cat "$INCIDENT_FILE")"
fi

mkdir -p /tmp/safeops-demo

echo "Approving smart remediation for incident: $INCIDENT_ID"
./scripts/approve_set_env_fix.sh "$INCIDENT_ID" | tee "$OUTPUT_FILE"

echo
echo "Saved remediation output to: $OUTPUT_FILE"
