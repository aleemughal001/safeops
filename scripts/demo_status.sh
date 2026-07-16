#!/usr/bin/env bash
set -euo pipefail

echo "== SafeOps service health =="
echo "Executor:"
curl -sS http://localhost:8010/health || true
echo

echo "Backend:"
curl -sS http://localhost:8000/health || true
echo

echo "== Kubernetes demo status =="
kubectl -n demo get pods || true
kubectl -n demo rollout status deployment/checkout-api --timeout=10s || true

echo

echo "== checkout-api env =="
kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}' || true
