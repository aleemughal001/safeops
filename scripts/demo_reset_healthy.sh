#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Resetting checkout-api to known-good manifest..."
kubectl apply -f demo/k8s/checkout-api-working.yaml
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
kubectl -n demo get pods

echo "checkout-api environment:"
kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
