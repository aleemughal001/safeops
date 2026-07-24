#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="${1:-demo}"
MODE="${2:-request}"
APPROVER="${3:-local-demo-user}"
OUT_DIR="/tmp/safeops-demo"
PLAN_JSON="$OUT_DIR/real-k8s-remediation-plan.json"
REQUEST_JSON="$OUT_DIR/real-k8s-approval-request.json"
REQUEST_MD="$OUT_DIR/real-k8s-approval-request.md"
DECISION_JSON="$OUT_DIR/real-k8s-approval-decision.json"
DECISION_MD="$OUT_DIR/real-k8s-approval-decision.md"

mkdir -p "$OUT_DIR"

"$SCRIPT_DIR/demo_generate_real_remediation_plan.sh" "$NAMESPACE"

if [[ "$MODE" == "approve" || "$MODE" == "reject" ]]; then
  python3 "$SCRIPT_DIR/safeops_real_approval_gate.py" \
    --input "$PLAN_JSON" \
    --json-out "$REQUEST_JSON" \
    --md-out "$REQUEST_MD" \
    --decision "$MODE" \
    --approver "$APPROVER" \
    --reason "SafeOps local demo ${MODE} decision." \
    --decision-json-out "$DECISION_JSON" \
    --decision-md-out "$DECISION_MD"
else
  python3 "$SCRIPT_DIR/safeops_real_approval_gate.py" \
    --input "$PLAN_JSON" \
    --json-out "$REQUEST_JSON" \
    --md-out "$REQUEST_MD" \
    --decision-json-out "$DECISION_JSON" \
    --decision-md-out "$DECISION_MD"
fi

cat <<EOF

SafeOps real approval gate ready.
Namespace scanned: $NAMESPACE
Mode: $MODE
Plan JSON: $PLAN_JSON
Approval request JSON: $REQUEST_JSON
Approval request Markdown: $REQUEST_MD
Decision JSON: $DECISION_JSON
Decision Markdown: $DECISION_MD

Open/read the approval request:
  less $REQUEST_MD

Open/read the decision record if mode was approve/reject:
  less $DECISION_MD
EOF
