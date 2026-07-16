# Milestone 5: Smart Remediation for Missing REDIS_URL

Milestone 4 proved that SafeOps can perform a real Kubernetes rollback, but the demo also showed an important product lesson: a simple rollback may not always restore service if rollout history is polluted or if the previous revision is also broken.

Milestone 5 adds a more precise remediation path for the known demo incident:

```text
CrashLoopBackOff + missing REDIS_URL
→ recommend set_env_deployment
→ require human approval
→ backend policy validates namespace, service, env name, and env value
→ executor applies the known-good REDIS_URL
→ verifier checks rollout status, pod readiness, and deployment env
→ audit + memory record the outcome
```

## Allowed Smart Fix

Only this scoped remediation is allowed by default:

```bash
kubectl -n demo set env deployment/checkout-api REDIS_URL=redis://redis.demo.svc.cluster.local:6379
```

The executor blocks arbitrary commands, arbitrary namespaces, arbitrary deployments, and arbitrary environment variables.

## Demo Flow

Start executor in Kubernetes mode and backend in separate terminals:

```bash
./scripts/run_executor_kubernetes.sh
./scripts/run_backend.sh
```

Reset to healthy state:

```bash
kubectl apply -f demo/k8s/checkout-api-working.yaml
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
```

Break the deployment:

```bash
kubectl apply -f demo/k8s/checkout-api-broken.yaml
kubectl -n demo get pods -w
```

Run collector:

```bash
./scripts/run_collector_once.sh
```

Approve smart remediation using the new incident ID:

```bash
./scripts/approve_set_env_fix.sh inc_checkout-api_xxxxx
```

Verify Kubernetes recovered:

```bash
kubectl -n demo get pods
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
```

Verify SafeOps audit and memory:

```bash
curl -s http://localhost:8000/audit-log/verify | python3 -m json.tool
curl -s http://localhost:8000/memory | python3 -m json.tool
```

## Why this matters

This is closer to a real AI DevOps Engineer because SafeOps is no longer only saying “roll back.” It is using evidence to identify the exact missing configuration and then applying a narrowly scoped, approved fix.
