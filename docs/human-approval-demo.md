# Human Approval Demo

Milestone 9 adds a visible human approval gate to the SafeOps demo.

SafeOps should not silently remediate production systems. The demo now makes the trust boundary explicit:

1. SafeOps detects the Kubernetes incident.
2. SafeOps explains the likely root cause.
3. SafeOps recommends a constrained remediation.
4. A human approves or denies the action.
5. Policy validates the approved request.
6. The executor performs the allowlisted action.
7. SafeOps verifies recovery.
8. The audit log records the approval, policy decision, execution, verification, and memory event.

## Run the interactive demo

```bash
./scripts/demo_run_full.sh
```

When prompted, type:

```text
yes
```

SafeOps will then execute the approved remediation.

## Run the demo non-interactively

For recordings, CI experiments, or scripted demos, you can bypass the prompt with:

```bash
SAFEOPS_AUTO_APPROVE=true ./scripts/demo_run_full.sh
```

This still uses the same approval path, but the script supplies the approval automatically.

## Approval prompt example

```text
SafeOps Human Approval Gate
===========================
Incident ID:        inc_checkout-api_...
Service:            checkout-api
Namespace:          demo
Detected problem:   checkout-api rollout is unhealthy / CrashLoopBackOff symptoms
Likely root cause:  REDIS_URL is missing or misconfigured
Confidence:         89%

Recommended remediation
-----------------------
Action:             set_env_deployment
Change:             Restore REDIS_URL on deployment/checkout-api
Risk level:         low
Blast radius:       checkout-api in namespace demo only

Approve this remediation? Type 'yes' to continue:
```

## Why this matters

The approval gate demonstrates SafeOps' core safety model:

- AI can recommend a fix.
- Humans remain in control.
- Policy restricts what can be executed.
- The executor only performs allowlisted actions.
- Verification proves whether the system recovered.
- Audit records the full decision trail.
