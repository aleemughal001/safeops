# SafeOps 2-Minute Demo Script

## 0:00–0:20 — Problem

Modern DevOps teams get flooded with alerts. Existing monitoring tools can show that something is broken, but engineers still need to investigate logs, events, rollout state, recent changes, and safe recovery options.

SafeOps is an open-source safety layer for AI-assisted DevOps. It focuses on evidence, human approval, policy checks, safe remediation, verification, and auditability.

## 0:20–0:40 — Healthy baseline

Start from a healthy Kubernetes service called `checkout-api` running in the `demo` namespace.

Show:

```bash
kubectl -n demo get pods
kubectl -n demo rollout status deployment/checkout-api
```

Explain that `REDIS_URL` is required by the application.

## 0:40–1:00 — Break the app

Run the full demo:

```bash
./scripts/demo_run_full.sh
```

SafeOps applies a broken manifest that removes `REDIS_URL`. Kubernetes now shows an unhealthy rollout and failed pod behavior.

## 1:00–1:25 — SafeOps analysis

SafeOps collects real Kubernetes evidence: pod status, logs, events, and deployment configuration.

It identifies the likely root cause:

```text
The latest deployment likely removed or misconfigured REDIS_URL for checkout-api.
```

It recommends a scoped fix:

```text
Restore REDIS_URL on deployment/checkout-api
Blast radius: checkout-api in namespace demo only
Risk level: low
```

## 1:25–1:40 — Human approval

SafeOps stops before execution and asks:

```text
Approve this remediation? Type 'yes' to continue:
```

Type:

```text
yes
```

Explain: the AI does not directly change production. A human approves, then policy validates the action.

## 1:40–2:00 — Execution, verification, audit

SafeOps runs the approved Kubernetes command:

```bash
kubectl -n demo set env deployment/checkout-api REDIS_URL=redis://redis.demo.svc.cluster.local:6379
```

Then it verifies:

```text
rollout_status: passed
deployment_env: passed
pod_readiness: passed
Audit valid: PASS
```

Close with:

SafeOps is not trying to replace observability tools. It adds a trusted action layer on top: explain, approve, remediate safely, verify recovery, and audit every step.
