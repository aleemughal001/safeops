#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat <<'TXT'
=== SafeOps full demo with Incident Cockpit ===
TXT

"$SCRIPT_DIR/demo_run_full_with_slack.sh"

echo
echo "Generating SafeOps Incident Cockpit HTML report..."
"$SCRIPT_DIR/demo_incident_cockpit.sh"

cat <<'TXT'

Full cockpit demo completed.
Generated cockpit: /tmp/safeops-demo/incident-cockpit.html
Generated Slack approval card: /tmp/safeops-demo/latest_slack_approval_card.json
Generated Slack decision:      /tmp/safeops-demo/latest_slack_approval_decision.json
Generated CI/CD context:       /tmp/safeops-demo/latest_cicd_context.json
Generated remediation output:  /tmp/safeops-demo/latest_remediation_output.json
To stop backend/executor started by this demo, run: ./scripts/demo_stop_services.sh
TXT
