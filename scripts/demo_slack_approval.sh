#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUT_DIR="/tmp/safeops-demo"
mkdir -p "$OUT_DIR"

INCIDENT_ID="${1:-}"
if [[ -z "$INCIDENT_ID" && -f "$OUT_DIR/latest_incident_id" ]]; then
  INCIDENT_ID="$(cat "$OUT_DIR/latest_incident_id")"
fi
if [[ -z "$INCIDENT_ID" ]]; then
  echo "No incident id provided and $OUT_DIR/latest_incident_id was not found." >&2
  exit 1
fi

SERVICE="${SAFEOPS_SERVICE:-checkout-api}"
NAMESPACE="${SAFEOPS_NAMESPACE:-demo}"
REQUIRED_ENV="${SAFEOPS_REQUIRED_ENV:-REDIS_URL}"
EXPECTED_VALUE="${SAFEOPS_REQUIRED_ENV_VALUE:-redis://redis.demo.svc.cluster.local:6379}"
APPROVER="${SAFEOPS_SLACK_APPROVER:-aleemughal@local.demo}"
CHANNEL="${SAFEOPS_SLACK_CHANNEL:-#safeops-approvals}"
NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

CICD_JSON="$OUT_DIR/latest_cicd_context.json"
SLACK_JSON="$OUT_DIR/latest_slack_approval_card.json"
SLACK_TXT="$OUT_DIR/latest_slack_approval_card.txt"
DECISION_JSON="$OUT_DIR/latest_slack_approval_decision.json"

# Defaults if CI/CD context has not been generated yet.
DETECTED_CHANGE="CI/CD context not available for this incident."
LIKELY_CONTRIBUTION="SafeOps will proceed using Kubernetes evidence only."
CORRELATION_LEVEL="unknown"

if [[ -f "$CICD_JSON" ]]; then
  readarray -t cicd_lines < <(python3 - <<PY
import json
from pathlib import Path
p = Path("$CICD_JSON")
try:
    data = json.loads(p.read_text())
except Exception:
    data = {}
print(data.get("detected_change", "CI/CD context not available for this incident."))
print(data.get("likely_contribution", "SafeOps will proceed using Kubernetes evidence only."))
print(data.get("correlation_level", "unknown"))
PY
)
  DETECTED_CHANGE="${cicd_lines[0]:-$DETECTED_CHANGE}"
  LIKELY_CONTRIBUTION="${cicd_lines[1]:-$LIKELY_CONTRIBUTION}"
  CORRELATION_LEVEL="${cicd_lines[2]:-$CORRELATION_LEVEL}"
fi

cat > "$SLACK_TXT" <<TXT
SafeOps Slack Approval Simulation
=================================
Channel:            $CHANNEL
Timestamp:          $NOW_UTC
Incident ID:        $INCIDENT_ID
Service:            $SERVICE
Namespace:          $NAMESPACE
Severity:           high
Status:             waiting_for_human_approval

Slack message preview
---------------------
🚨 SafeOps incident detected: $SERVICE is failing in namespace $NAMESPACE

Likely root cause:
REDIS_URL is missing or misconfigured after a deployment.

CI/CD correlation:
$DETECTED_CHANGE
$LIKELY_CONTRIBUTION
Correlation level: $CORRELATION_LEVEL

Recommended safe fix:
Restore $REQUIRED_ENV on deployment/$SERVICE.

Proposed command:
kubectl -n $NAMESPACE set env deployment/$SERVICE $REQUIRED_ENV=$EXPECTED_VALUE

Safety controls:
- Human approval required
- Policy allowlist must pass
- Executor scoped to namespace=$NAMESPACE and service=$SERVICE
- Verification checks rollout status, deployment env, and pod readiness
- Audit log records approval, policy, execution, verification, and memory

Buttons:
[Approve Fix] [Reject] [Create Prevention PR Instead]
TXT

python3 - <<PY
import json
from pathlib import Path
payload = {
    "schema_version": "safeops.slack_approval.v1",
    "channel": "$CHANNEL",
    "created_at": "$NOW_UTC",
    "incident_id": "$INCIDENT_ID",
    "service": "$SERVICE",
    "namespace": "$NAMESPACE",
    "severity": "high",
    "status": "waiting_for_human_approval",
    "root_cause_summary": "REDIS_URL is missing or misconfigured after a deployment.",
    "cicd_context": {
        "detected_change": "$DETECTED_CHANGE",
        "likely_contribution": "$LIKELY_CONTRIBUTION",
        "correlation_level": "$CORRELATION_LEVEL"
    },
    "recommended_action": {
        "action_id": "set_env_deployment",
        "description": "Restore REDIS_URL on deployment/checkout-api.",
        "risk_level": "low",
        "blast_radius": "checkout-api in namespace demo only",
        "command_preview": "kubectl -n $NAMESPACE set env deployment/$SERVICE $REQUIRED_ENV=$EXPECTED_VALUE"
    },
    "buttons": ["approve_fix", "reject", "create_prevention_pr_instead"],
    "safety_controls": [
        "human_approval_required",
        "policy_allowlist_required",
        "scoped_executor",
        "post_action_verification",
        "tamper_evident_audit"
    ]
}
Path("$SLACK_JSON").write_text(json.dumps(payload, indent=2) + "\n")
PY

cat "$SLACK_TXT"

echo
read -r -p "Simulate Slack approval? Type 'approve' or 'yes' to click [Approve Fix]: " DECISION

if [[ "$DECISION" != "approve" && "$DECISION" != "yes" ]]; then
  python3 - <<PY
import json
from pathlib import Path
payload = {
    "schema_version": "safeops.slack_decision.v1",
    "incident_id": "$INCIDENT_ID",
    "channel": "$CHANNEL",
    "decided_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "decided_by": "$APPROVER",
    "decision": "rejected",
    "reason": "Slack simulation did not receive approve/yes."
}
Path("$DECISION_JSON").write_text(json.dumps(payload, indent=2) + "\n")
PY
  echo
  echo "Slack approval rejected. No remediation was executed."
  echo "Decision saved to: $DECISION_JSON"
  exit 1
fi

python3 - <<PY
import json
from pathlib import Path
payload = {
    "schema_version": "safeops.slack_decision.v1",
    "incident_id": "$INCIDENT_ID",
    "channel": "$CHANNEL",
    "decided_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "decided_by": "$APPROVER",
    "decision": "approved",
    "button_clicked": "approve_fix"
}
Path("$DECISION_JSON").write_text(json.dumps(payload, indent=2) + "\n")
PY

echo
echo "Slack approval granted by $APPROVER."
echo "Card saved to:     $SLACK_JSON"
echo "Decision saved to: $DECISION_JSON"
echo

echo "Executing approved remediation through SafeOps policy/executor path..."
"$SCRIPT_DIR/approve_set_env_fix.sh" "$INCIDENT_ID" | tee "$OUT_DIR/latest_remediation_output.json"
echo "Saved remediation output to: $OUT_DIR/latest_remediation_output.json"
