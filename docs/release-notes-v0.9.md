# SafeOps v0.9 — Human Approval Demo Release Notes

SafeOps v0.9 demonstrates a complete trust-first AI-assisted Kubernetes incident workflow.

## What this release proves

- SafeOps can detect a real Kubernetes rollout failure.
- SafeOps can collect evidence from pods, logs, events, and deployment configuration.
- SafeOps can explain the likely root cause in plain English.
- SafeOps can recommend a low-risk remediation with blast-radius information.
- SafeOps requires human approval before execution.
- SafeOps checks policy allowlists before running a fix.
- SafeOps executes a real Kubernetes remediation through the executor.
- SafeOps verifies recovery after execution.
- SafeOps records approval, policy, execution, verification, and memory in a tamper-evident audit log.
- SafeOps prints a clean CLI incident report suitable for demos.

## Demo scenario

The demo intentionally breaks the `checkout-api` Kubernetes deployment by removing `REDIS_URL`.
The app enters an unhealthy rollout / CrashLoopBackOff-like state.
SafeOps detects the missing environment variable, recommends restoring it, asks for human approval, applies the fix, verifies recovery, and prints a final report.

## Main command

```bash
./scripts/demo_run_full.sh
```

When prompted, type:

```text
yes
```

## Expected outcome

The final report should show:

```text
Policy allowed:     PASS
Status:             executed
Mode:               kubernetes
Overall:            healthy
Audit valid:        PASS
```

## Current limitations

This is a local demo, not a production SaaS system yet. It does not yet include production authentication, enterprise RBAC, multi-tenant isolation, persistent database storage, Slack approval buttons, signed audit export, or a dashboard UI.
