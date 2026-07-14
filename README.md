# SafeOps

SafeOps is an open-source trust and safety layer for AI-assisted DevOps and Kubernetes remediation.

It helps engineering teams safely use AI agents to investigate Kubernetes and CI/CD incidents, explain root causes with evidence, recommend remediation steps, request human approval, execute only allowlisted actions, verify recovery, record every step in a tamper-evident audit log, and save incident memory for future similarity detection.

## First Use Case

The first SafeOps demo focuses on a Kubernetes deployment failure.

A sample service enters `CrashLoopBackOff` after a broken deployment. SafeOps collects Kubernetes events, pod status, logs, deployment history, Git commit context, and CI/CD pipeline results. It then generates an evidence-backed root-cause explanation and recommends a safe rollback. The rollback only executes after human approval, passes through policy enforcement, calls the executor, verifies recovery, stores incident memory, and writes a tamper-evident audit trail.

## Closed-Loop MVP Workflow

```text
analyze incident
  ↓
create recommendation
  ↓
record recommendation audit event
  ↓
human approves action
  ↓
policy engine checks allowlist
  ↓
executor runs approved action in dry-run/simulated mode
  ↓
executor verifies recovery
  ↓
backend saves incident memory
  ↓
audit chain verifies as valid
```

## Core Components

- Kubernetes read-only collector
- Helm chart
- Telemetry sanitization
- Enforced action allowlist
- Policy templates
- Approval workflow
- Executor service with `/execute` and `/verify`
- Tamper-evident JSONL audit log
- Incident memory JSONL store
- Incident replay demo structure
- Local Kubernetes demo environment

## Project Structure

```text
safeops-starter/
├── docs/                      # Architecture and security documentation
├── backend/                   # FastAPI backend and incident engine
├── agent/                     # Collector, sanitizer, executor service
├── charts/safeops-agent/      # Helm chart skeleton
├── demo/                      # Local Kubernetes demo app and manifests
├── examples/                  # Policies, audit events, incident reports
└── scripts/                   # Local helper scripts
```

## Run the Closed-Loop Demo

Open one terminal and start the executor service:

```bash
./scripts/run_executor.sh
```

Open another terminal and start the backend:

```bash
./scripts/run_backend.sh
```

Open a third terminal and run the closed-loop test:

```bash
./scripts/test_closed_loop.sh
```

Expected output:

- Incident analysis identifies missing `REDIS_URL` as likely root cause.
- Recommendation is `rollout_undo_deployment`.
- Human approval is recorded.
- Policy engine allows the action.
- Executor simulates rollback.
- `/verify` confirms recovery.
- Incident memory is saved.
- Audit chain validates successfully.

## Safety Defaults

The prototype defaults to dry-run/simulated execution. Real Kubernetes execution must be enabled explicitly and must use narrowly scoped RBAC.

Environment variables:

```bash
SAFEOPS_EXECUTOR_URL=http://localhost:8010
SAFEOPS_AUDIT_LOG_PATH=/tmp/safeops/audit-log.jsonl
SAFEOPS_MEMORY_PATH=/tmp/safeops/incident-memory.jsonl
SAFEOPS_POLICY_PATH=./examples/policies/safe-actions.yaml
SAFEOPS_EXECUTOR_MODE=simulate # simulate | kubernetes
```

## API Highlights

Backend:

- `POST /incidents/analyze`
- `POST /approvals`
- `GET /incidents/{incident_id}`
- `GET /audit-log`
- `GET /audit-log/verify`
- `GET /memory`

Executor:

- `POST /execute`
- `POST /verify`
- `GET /health`

## Commercial Boundary

SafeOps is the open-source trust foundation:

- read-only collector
- telemetry sanitization
- action allowlist
- policy templates
- audit log schema
- approval workflow
- local replay/demo environment

The private commercial product later, AURA Cloud / AURA Pro, keeps the advanced intelligence layer:

- hosted dashboard
- AI agent orchestration
- incident memory engine at scale
- Adaptive Reliability Engine
- advanced connectors
- enterprise RBAC/SSO
- compliance reporting
- customer-specific knowledge graph
- advanced remediation intelligence
