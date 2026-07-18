#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUT_DIR="/tmp/safeops-demo"
mkdir -p "$OUT_DIR"

echo "=== SafeOps full demo with Slack approval simulation ==="

./scripts/demo_setup.sh
./scripts/demo_start_services.sh
./scripts/demo_status.sh
./scripts/demo_reset_healthy.sh
./scripts/demo_break_app.sh

# Show deployment/manifest context before and after detection.
./scripts/demo_cicd_context.sh "pending-detection"
./scripts/demo_detect.sh

INCIDENT_ID="$(cat "$OUT_DIR/latest_incident_id")"
./scripts/demo_cicd_context.sh "$INCIDENT_ID"

# Slack-style approval replaces the terminal-only human approval gate.
./scripts/demo_slack_approval.sh "$INCIDENT_ID"

./scripts/demo_verify.sh
./scripts/demo_report.sh
./scripts/demo_prevention_recommend.sh "$INCIDENT_ID"

echo
echo "Full Slack-aware demo completed."
echo "Generated Slack approval card: $OUT_DIR/latest_slack_approval_card.json"
echo "Generated Slack decision:      $OUT_DIR/latest_slack_approval_decision.json"
echo "Generated CI/CD context:       $OUT_DIR/latest_cicd_context.json"
echo "To stop backend/executor started by this demo, run: ./scripts/demo_stop_services.sh"
