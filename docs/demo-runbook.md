# SafeOps Demo Runbook

This runbook shows how to run the local SafeOps demo from a clean working state.

## 1. Start SafeOps services

### Terminal 1: executor

```bash
cd ~/safeops-starter/safeops-starter
./scripts/run_executor_kubernetes.sh
```

### Terminal 2: backend

```bash
cd ~/safeops-starter/safeops-starter
./scripts/run_backend.sh
```

### Terminal 3: health check

```bash
curl -sS http://localhost:8010/health
curl -sS http://localhost:8000/health
```

Expected:

```text
executor status ok
backend status ok
executor mode kubernetes
allowed_env_names includes REDIS_URL
```

## 2. Confirm Kubernetes is healthy

```bash
kubectl -n demo get pods
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
```

Expected:

```text
checkout-api pod is 1/1 Running
deployment successfully rolled out
```

## 3. Break checkout-api

```bash
kubectl apply -f demo/k8s/checkout-api-broken.yaml
kubectl -n demo get pods -w
```

Wait for:

```text
CrashLoopBackOff
```

Then press `CTRL+C`.

## 4. Detect incident

```bash
./scripts/run_collector_once.sh
```

Copy the returned `incident_id`.

Expected root cause:

```text
The latest deployment likely removed or misconfigured REDIS_URL for checkout-api.
```

Expected recommended action:

```text
set_env_deployment
```

## 5. Approve smart fix

```bash
./scripts/approve_set_env_fix.sh <INCIDENT_ID>
```

Example:

```bash
./scripts/approve_set_env_fix.sh inc_checkout-api_1784229327
```

Expected execution:

```text
kubectl -n demo set env deployment/checkout-api REDIS_URL=redis://redis.demo.svc.cluster.local:6379
```

## 6. Verify Kubernetes recovery

```bash
kubectl -n demo get pods
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
```

Expected:

```text
pod is 1/1 Running
deployment successfully rolled out
REDIS_URL is present
```

## 7. Verify SafeOps audit and memory

```bash
curl -s http://localhost:8000/audit-log/verify | python3 -m json.tool
curl -s http://localhost:8000/memory | python3 -m json.tool
```

Expected audit:

```text
valid: true
issues: []
```

Expected memory:

```text
recommended_action: set_env_deployment
outcome: healthy
```

## 8. Reset demo manually if needed

```bash
kubectl apply -f demo/k8s/checkout-api-working.yaml
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
kubectl -n demo get pods
```
