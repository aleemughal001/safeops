# SafeOps

**SafeOps** is an open-source safety layer for AI-assisted DevOps remediation.

It demonstrates a safe closed-loop workflow for Kubernetes incidents:

```text
Detect incident → collect evidence → explain root cause → recommend action
→ require human approval → enforce policy → execute safe remediation
→ verify recovery → write audit log → save incident memory
```

The current demo focuses on one realistic failure mode:

```text
checkout-api enters CrashLoopBackOff because REDIS_URL was removed from the deployment.
```

SafeOps detects the missing environment variable, recommends a constrained fix, waits for human approval, applies the safe Kubernetes remediation, verifies recovery, and records the action in audit + memory.

---

## Why SafeOps exists

Modern DevOps teams already have alerts, dashboards, logs, and CI/CD systems. The hard part is not only knowing that something broke. The hard part is answering:

```text
What changed?
Why did it break?
What is the safest fix?
Who approved it?
Did it actually recover?
Can we prove what happened later?
```

SafeOps is designed around those questions. It is intentionally conservative: no uncontrolled shell access, no automatic production changes, no hidden remediation, and no action without policy and approval.

---

## Current demo capabilities

SafeOps currently demonstrates:

- Real Kubernetes evidence collection from pods, logs, events, and deployment config
- Root-cause analysis for a CrashLoopBackOff caused by missing `REDIS_URL`
- Recommended remediation based on evidence
- Human approval workflow through an API/script
- Policy allowlist enforcement before execution
- Real Kubernetes executor mode
- Smart remediation using `kubectl set env`
- Real verification of rollout status, pod readiness, and deployment environment
- Tamper-evident audit log with hash chaining
- Incident memory for similar future incidents

---

## What this demo proves

This prototype proves the core SafeOps safety workflow:

```text
SafeOps can detect a real Kubernetes incident, explain the likely root cause,
recommend a constrained action, require approval, enforce policy, execute the fix,
verify recovery, and save an auditable record.
```

The strongest current path is the smart remediation flow:

```text
CrashLoopBackOff caused by missing REDIS_URL
→ SafeOps recommends set_env_deployment
→ engineer approves
→ policy validates namespace/service/env name/env value
→ executor runs kubectl set env
→ deployment becomes healthy
→ audit + memory are updated
```

---

## What this demo does not claim yet

SafeOps is still a local prototype. It is **not production-ready** yet.

Missing production features include:

- Authentication and user management
- RBAC and team permissions
- Persistent database for incidents and approvals
- Real Slack / Teams approval buttons
- Multi-cluster support
- SaaS dashboard
- Secrets management
- Full CI test suite
- Helm-based production deployment
- Enterprise audit/export controls
- SSO/SAML
- Hardened runtime security

---

## Repository structure

```text
safeops-starter/
├── agent/
│   ├── collector/          # Kubernetes evidence collector
│   ├── executor/           # Safe remediation executor
│   └── sanitizer/          # Telemetry sanitizer prototype
├── backend/
│   └── app/                # FastAPI backend, policy, audit, memory, incident engine
├── demo/
│   ├── k8s/                # Working and broken Kubernetes manifests
│   └── sample-app/         # Demo checkout-api app
├── docs/                   # Architecture, security model, demo docs, roadmap
├── examples/               # Example policy, reports, audit events
└── scripts/                # Local run and demo helper scripts
```

---

## Prerequisites

The local demo expects:

- Linux VM or local Linux environment
- Docker
- kubectl
- kind
- Python 3.10+
- python3.10-venv

Example packages on Ubuntu:

```bash
sudo apt update
sudo apt install python3.10-venv python3-pip -y
```

---

## Quick start: run the demo

### 1. Start the executor

Terminal 1:

```bash
cd ~/safeops-starter/safeops-starter
./scripts/run_executor_kubernetes.sh
```

Expected:

```text
Uvicorn running on http://0.0.0.0:8010
```

