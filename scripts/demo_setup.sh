#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${SAFEOPS_KIND_CLUSTER:-safeops-demo}"
NAMESPACE="${SAFEOPS_DEMO_NAMESPACE:-demo}"
IMAGE="${SAFEOPS_DEMO_IMAGE:-safeops/checkout-api-demo:0.1.0}"

echo "== SafeOps demo setup =="
cd "$ROOT_DIR"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd docker
require_cmd kubectl
require_cmd kind
require_cmd python3
require_cmd curl

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running or current user cannot access Docker." >&2
  exit 1
fi

if ! kind get clusters | grep -qx "$CLUSTER_NAME"; then
  echo "Creating kind cluster: $CLUSTER_NAME"
  kind create cluster --name "$CLUSTER_NAME"
else
  echo "kind cluster already exists: $CLUSTER_NAME"
fi

kubectl config use-context "kind-$CLUSTER_NAME" >/dev/null

echo "Building demo image: $IMAGE"
docker build -t "$IMAGE" demo/sample-app

echo "Loading image into kind cluster: $CLUSTER_NAME"
kind load docker-image "$IMAGE" --name "$CLUSTER_NAME"

echo "Applying known-good Kubernetes manifest..."
kubectl apply -f demo/k8s/namespace.yaml
kubectl apply -f demo/k8s/checkout-api-working.yaml
kubectl -n "$NAMESPACE" rollout status deployment/checkout-api --timeout=120s

echo
kubectl -n "$NAMESPACE" get pods

echo
./scripts/demo_status.sh || true

echo
printf 'Demo setup complete.\n'
