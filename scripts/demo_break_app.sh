#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${SAFEOPS_DEMO_NAMESPACE:-demo}"
cd "$ROOT_DIR"

echo "Applying broken checkout-api manifest..."
kubectl apply -f demo/k8s/checkout-api-broken.yaml

echo "Waiting for checkout-api to show failure symptoms..."
for i in $(seq 1 90); do
  status=$(kubectl -n "$NAMESPACE" get pods -l app=checkout-api --no-headers 2>/dev/null || true)
  echo "$status" | grep -E 'CrashLoopBackOff|Error|RunContainerError|ImagePullBackOff' >/dev/null 2>&1 && break
  sleep 1
done

echo
kubectl -n "$NAMESPACE" get pods

echo
if kubectl -n "$NAMESPACE" rollout status deployment/checkout-api --timeout=5s; then
  echo "Warning: rollout still reports healthy; collector may not see an incident yet."
else
  echo "Broken rollout confirmed."
fi