### 2. Start the backend

Terminal 2:

```bash
cd ~/safeops-starter/safeops-starter
./scripts/run_backend.sh
```

Expected:

```text
Uvicorn running on http://0.0.0.0:8000
```

### 3. Confirm health

Terminal 3:

```bash
curl -sS http://localhost:8010/health
curl -sS http://localhost:8000/health
```

Expected executor health includes:

```json
{
  "status": "ok",
  "mode": "kubernetes",
  "allowed_namespaces": ["demo"],
  "allowed_services": ["checkout-api"],
  "allowed_env_names": ["REDIS_URL"]
}
```

---

## Demo flow: smart REDIS_URL remediation

### 1. Confirm the demo app is healthy

```bash
kubectl -n demo get pods
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
```

### 2. Break the app

```bash
kubectl apply -f demo/k8s/checkout-api-broken.yaml
kubectl -n demo get pods -w
```

Wait until the new pod shows `CrashLoopBackOff`, then press `CTRL+C`.

### 3. Collect evidence and analyze incident

```bash
./scripts/run_collector_once.sh
```

Copy the returned `incident_id`.

Expected recommendation:

```text
action_id: set_env_deployment
env_name: REDIS_URL
env_value: redis://redis.demo.svc.cluster.local:6379
```

### 4. Approve the smart remediation

```bash
./scripts/approve_set_env_fix.sh <INCIDENT_ID>
```

Example:

```bash
./scripts/approve_set_env_fix.sh inc_checkout-api_1784229327
```

SafeOps will execute the constrained command:

```bash
kubectl -n demo set env deployment/checkout-api REDIS_URL=redis://redis.demo.svc.cluster.local:6379
```

### 5. Verify recovery

```bash
kubectl -n demo get pods
kubectl -n demo rollout status deployment/checkout-api --timeout=120s
kubectl -n demo get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
```

Expected:

```text
deployment "checkout-api" successfully rolled out
REDIS_URL is present on the deployment
```

### 6. Verify audit and memory

```bash
curl -s http://localhost:8000/audit-log/verify | python3 -m json.tool
curl -s http://localhost:8000/memory | python3 -m json.tool
```

Expected audit:

```json
{
  "valid": true,
  "issues": []
}
```

---

## Safety model

SafeOps does not execute arbitrary remediation commands.

The current smart remediation is constrained to:

```text
namespace: demo
service/deployment: checkout-api
action: set_env_deployment
env_name: REDIS_URL
env_value: redis://redis.demo.svc.cluster.local:6379
```

The executor should reject unrelated namespaces, services, action names, environment variables, and values.

See:

- [`docs/security-model.md`](docs/security-model.md)
- [`docs/action-allowlist.md`](docs/action-allowlist.md)
- [`docs/smart-remediation.md`](docs/smart-remediation.md)

---

## Current milestones

| Milestone | Status | Description |
|---|---:|---|
| Milestone 3 | Complete | Real Kubernetes incident dry-run closed loop |
| Milestone 4 | Complete | Real Kubernetes rollback executor |
| Milestone 5 | Complete | Smart `REDIS_URL` remediation |
| Milestone 6 | In progress | GitHub-ready repo and documentation |

---

## Roadmap

Near-term:

- One-command repeatable demo scripts
- CLI incident report output
- Interactive approval prompt
- Better incident timeline
- Tests for policy and executor safety
- GitHub Actions CI

Later:

- Slack / Teams approval
- Web dashboard
- Persistent incident database
- RBAC and authentication
- Multi-cluster support
- More remediation playbooks
- Helm-based installation
- Enterprise audit export

---

## License

License is not finalized yet. Add a license before public release.

---

## Project positioning

SafeOps is the open-source safety foundation for AI-assisted DevOps remediation.

A future commercial platform can build on top of this foundation with dashboard, agent orchestration, enterprise controls, integrations, RBAC, SSO, advanced memory, and managed deployment.
