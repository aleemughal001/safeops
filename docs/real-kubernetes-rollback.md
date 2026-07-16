# SafeOps Real Kubernetes Rollback Demo

This patch enables a narrowly scoped real Kubernetes rollback path for the local demo.

## Safety constraints

The executor still blocks arbitrary operations. Real Kubernetes actions are restricted by executor-side allowlists:

- `SAFEOPS_ALLOWED_K8S_NAMESPACES`, default: `demo`
- `SAFEOPS_ALLOWED_K8S_SERVICES`, default: `checkout-api`

The backend policy still performs its own allowlist check before the executor is called. The executor performs the same kind of scope check again as defense in depth.

## Supported real action

For the local demo, the executor supports:

```bash
kubectl -n demo rollout undo deployment/checkout-api
```

It does not allow arbitrary shell commands. The command is executed as a fixed argument list with `shell=False`.

## Demo flow

1. Run executor in Kubernetes mode:

```bash
./scripts/run_executor_kubernetes.sh
```

2. Run backend:

```bash
./scripts/run_backend.sh
```

3. Make sure the demo app is broken:

```bash
kubectl apply -f demo/k8s/checkout-api-broken.yaml
kubectl -n demo get pods
```

4. Run collector:

```bash
./scripts/run_collector_once.sh
```

5. Copy the returned `incident_id`.

6. Approve real rollback:

```bash
./scripts/approve_real_rollback.sh <incident_id>
```

7. Confirm Kubernetes recovered:

```bash
kubectl -n demo get pods
kubectl -n demo rollout status deployment/checkout-api
curl -s http://localhost:8000/audit-log/verify | python3 -m json.tool
curl -s http://localhost:8000/memory | python3 -m json.tool
```
