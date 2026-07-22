# SafeOps

**Evidence-driven safe remediation for Kubernetes incidents.**

SafeOps is an open-source prototype of a safety layer for AI-assisted DevOps. It demonstrates how an operational assistant can investigate a Kubernetes failure, correlate it with CI/CD context, request human approval, execute a scoped remediation, verify recovery, write an audit trail, remember the incident, and generate a prevention handoff.

> Current status: local prototype / demo system. It is useful for demonstrating the architecture and safety model, but it is not production-ready yet.

---

## What the demo proves

SafeOps currently demonstrates this end-to-end flow:

```text
Kubernetes failure
→ evidence collection
→ root-cause explanation
→ CI/CD correlation
→ Slack-style human approval
→ policy-gated remediation
→ Kubernetes execution
→ verification
→ audit log validation
→ incident memory
→ prevention PR draft
→ incident cockpit dashboard
→ investor/demo package
```

The current demo incident is intentionally simple: `checkout-api` fails when a deployment removes the required `REDIS_URL` environment variable. SafeOps detects the missing configuration, connects it to the deployment/manifest change, proposes a low-risk scoped fix, waits for approval, restores the environment variable, verifies recovery, and creates prevention artifacts.

---

## Why this exists

Modern DevOps teams already have observability, logs, alerts, CI/CD systems, and runbooks. The hard part is safely turning all that information into action.

SafeOps focuses on the missing control layer:

- collect evidence before recommending action;
- keep remediation read-only by default until approval;
- restrict execution through an allowlist;
- limit blast radius by namespace/service/action;
- verify recovery after execution;
- create an audit trail for every decision;
- turn incidents into future prevention checks.

---

## Safety model

SafeOps is designed around safety controls rather than blind automation:

| Control | What it does |
|---|---|
| Read-first investigation | Collects Kubernetes, logs, events, and deployment evidence before action. |
| Human approval | Remediation requires explicit approval in the demo flow. |
| Action allowlist | Only approved low-risk actions are executable. |
| Scoped executor | Executor is limited to the `demo` namespace and `checkout-api` service in the demo. |
| Verification gate | Checks rollout status, deployment environment, and pod readiness after remediation. |
| Audit log | Records approval, policy decision, execution, verification, and memory. |
| Prevention handoff | Generates a local PR-style package to prevent repeat incidents. |

See also:

- [`docs/security-model.md`](docs/security-model.md)
- [`docs/action-allowlist.md`](docs/action-allowlist.md)
- [`docs/audit-log-schema.md`](docs/audit-log-schema.md)

---

## Current capabilities

