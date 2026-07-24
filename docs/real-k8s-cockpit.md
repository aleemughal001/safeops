# SafeOps Real Kubernetes Cockpit

Milestone 22 connects the real Kubernetes detector and grouped evidence pack to an engineer-ready HTML cockpit.

## Why this milestone matters

Milestone 20 added real Kubernetes detection. Milestone 21 grouped raw Kubernetes symptoms into root incidents. Milestone 22 makes that evidence visible in a clean cockpit that can be shown to engineers.

The cockpit is generated from:

```text
/tmp/safeops-demo/real-k8s-incidents.json
```

and rendered to:

```text
/tmp/safeops-demo/real-k8s-cockpit.html
```

## What the cockpit shows

- scan status and namespace scope
- root incident count
- raw Kubernetes findings grouped
- severity and category distribution
- root-cause hypothesis
- recommended safe action
- approval boundary
- grouped reasons
- affected resources
- safe action options
- evidence chain
- high-signal Kubernetes events
- verification plan
- prevention ideas
- raw findings table for auditability

## Safety boundary

The cockpit is read-only. It displays evidence and safe action options, but it does not execute remediation actions.

Execution must remain behind:

- policy checks
- allowlisted actions
- human approval
- scoped executor permissions
- verification gates
- audit logging

## Demo commands

Healthy namespace:

```bash
./scripts/demo_real_k8s_cockpit.sh demo
./scripts/demo_open_real_k8s_cockpit.sh
```

Bad image test:

```bash
CONTAINER=$(kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl -n demo set image deployment/checkout-api $CONTAINER=safeops/checkout-api-demo:bad-tag-does-not-exist
kubectl -n demo rollout status deployment/checkout-api --timeout=30s || true

./scripts/demo_real_k8s_cockpit.sh demo
./scripts/demo_open_real_k8s_cockpit.sh
```

Restore:

```bash
CONTAINER=$(kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl -n demo set image deployment/checkout-api $CONTAINER=safeops/checkout-api-demo:0.1.0
kubectl -n demo rollout status deployment/checkout-api --timeout=90s || true
./scripts/demo_real_k8s_cockpit.sh demo
```

## Product direction

This is the bridge from terminal-only evidence to product experience:

```text
real Kubernetes cluster -> detector -> grouped evidence JSON -> engineer cockpit -> future approval/remediation flow
```
