# SafeOps Architecture Overview

## High-level flow

```text
Kubernetes cluster
   ↓
Collector agent
   ↓
FastAPI backend
   ↓
Incident engine + policy + audit + memory
   ↓
Human approval
   ↓
Executor agent
   ↓
Kubernetes remediation
   ↓
Verification
   ↓
Audit + memory
```

## Components

### Collector

Location:

```text
agent/collector/collector.py
```

Responsibilities:

- Read Kubernetes pod status
- Read logs and previous logs
- Read deployment environment config
- Read Kubernetes events
- Send evidence to backend

### Backend

Location:

```text
backend/app/
```

Responsibilities:

- Analyze incident evidence
- Generate root cause
- Recommend action
- Receive approval
- Enforce policy
- Call executor
- Verify result
- Write audit log
- Save incident memory

### Policy engine

Location:

```text
backend/app/policy.py
```

Responsibilities:

- Allow only approved actions
- Validate namespace
- Validate service/deployment
- Validate environment variable name
- Validate environment variable value

### Executor

Location:

```text
agent/executor/executor.py
```

Responsibilities:

- Execute safe remediation only after policy approval
- Support simulate mode
- Support Kubernetes mode
- Reject unsafe or non-allowlisted actions
- Verify rollout and pod readiness

### Audit log

Location:

```text
/tmp/safeops/audit-log.jsonl
```

Responsibilities:

- Store incident, approval, execution, verification events
- Hash-chain events to detect tampering
- Provide verification endpoint

### Incident memory

Location:

```text
/tmp/safeops/incident-memory.jsonl
```

Responsibilities:

- Store previous incident outcomes
- Return similar incidents during analysis
- Help future recommendations

## Current remediation actions

### rollout_undo_deployment

Runs:

```bash
kubectl -n demo rollout undo deployment/checkout-api
```

### set_env_deployment

Runs:

```bash
kubectl -n demo set env deployment/checkout-api REDIS_URL=redis://redis.demo.svc.cluster.local:6379
```

## Current safety boundaries

The executor is limited to:

```text
namespace: demo
service: checkout-api
env name: REDIS_URL
env value: redis://redis.demo.svc.cluster.local:6379
```

It should not allow arbitrary commands, delete operations, secret reads, or production namespace changes.
