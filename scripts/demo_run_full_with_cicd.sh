#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "=== SafeOps full demo with CI/CD connector context ==="

./scripts/demo_setup.sh
./scripts/demo_start_services.sh
./scripts/demo_status.sh
./scripts/demo_reset_healthy.sh
./scripts/demo_break_app.sh

# Collect CI/CD deployment context before SafeOps detection.
# At this point the demo has applied the broken manifest, so the connector can
# correlate the deployment change with the Kubernetes symptoms.
./scripts/demo_cicd_context.sh

./scripts/demo_detect.sh
INCIDENT_ID="$(cat /tmp/safeops-demo/latest_incident_id)"

# Re-run CI/CD context with the real incident ID for a complete record.
./scripts/demo_cicd_context.sh "$INCIDENT_ID"

./scripts/demo_approve_prompt.sh "$INCIDENT_ID"
./scripts/demo_verify.sh
./scripts/demo_report.sh

if [[ -x ./scripts/demo_prevention_recommend.sh ]]; then
  ./scripts/demo_prevention_recommend.sh "$INCIDENT_ID"
else
  echo "Prevention recommendation script not found; skipping Milestone 11 prevention step."
fi

echo

echo "Full CI/CD-aware demo completed."
echo "Generated CI/CD context: /tmp/safeops-demo/latest_cicd_context.json"
echo "Generated CI/CD report:  /tmp/safeops-demo/latest_cicd_context.txt"
echo "To stop backend/executor started by this demo, run: ./scripts/demo_stop_services.sh"
