#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${SAFEOPS_DEMO_STATE_DIR:-/tmp/safeops-demo}"
INCIDENT_FILE="$STATE_DIR/latest_incident_id"
INCIDENT_ID="${1:-}"
cd "$ROOT_DIR"

if [ -z "$INCIDENT_ID" ]; then
  if [ ! -f "$INCIDENT_FILE" ]; then
    echo "No incident ID provided and no saved incident found at $INCIDENT_FILE" >&2
    echo "Run ./scripts/demo_detect.sh first or pass an incident ID." >&2
    exit 1
  fi
  INCIDENT_ID=$(cat "$INCIDENT_FILE")
fi

printf 'Approving smart remediation for incident: %s\n' "$INCIDENT_ID"
./scripts/approve_set_env_fix.sh "$INCIDENT_ID"
