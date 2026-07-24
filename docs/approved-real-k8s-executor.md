# SafeOps Approved Real Kubernetes Executor

Milestone 25 connects the real remediation approval decision to a restricted Kubernetes executor.

## Purpose

This milestone turns the SafeOps real-world flow into an approval-gated remediation loop:

```text
real Kubernetes incident
→ grouped evidence pack
→ remediation plan
→ approval request
→ approval decision
→ policy check
→ allowlisted execution
→ rollout verification
→ execution record
```

## Safety boundary

The executor is intentionally narrow.

It does **not** run arbitrary shell commands.
It accepts only typed actions from the remediation plan.
For this milestone, the only supported write action is:

```text
kubernetes_rollout_undo
```

The executor also validates:

- approval decision is `approve`
- namespace is allowlisted
- namespace and deployment names match safe Kubernetes name patterns
- action type is allowlisted
- target deployment exists before execution

By default, only the `demo` namespace is allowed. This can be changed with:

```bash
SAFEOPS_ALLOWED_NAMESPACES=demo,staging ./scripts/demo_execute_approved_real_fix.sh demo approve aleemughal001
```

## Generated artifacts

```text
/tmp/safeops-demo/real-k8s-execution-record.json
/tmp/safeops-demo/real-k8s-execution-record.md
```

The execution record includes:

- source plan
- approval decision
- approver
- policy decision
- command executed
- precheck result
- execution result
- verification result
- safety notes

## Demo

Create a bad image incident first:

```bash
CONTAINER=$(kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].name}')
kubectl -n demo set image deployment/checkout-api $CONTAINER=safeops/checkout-api-demo:bad-tag-does-not-exist
kubectl -n demo rollout status deployment/checkout-api --timeout=30s || true
```

Then run the approved executor flow:

```bash
./scripts/demo_execute_approved_real_fix.sh demo approve aleemughal001
```

Expected result:

```text
Executed actions: 1
Verified healthy: 1
SUCCEEDED demo/checkout-api action=rollback-deployment verification=verified_healthy
```

## Rejection test

```bash
./scripts/demo_execute_approved_real_fix.sh demo reject aleemughal001
```

Expected: no execution, because the decision was rejected.

## Why this matters

SafeOps now proves the real safety workflow:

```text
AI does not blindly act.
A human approves.
Policy checks the action.
Executor runs only an allowlisted Kubernetes operation.
Verification proves recovery.
Audit record captures every step.
```
