#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SAFEOPS_BACKEND_URL:-http://localhost:8000}"
INCIDENT_ID="inc_checkout_001"

echo "1) Analyze incident"
curl -s -X POST "$BASE_URL/incidents/analyze" \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "inc_checkout_001",
    "service": "checkout-api",
    "namespace": "demo",
    "symptoms": ["Pod is in CrashLoopBackOff"],
    "evidence": [
      {"source":"kubernetes.event","summary":"Back-off restarting failed container checkout-api"},
      {"source":"kubernetes.log","summary":"RuntimeError: Missing required environment variable REDIS_URL"},
      {"source":"git.diff","summary":"Latest commit changed environment variable mapping for checkout-api"}
    ]
  }' | python3 -m json.tool

printf "\n2) Approve + execute + verify + save memory\n"
curl -s -X POST "$BASE_URL/approvals" \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "inc_checkout_001",
    "action_id": "rollout_undo_deployment",
    "approved_by": "demo.engineer@example.com",
    "approved": true,
    "dry_run": true,
    "parameters": {"reason": "SafeOps local closed-loop demo"}
  }' | python3 -m json.tool

printf "\n3) Verify audit chain\n"
curl -s "$BASE_URL/audit-log/verify" | python3 -m json.tool

printf "\n4) Show incident memory\n"
curl -s "$BASE_URL/memory" | python3 -m json.tool