| Capability | Status |
|---|---|
| Kubernetes collector | Working local demo |
| Incident root-cause explanation | Working local demo |
| Smart remediation for missing `REDIS_URL` | Working local demo |
| Real Kubernetes execution through scoped executor | Working local demo |
| Verification after remediation | Working local demo |
| Human approval prompt | Working local demo |
| CI/CD manifest correlation | Working local demo |
| Slack-style approval simulation | Working local demo |
| Prevention PR draft generation | Working local demo |
| Incident Cockpit HTML dashboard | Working local demo |
| Investor demo package | Working local demo |
| GitHub Actions CI smoke tests | Working |

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/aleemughal001/safeops.git
cd safeops
```

### 2. Requirements

The local demo expects:

- Linux shell environment;
- Docker;
- kind;
- kubectl;
- Python 3.10+;
- Git.

### 3. Run the CI smoke test

```bash
./scripts/ci_smoke_test.sh
```

Expected result:

```text
== SafeOps CI smoke test complete ==
All checks passed.
```

### 4. Run the investor demo

```bash
DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh
```

This one-command demo runs the full SafeOps story and packages the outputs under:

```text
/tmp/safeops-demo/investor-demo-package
```

Key generated files:

```text
/tmp/safeops-demo/investor-demo-package/investor-summary.md
/tmp/safeops-demo/investor-demo-package/investor-summary.json
/tmp/safeops-demo/investor-demo-package/incident-cockpit.html
/tmp/safeops-demo/investor-demo-package/logs/full-demo-output.log
/tmp/safeops-demo/investor-demo-package/artifacts/
```

Open the generated cockpit:

```bash
xdg-open /tmp/safeops-demo/investor-demo-package/incident-cockpit.html
```

Or serve it locally:

```bash
python3 -m http.server 8088 --directory /tmp/safeops-demo/investor-demo-package
```

Then open:

```text
http://127.0.0.1:8088/incident-cockpit.html
```

Stop local services after a demo:

```bash
./scripts/demo_stop_services.sh
```

---

## Main demo commands

| Command | Purpose |
|---|---|
| `./scripts/ci_smoke_test.sh` | Local CI smoke test. |
| `DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh` | Full investor-ready one-command demo. |
| `DOCKER_BUILDKIT=0 ./scripts/demo_run_full_with_cockpit.sh` | Full demo with incident cockpit. |
| `DOCKER_BUILDKIT=0 ./scripts/demo_run_full_with_slack.sh` | Full demo with Slack-style approval simulation. |
| `DOCKER_BUILDKIT=0 ./scripts/demo_run_full_with_cicd.sh` | Full demo with CI/CD correlation. |
| `./scripts/demo_stop_services.sh` | Stop demo backend/executor services. |

---

## Incident Cockpit

The generated cockpit is a local HTML dashboard that summarizes the incident in a reviewer-friendly format.

It shows:

- incident summary;
- CI/CD correlation;
- Slack-style approval;
- policy decision;
- executed remediation;
- verification checks;
- audit status;
- Kubernetes evidence;
- raw demo artifacts.

Documentation:

- [`docs/incident-cockpit-demo.md`](docs/incident-cockpit-demo.md)
- [`examples/dashboard/sample-incident-cockpit.html`](examples/dashboard/sample-incident-cockpit.html)

---

## Investor demo package

The investor demo package is designed to make the prototype easy to show without explaining every terminal step.

It includes:

- a generated incident cockpit HTML file;
- a Markdown summary;
- a JSON summary;
- full demo logs;
- CI/CD context artifacts;
- Slack approval artifacts;
- audit verification artifacts;
- prevention PR draft files.

Documentation:

- [`docs/investor-demo-package.md`](docs/investor-demo-package.md)
- [`examples/investor/README.md`](examples/investor/README.md)

---

## Repository structure

```text
backend/                  SafeOps API, policy, audit, memory, incident engine
agent/                    Kubernetes collector, sanitizer, executor
charts/                   Helm chart placeholder for SafeOps agent
demo/k8s/                 Working and broken Kubernetes demo manifests
demo/sample-app/          Demo checkout-api service
scripts/                  Demo, remediation, cockpit, investor package, CI scripts
docs/                     Architecture, safety model, demo docs, roadmap
examples/                 Example reports, audit events, Slack cards, dashboard, investor docs
.github/workflows/        GitHub Actions CI workflow
```

---

## Version milestones

| Version | Milestone |
|---|---|
| `v0.5-smart-remediation` | Smart remediation for missing `REDIS_URL`. |
| `v0.6-github-ready` | GitHub-ready docs/scripts. |
| `v0.7-repeatable-demo` | Repeatable one-command demo. |
| `v0.8-cli-report` | Clean CLI incident report. |
| `v0.9-human-approval` | Human approval gate. |
| `v1.0-demo-package` | Release/demo package. |
| `v1.1-prevention-pr` | Prevention PR simulation. |
| `v1.2-cicd-connector` | CI/CD connector context. |
| `v1.3-slack-approval` | Slack approval simulation. |
| `v1.4-incident-cockpit` | Incident cockpit dashboard. |
| `v1.5-investor-demo` | Investor demo package. |
| `v1.6-ci-smoke-tests` | GitHub Actions CI smoke tests. |

---

## Roadmap

Near-term next steps:

1. Polish GitHub landing page and reviewer docs.
2. Add screenshots/GIFs of the incident cockpit.
3. Add real GitHub/GitLab PR creation behind approval.
4. Add real Slack/Teams integration.
5. Add stronger test coverage and API tests.
6. Add persistent storage for audit and incident memory.
7. Add multi-service and multi-namespace support.
8. Add tenant/auth/RBAC model for production design.
9. Add signed/exportable audit reports.
10. Package deployment through Helm and cloud examples.

See also:

- [`docs/roadmap.md`](docs/roadmap.md)
- [`docs/project-status.md`](docs/project-status.md)

---

## Production readiness note

SafeOps is currently a prototype. It is not yet ready for production remediation in real customer environments.

Before production use, it would need at minimum:

- authentication and authorization;
- tenant isolation;
- stronger policy engine and RBAC mapping;
- persistent database-backed audit and memory;
- signed audit exports;
- real integration credentials management;
- secure secret handling;
- automated tests beyond smoke tests;
- safe rollout/rollback strategy;
- operational hardening and monitoring.

---

## License

License information should be added before external distribution.
