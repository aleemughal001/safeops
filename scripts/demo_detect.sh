#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p /tmp/safeops-demo

OUTPUT_FILE="/tmp/safeops-demo/latest_collector_output.txt"
INCIDENT_FILE="/tmp/safeops-demo/latest_incident_id"

echo "Running SafeOps collector..."
./scripts/run_collector_once.sh | tee "$OUTPUT_FILE"

# The collector prints the newly analyzed incident first.
# Similar incidents may also contain old incident IDs later in the output.
# Use the FIRST incident ID, not the last one.
INCIDENT_ID="$(grep -o "inc_checkout-api_[0-9]\+" "$OUTPUT_FILE" | head -n 1 || true)"

if [ -z "$INCIDENT_ID" ]; then
  echo "ERROR: Could not detect incident_id from collector output."
  echo "Collector output saved to: $OUTPUT_FILE"
  exit 1
fi

echo "$INCIDENT_ID" > "$INCIDENT_FILE"

echo
echo "Detected new incident_id: $INCIDENT_ID"
echo "Saved to: $INCIDENT_FILE"
