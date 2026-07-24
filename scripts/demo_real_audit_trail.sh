#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-demo}"
MODE="${2:-generate}"
OUT_DIR="/tmp/safeops-${NAMESPACE}"

INCIDENT_JSON="$OUT_DIR/real-k8s-incidents.json"
PLAN_JSON="$OUT_DIR/real-k8s-remediation-plan.json"
APPROVAL_REQUEST_JSON="$OUT_DIR/real-k8s-approval-request.json"
APPROVAL_DECISION_JSON="$OUT_DIR/real-k8s-approval-decision.json"
EXECUTION_JSON="$OUT_DIR/real-k8s-execution-record.json"
AUDIT_JSON="$OUT_DIR/real-k8s-audit-trail.json"
AUDIT_MD="$OUT_DIR/real-k8s-audit-trail.md"
TAMPERED_AUDIT_JSON="$OUT_DIR/real-k8s-audit-trail-tampered.json"

if [[ "$MODE" == "generate" ]]; then
  python3 scripts/safeops_real_audit_trail.py generate \
    --namespace "$NAMESPACE" \
    --incident-json "$INCIDENT_JSON" \
    --plan-json "$PLAN_JSON" \
    --approval-request-json "$APPROVAL_REQUEST_JSON" \
    --approval-decision-json "$APPROVAL_DECISION_JSON" \
    --execution-json "$EXECUTION_JSON" \
    --audit-json "$AUDIT_JSON" \
    --audit-md "$AUDIT_MD"
elif [[ "$MODE" == "verify" ]]; then
  python3 scripts/safeops_real_audit_trail.py verify \
    --audit-json "$AUDIT_JSON" \
    --audit-md "$AUDIT_MD"
elif [[ "$MODE" == "tamper-test" ]]; then
  python3 scripts/safeops_real_audit_trail.py tamper-test \
    --audit-json "$AUDIT_JSON" \
    --tampered-audit-json "$TAMPERED_AUDIT_JSON"
else
  echo "Usage: $0 [namespace] [generate|verify|tamper-test]" >&2
  exit 2
fi

echo
echo "SafeOps real audit trail ready."
echo "Namespace scanned: $NAMESPACE"
echo "Mode: $MODE"
echo "Audit JSON: $AUDIT_JSON"
echo "Audit Markdown: $AUDIT_MD"
echo
echo "Open/read the audit trail:"
echo "  less $AUDIT_MD"
