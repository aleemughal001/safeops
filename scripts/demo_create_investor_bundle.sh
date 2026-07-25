#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-demo}"
APPROVER="${2:-aleemughal001}"
DEPLOYMENT="${SAFEOPS_DEMO_DEPLOYMENT:-checkout-api}"
GOOD_IMAGE="${SAFEOPS_GOOD_IMAGE:-safeops/checkout-api-demo:0.1.0}"
BAD_IMAGE="${SAFEOPS_BAD_IMAGE:-safeops/checkout-api-demo:bad-tag-does-not-exist}"
ARTIFACTS_DIR="${SAFEOPS_ARTIFACTS_DIR:-/tmp/safeops-${NAMESPACE}}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
mkdir -p "$ARTIFACTS_DIR"

echo ""
echo "================================================================"
echo "SafeOps investor evidence bundle demo starting"
echo "================================================================"
echo "Namespace: $NAMESPACE"
echo "Deployment: $DEPLOYMENT"
echo "Approver: $APPROVER"
echo "Artifacts directory: $ARTIFACTS_DIR"

CONTAINER="$(kubectl -n "$NAMESPACE" get deployment "$DEPLOYMENT" -o jsonpath='{.spec.template.spec.containers[0].name}')"
echo "Container: $CONTAINER"

echo ""
echo "================================================================"
echo "1/6 Reset demo workload to known-good image"
echo "================================================================"
kubectl -n "$NAMESPACE" set image "deployment/${DEPLOYMENT}" "${CONTAINER}=${GOOD_IMAGE}" >/dev/null
kubectl -n "$NAMESPACE" rollout status "deployment/${DEPLOYMENT}" --timeout=90s
kubectl -n "$NAMESPACE" get pods

echo ""
echo "================================================================"
echo "2/6 Inject real bad-image rollout failure"
echo "================================================================"
kubectl -n "$NAMESPACE" set image "deployment/${DEPLOYMENT}" "${CONTAINER}=${BAD_IMAGE}"
kubectl -n "$NAMESPACE" rollout status "deployment/${DEPLOYMENT}" --timeout=30s || true
kubectl -n "$NAMESPACE" get pods

echo ""
echo "================================================================"
echo "3/6 Run approved SafeOps remediation flow"
echo "================================================================"
./scripts/demo_execute_approved_real_fix.sh "$NAMESPACE" approve "$APPROVER"

echo ""
echo "================================================================"
echo "4/6 Generate and verify tamper-evident audit trail"
echo "================================================================"
./scripts/demo_real_audit_trail.sh "$NAMESPACE"
./scripts/demo_real_audit_trail.sh "$NAMESPACE" verify

echo ""
echo "================================================================"
echo "5/6 Capture final cluster state"
echo "================================================================"
{
  echo "SafeOps final Kubernetes cluster state"
  echo "Generated at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Namespace: $NAMESPACE"
  echo "Deployment: $DEPLOYMENT"
  echo ""
  echo "rollout status:"
  kubectl -n "$NAMESPACE" rollout status "deployment/${DEPLOYMENT}" --timeout=90s
  echo ""
  echo "pods:"
  kubectl -n "$NAMESPACE" get pods -o wide
  echo ""
  echo "deployment image:"
  kubectl -n "$NAMESPACE" get deployment "$DEPLOYMENT" -o jsonpath='{.spec.template.spec.containers[0].image}'
  echo ""
} | tee "$ARTIFACTS_DIR/final-cluster-state.txt"

echo ""
echo "================================================================"
echo "6/6 Package investor/customer evidence bundle"
echo "================================================================"
python3 ./scripts/safeops_investor_bundle.py "$NAMESPACE" "$APPROVER" --deployment "$DEPLOYMENT" --artifacts-dir "$ARTIFACTS_DIR" --output-root "$ARTIFACTS_DIR"

echo ""
echo "SafeOps investor evidence bundle demo complete."
echo "Find the newest bundle:"
echo "  ls -td ${ARTIFACTS_DIR}/safeops-investor-demo-bundle-* | head -1"
