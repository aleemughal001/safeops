#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="/tmp/safeops-demo"

NAMESPACE="${1:-demo}"
DECISION="${2:-approve}"
APPROVER="${3:-aleemughal001}"

PLAN_JSON="$OUT_DIR/real-k8s-remediation-plan.json"
DECISION_JSON="$OUT_DIR/real-k8s-approval-decision.json"
EXEC_JSON="$OUT_DIR/real-k8s-execution-record.json"
EXEC_MD="$OUT_DIR/real-k8s-execution-record.md"

cd "$ROOT_DIR"

# Generate fresh evidence, remediation plan, approval request, and approval/rejection decision.
"$SCRIPT_DIR/demo_real_approval_gate.sh" "$NAMESPACE" "$DECISION" "$APPROVER"

# Execute only if the decision is approve and policy allows the typed action.
python3 "$SCRIPT_DIR/safeops_approved_k8s_executor.py" \
  --plan "$PLAN_JSON" \
  --decision "$DECISION_JSON" \
  --json-out "$EXEC_JSON" \
  --md-out "$EXEC_MD"

echo
echo "SafeOps approved execution flow complete."
echo "Namespace scanned: $NAMESPACE"
echo "Decision: $DECISION"
echo "Approver: $APPROVER"
echo "Plan JSON: $PLAN_JSON"
echo "Decision JSON: $DECISION_JSON"
echo "Execution JSON: $EXEC_JSON"
echo "Execution Markdown: $EXEC_MD"
echo
echo "Open/read the execution record:"
echo "  less $EXEC_MD"
