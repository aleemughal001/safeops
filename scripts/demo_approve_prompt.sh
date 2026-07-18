#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

INCIDENT_FILE="/tmp/safeops-demo/latest_incident_id"

if [ ! -f "$INCIDENT_FILE" ]; then
  echo "ERROR: No latest incident id found at: $INCIDENT_FILE"
  echo "Run: ./scripts/demo_detect.sh"
  exit 1
fi

INCIDENT_ID="$(cat "$INCIDENT_FILE" | tr -d '[:space:]')"

if [ -z "$INCIDENT_ID" ]; then
  echo "ERROR: Incident id file is empty: $INCIDENT_FILE"
  exit 1
fi

cat <<REPORT

SafeOps Human Approval Gate
===========================
Incident ID:        $INCIDENT_ID
Service:            checkout-api
Namespace:          demo
Detected problem:   checkout-api rollout is unhealthy / CrashLoopBackOff symptoms
Likely root cause:  REDIS_URL is missing or misconfigured
Confidence:         89%

Recommended remediation
-----------------------
Action:             set_env_deployment
Change:             Restore REDIS_URL on deployment/checkout-api
Value:              redis://redis.demo.svc.cluster.local:6379
Risk level:         low
Blast radius:       checkout-api in namespace demo only

Safety controls
---------------
Approval required:  yes
Policy check:       must pass before executor runs
Executor mode:      kubernetes
Audit log:          approval, policy, execution, verification, and memory will be recorded

REPORT

if [ "${SAFEOPS_AUTO_APPROVE:-false}" = "true" ]; then
  echo "SAFEOPS_AUTO_APPROVE=true, approving remediation automatically for non-interactive demo."
  APPROVAL="yes"
else
  read -r -p "Approve this remediation? Type 'yes' to continue: " APPROVAL
fi

case "$APPROVAL" in
  yes|YES|y|Y)
    echo
    echo "Approval granted. Sending approved remediation request..."
    ./scripts/demo_smart_fix.sh
    ;;
  *)
    echo
    echo "Approval denied. No remediation was executed."
    echo "The incident remains unresolved until an approved safe action is submitted."
    exit 2
    ;;
esac
