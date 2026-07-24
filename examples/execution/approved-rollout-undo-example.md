# Example: Approved Rollout Undo Execution

This example shows the intended Milestone 25 behavior for an image pull failure.

```text
Incident: Image pull failure / bad image or registry access
Target: demo/checkout-api
Approval: approve by aleemughal001
Policy: allowed
Action: kubernetes_rollout_undo
Command: kubectl -n demo rollout undo deployment/checkout-api
Verification: kubectl -n demo rollout status deployment/checkout-api --timeout=90s
Result: verified_healthy
```

The executor does not accept arbitrary shell commands. It reconstructs the command from a typed action, namespace, and deployment name after policy validation.
