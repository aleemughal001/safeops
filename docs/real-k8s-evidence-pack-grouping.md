# SafeOps Real Kubernetes Evidence Pack and Incident Grouping

Milestone 21 improves the real Kubernetes detector so it behaves more like an engineer-facing incident system instead of a noisy alert list.

## Why this milestone matters

A single Kubernetes root problem often creates many symptoms.

Example: a bad image tag can create:

- `DeploymentUnavailable`
- `ErrImagePull`
- `Pending`
- rollout timeout

A raw detector may list these as separate incidents. Engineers usually want one clean root incident with the raw symptoms preserved as evidence.

## New behavior

The detector now writes a v2 report schema:

```text
safeops.real_k8s_incident_report.v2
```

The output contains two layers:

1. `root_incidents` — grouped engineer-facing incidents.
2. `raw_findings` — underlying Kubernetes symptoms preserved for audit/debugging.

## Example grouping

Instead of showing three separate findings:

```text
DeploymentUnavailable
ErrImagePull
Pending
```

SafeOps now groups them as:

```text
Root incident: Image pull failure / bad image or registry access
Primary category: image_or_registry
Affected workload: demo/checkout-api
Raw findings grouped: 3
```

The evidence pack includes:

- affected workload
- grouped symptoms
- Kubernetes resource details
- deployment availability status
- pod phase and Ready condition
- container name and image summary
- high-signal Kubernetes events
- sanitized logs tail when available
- safe action options
- verification plan
- prevention ideas

## Safety model

This detector is still read-only.

It does not execute remediation. It only prepares evidence and safe action options. Any future execution must still go through:

1. policy validation
2. human approval
3. scoped executor
4. verification
5. audit log

## Test flow

Healthy namespace:

```bash
./scripts/demo_detect_real_k8s_incidents.sh demo
```

Expected:

```text
Root incidents detected: 0
Raw findings grouped: 0
```

Create a real image pull failure:

```bash
CONTAINER=$(kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl -n demo set image deployment/checkout-api $CONTAINER=safeops/checkout-api-demo:bad-tag-does-not-exist
kubectl -n demo rollout status deployment/checkout-api --timeout=30s || true
./scripts/demo_detect_real_k8s_incidents.sh demo
```

Expected:

```text
Root incidents detected: 1
Raw findings grouped: 2 or more
Top root incidents:
- MEDIUM demo/checkout-api title=Image pull failure / bad image or registry access category=image_or_registry
```

Restore healthy:

```bash
CONTAINER=$(kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl -n demo set image deployment/checkout-api $CONTAINER=safeops/checkout-api-demo:0.1.0
kubectl -n demo rollout status deployment/checkout-api --timeout=90s || true
./scripts/demo_detect_real_k8s_incidents.sh demo
```

Expected:

```text
Root incidents detected: 0
Raw findings grouped: 0
```

## Product direction

This milestone is important for the engineer-ready prototype because real clusters are noisy. SafeOps must reduce noise without hiding evidence.

The correct product behavior is:

```text
many Kubernetes symptoms -> one root incident -> evidence pack -> safe action options -> approval -> execution later -> verification -> audit
```
