#!/usr/bin/env bash
set -euo pipefail
if [ -z "${1:-}" ]; then
  echo "Usage: ./scripts/approve_real_rollback.sh <incident_id>"
  exit 1
fi
INCIDENT_ID="$1"
curl -s -X POST "http://localhost:8000/approvals" \
  -H "Content-Type: application/json" \
  -d "{
    \"incident_id\": \"$INCIDENT_ID\",
    \"action_id\": \"rollout_undo_deployment\",
    \"approved_by\": \"aleemughal@local.demo\",
    \"approved\": true,
    \"dry_run\": false,
    \"parameters\": {
      \"reason\": \"Real controlled Kubernetes rollback demo\"
    }
  }" | python3 -m json.tool
