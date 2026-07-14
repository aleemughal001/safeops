# Action Allowlist

SafeOps must never execute arbitrary infrastructure actions. Every action must be explicitly allowlisted and checked by backend policy before execution.

Policy file:

```text
examples/policies/safe-actions.yaml
```

Currently allowed:

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

The allowlist is now enforced in code by:

```text
backend/app/policy.py
```

The executor also performs a local safety check before execution.

## Rule

Documentation is not security. The allowlist must be enforced at runtime before any action reaches the executor.
