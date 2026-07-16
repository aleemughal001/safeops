#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${SAFEOPS_DEMO_NAMESPACE:-demo}"
cd "$ROOT_DIR"

echo "== Kubernetes status =="
kubectl -n "$NAMESPACE" get pods
kubectl -n "$NAMESPACE" rollout status deployment/checkout-api --timeout=120s

echo
echo "== checkout-api env =="
kubectl -n "$NAMESPACE" get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'

echo
echo "== SafeOps audit verification =="
if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
  curl -s http://localhost:8000/audit-log/verify | python3 -m json.tool
else
  echo "Backend is not running; skipping audit API verification."
fi
