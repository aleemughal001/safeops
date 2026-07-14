# Security Model

SafeOps exists because AI-assisted DevOps actions require a strict trust model.

## Safety Defaults

- Collector is read-only.
- Executor defaults to simulated execution.
- Real Kubernetes execution must be explicitly enabled.
- Actions are allowlisted.
- Dangerous actions are blocked.
- Human approval is required for remediation actions.
- Audit logs are tamper-evident.
- Incident memory stores operational context, not secrets.

## Current Runtime Controls

- Backend checks policy before executor call.
- Executor checks action allowlist before execution.
- `/verify` closes the remediation loop.
- Audit chain can detect event modification or reordering.

## Production Requirements Later

- PostgreSQL append-only audit table.
- Tenant isolation.
- KMS/Vault secret storage.
- Signed collector/executor images.
- Kubernetes namespace/action scoped RBAC.
- mTLS or signed requests between backend and executor.
- OPA/Kyverno policy integration.
- WORM/object-lock audit export.
