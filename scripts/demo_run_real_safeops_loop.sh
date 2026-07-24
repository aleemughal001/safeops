#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-demo}"
APPROVER="${2:-${USER:-safeops-demo-user}}"
DEPLOYMENT="${SAFEOPS_DEMO_DEPLOYMENT:-checkout-api}"
GOOD_IMAGE="${SAFEOPS_DEMO_GOOD_IMAGE:-safeops/checkout-api-demo:0.1.0}"
BAD_IMAGE="${SAFEOPS_DEMO_BAD_IMAGE:-safeops/checkout-api-demo:bad-tag-does-not-exist}"
OUT_DIR="${SAFEOPS_DEMO_OUT_DIR:-/tmp/safeops-demo}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing required file: $path" >&2
    echo "Run the previous SafeOps milestones first, then retry." >&2
    exit 1
  fi
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

print_step() {
  echo
  echo "================================================================"
  echo "$1"
  echo "================================================================"
}

require_cmd kubectl
require_cmd python3
require_file "$SCRIPT_DIR/demo_execute_approved_real_fix.sh"
require_file "$SCRIPT_DIR/demo_real_audit_trail.sh"
require_file "$SCRIPT_DIR/demo_real_approval_gate.sh"
require_file "$SCRIPT_DIR/demo_real_safeops_summary.py"

mkdir -p "$OUT_DIR"

print_step "SafeOps one-command real loop starting"
echo "Namespace: $NAMESPACE"
echo "Deployment: $DEPLOYMENT"
echo "Approver: $APPROVER"
echo "Good image: $GOOD_IMAGE"
echo "Injected bad image: $BAD_IMAGE"
echo "Artifacts directory: $OUT_DIR"

if ! kubectl -n "$NAMESPACE" get deployment "$DEPLOYMENT" >/dev/null 2>&1; then
  echo "Deployment $NAMESPACE/$DEPLOYMENT not found." >&2
  echo "Start the demo app first, for example:" >&2
  echo "  kubectl apply -f demo/k8s/namespace.yaml" >&2
  echo "  kubectl apply -f demo/k8s/checkout-api-working.yaml" >&2
  exit 1
fi

CONTAINER="$(kubectl -n "$NAMESPACE" get deployment "$DEPLOYMENT" -o jsonpath='{.spec.template.spec.containers[0].name}')"
if [[ -z "$CONTAINER" ]]; then
  echo "Could not resolve container name for deployment $NAMESPACE/$DEPLOYMENT" >&2
  exit 1
fi

echo "Container: $CONTAINER"

print_step "1/7 Reset demo workload to a known-good state"
kubectl -n "$NAMESPACE" set image "deployment/$DEPLOYMENT" "$CONTAINER=$GOOD_IMAGE"
kubectl -n "$NAMESPACE" rollout status "deployment/$DEPLOYMENT" --timeout=90s || true
kubectl -n "$NAMESPACE" get pods

print_step "2/7 Inject real Kubernetes bad-image rollout failure"
kubectl -n "$NAMESPACE" set image "deployment/$DEPLOYMENT" "$CONTAINER=$BAD_IMAGE"
kubectl -n "$NAMESPACE" rollout status "deployment/$DEPLOYMENT" --timeout=30s || true
kubectl -n "$NAMESPACE" get pods

print_step "3/7 Detect, plan, approve, execute, and verify safe remediation"
"$SCRIPT_DIR/demo_execute_approved_real_fix.sh" "$NAMESPACE" approve "$APPROVER"

print_step "4/7 Generate tamper-evident audit trail"
"$SCRIPT_DIR/demo_real_audit_trail.sh" "$NAMESPACE"

print_step "5/7 Verify tamper-evident audit trail"
"$SCRIPT_DIR/demo_real_audit_trail.sh" "$NAMESPACE" verify

print_step "6/7 Final healthy-state scan"
"$SCRIPT_DIR/demo_real_approval_gate.sh" "$NAMESPACE"

print_step "7/7 Executive demo summary"
python3 "$SCRIPT_DIR/demo_real_safeops_summary.py" \
  --namespace "$NAMESPACE" \
  --approver "$APPROVER" \
  --deployment "$DEPLOYMENT" \
  --out-dir "$OUT_DIR"

echo
echo "SafeOps one-command real loop complete."
echo "Open the audit trail:"
echo "  less $OUT_DIR/real-k8s-audit-trail.md"
echo "Open the execution record:"
echo "  less $OUT_DIR/real-k8s-execution-record.md"
