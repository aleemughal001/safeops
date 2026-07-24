# Real Kubernetes Remediation Plan Generator

Milestone 23 adds an approval-ready remediation planning layer on top of the real Kubernetes evidence pack.

It does not execute fixes. It reads `/tmp/safeops-demo/real-k8s-incidents.json` and produces:

- `/tmp/safeops-demo/real-k8s-remediation-plan.json`
- `/tmp/safeops-demo/real-k8s-remediation-plan.md`

## Why this matters

Milestones 20-22 proved that SafeOps can scan a real Kubernetes cluster, detect active incidents, group related symptoms into a root incident, and show the result in an engineer-facing cockpit.

Milestone 23 turns that grouped diagnosis into an approval-ready plan:

- incident category
- target namespace and workload
- blast radius
- recommended strategy
- safe action options
- command previews
- approval requirement
- policy requirement
- verification plan
- prevention plan
- safety notes

## Safety boundary

The plan generator is read-only. It never executes remediation commands. Production-changing actions remain gated by:

1. policy validation
2. human approval
3. typed allowlisted executor actions
4. post-action verification
5. audit logging

The detector/planner must not run arbitrary AI-generated shell commands.

## Example workflow

Healthy namespace:

```bash
./scripts/demo_generate_real_remediation_plan.sh demo
```

Expected: zero active root incidents and zero remediation plans.

Bad image incident:

```bash
CONTAINER=$(kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl -n demo set image deployment/checkout-api $CONTAINER=safeops/checkout-api-demo:bad-tag-does-not-exist
kubectl -n demo rollout status deployment/checkout-api --timeout=30s || true
./scripts/demo_generate_real_remediation_plan.sh demo
```

Expected: one approval-ready plan for an image pull failure.

Restore healthy:

```bash
CONTAINER=$(kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl -n demo set image deployment/checkout-api $CONTAINER=safeops/checkout-api-demo:0.1.0
kubectl -n demo rollout status deployment/checkout-api --timeout=90s || true
./scripts/demo_generate_real_remediation_plan.sh demo
```

## Current limitation

The plan generator creates structured plans and command previews, but it does not yet connect the plan to the approval system or Kubernetes executor. That should be a later milestone.
