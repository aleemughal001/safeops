# Action Allowlist

SafeOps must never execute arbitrary infrastructure actions. Every action must be explicitly allowlisted and checked by backend policy before execution.

Policy file:

```text
examples/policies/safe-actions.yaml
```

Currently allowed:

- `set_env_deployment`
- `rollout_undo_deployment`
- `rollout_restart_deployment`
- `rerun_pipeline`
- `create_issue`

Currently blocked:

- `delete_namespace`
- `delete_secret`
- `edit_secret`
- `run_arbitrary_command`
- `modify_iam_policy`

## Runtime Enforcement

The allowlist is enforced in code by:

```text
backend/app/policy.py
```

The executor also performs a local safety check before execution.

## Milestone 5 Smart Remediation Guardrail

`set_env_deployment` is intentionally narrow in the local demo. By default, it only allows:

```text
namespace: demo
service/deployment: checkout-api
env_name: REDIS_URL
env_value: redis://redis.demo.svc.cluster.local:6379
```

This prevents arbitrary environment edits and keeps the prototype safe.

## Rule

Documentation is not security. The allowlist must be enforced at runtime before any action reaches the executor.
