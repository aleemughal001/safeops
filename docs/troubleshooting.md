# SafeOps Troubleshooting

## Backend connection refused

Symptom:

```text
Failed to connect to localhost port 8000
```

Fix:

```bash
cd ~/safeops-starter/safeops-starter
./scripts/run_backend.sh
```

Keep the terminal open.

## Executor connection refused

Symptom:

```text
Failed to connect to localhost port 8010
```

Fix:

```bash
cd ~/safeops-starter/safeops-starter
./scripts/run_executor_kubernetes.sh
```

Keep the terminal open.

## Approval says incident has not been analyzed

Cause:

You used a placeholder incident ID or restarted the backend after the incident was created.

Fix:

```bash
./scripts/run_collector_once.sh
```

Copy the new `incident_id`, then approve again.

## Rollout exceeded progress deadline

This is expected after applying the broken manifest.

It means Kubernetes is stuck because the new pod is unhealthy.

SafeOps should detect this and recommend remediation.

## Rollback command succeeds but verification is unhealthy

This can happen if Kubernetes rollout history points to another broken revision.

This is why smart remediation is stronger than simple rollback.

Use the smart fix:

```bash
./scripts/approve_set_env_fix.sh <INCIDENT_ID>
```

## Reset app to healthy state

```bash
kubectl apply -f demo/k8s/checkout-api-working.yaml
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
kubectl -n demo get pods
```

## Check REDIS_URL

```bash
kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
```

Expected:

```text
REDIS_URL=redis://redis.demo.svc.cluster.local:6379
```

## Check no secret files before GitHub

```bash
find . -maxdepth 4 \( -name "*.pem" -o -name "*credentials*.csv" -o -name "rootkey.csv" -o -name "*.key" -o -name "*.zip" \) -print
```

Expected: no output.
