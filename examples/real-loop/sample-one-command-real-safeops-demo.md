# Sample One-Command Real SafeOps Demo Output

Example command:

```bash
./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
```

Expected high-level result:

```text
SafeOps approved Kubernetes executor complete.
Plans seen: 1
Execution records generated: 1
Executed actions: 1
Verified healthy: 1
Blocked actions: 0
- SUCCEEDED demo/checkout-api action=rollback-deployment verification=verified_healthy

SafeOps tamper-evident audit trail generated.
Events chained: 5
Verification valid: True

SafeOps audit trail verification complete.
Verification valid: True
Events checked: 5

SafeOps Real Loop Executive Summary
-----------------------------------
Namespace: demo
Deployment: checkout-api
Approver: aleemughal001
Final cluster state: healthy
Open root incidents after recovery: 0
Executed allowlisted actions: 1
Verified healthy actions: 1
Blocked actions: 0
Audit events chained: 5
Audit verification valid: True
Result: PASSED
```
