#!/usr/bin/env bash
set -euo pipefail

INCIDENT_ID="${1:-}"
BACKEND_URL="${SAFEOPS_BACKEND_URL:-http://localhost:8000}"
ENV_VALUE="${SAFEOPS_REDIS_URL:-redis://redis.demo.svc.cluster.local:6379}"

if [[ -z "$INCIDENT_ID" ]]; then
  echo "Usage: $0 <incident_id>" >&2
  echo "Example: $0 inc_checkout-api_1234567890" >&2
  exit 1
fi

curl -s -X POST "$BACKEND_URL/approvals" \
  -H "Content-Type: application/json" \
  -d "{
    \"incident_id\": \"$INCIDENT_ID\",
    \"action_id\": \"set_env_deployment\",
    \"approved_by\": \"aleemughal@local.demo\",
    \"approved\": true,
    \"dry_run\": false,
    \"parameters\": {
      \"reason\": \"Smart remediation: restore missing REDIS_URL\",
      \"env_name\": \"REDIS_URL\",
      \"env_value\": \"$ENV_VALUE\"
    }
  }" | python3 -m json.tool
