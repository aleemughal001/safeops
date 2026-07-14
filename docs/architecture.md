# SafeOps Architecture

SafeOps is the open-source trust layer for AI-assisted DevOps. The current prototype is intentionally small but now closes the end-to-end loop.

## Current Prototype Flow

```text
Incident payload
  ↓
Backend /incidents/analyze
  ↓
Rule-based incident engine
  ↓
Recommendation + evidence + confidence + blast radius
  ↓
Tamper-evident audit event: recommendation.created
  ↓
Backend /approvals
  ↓
Human approval recorded
  ↓
Policy engine checks examples/policies/safe-actions.yaml
  ↓
Executor service /execute
  ↓
Executor service /verify
  ↓
Incident memory saved
  ↓
Audit chain can be verified
```

## Backend Components

- `main.py`: FastAPI API and closed-loop orchestration.
- `incident_engine.py`: deterministic MVP incident explanation.
- `policy.py`: loads and enforces the action allowlist.
- `executor_client.py`: calls the customer-side executor service.
- `audit_log.py`: append-only JSONL audit log with hash chaining.
- `incident_memory.py`: persistent incident memory with simple similarity search.

## Customer-Side Agent Components

- `collector/collector.py`: read-only Kubernetes collector.
- `sanitizer/sanitizer.py`: masks common secrets and sensitive values.
- `executor/executor.py`: FastAPI executor service with `/execute` and `/verify`.

## Design Principle

The AI/devops brain may recommend actions, but SafeOps enforces the trust path:

1. Evidence must be recorded.
2. Action must be allowlisted.
3. Human approval must be present when required.
4. Execution must be scoped.
5. Recovery must be verified.
6. Audit trail must be tamper-evident.
