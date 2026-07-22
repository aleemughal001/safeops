# GitHub Landing Page Guide

This guide explains how to present the SafeOps repository to reviewers, mentors, investors, or technical collaborators.

## What the first 30 seconds should communicate

SafeOps is a safety layer for AI-assisted DevOps remediation. It is not just an alerting tool and not just a chatbot. The demo proves a controlled incident response loop:

```text
detect -> explain -> correlate -> approve -> execute -> verify -> audit -> prevent
```

The repository should make three ideas immediately clear:

1. SafeOps acts only after evidence is collected.
2. Remediation is policy-gated and human-approved.
3. The system verifies recovery and creates prevention artifacts.

## Best reviewer path

A reviewer should follow this path:

1. Open `README.md`.
2. Check the GitHub Actions badge/status through the Actions tab.
3. Run `./scripts/ci_smoke_test.sh`.
4. Run `DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh`.
5. Open `/tmp/safeops-demo/investor-demo-package/incident-cockpit.html`.
6. Read `/tmp/safeops-demo/investor-demo-package/investor-summary.md`.

## Demo talking points

Use this simple explanation:

> SafeOps detects that a Kubernetes service is failing, gathers evidence, correlates the issue to a CI/CD manifest change, asks for human approval, executes only an allowlisted low-risk fix, verifies the service is healthy again, records an audit trail, and generates a prevention PR draft so the same issue does not happen again.

## Important files to show

| File | Why it matters |
|---|---|
| `README.md` | Main landing page. |
| `.github/workflows/ci.yml` | Shows automated CI smoke checks. |
| `scripts/demo_run_investor.sh` | One-command demo entry point. |
| `scripts/ci_smoke_test.sh` | Local and GitHub CI validation. |
| `docs/security-model.md` | Safety design. |
| `docs/action-allowlist.md` | Why the executor is controlled. |
| `docs/investor-demo-package.md` | How the packaged demo works. |
| `docs/incident-cockpit-demo.md` | How the cockpit dashboard works. |

## What not to overclaim

Do not describe SafeOps as production-ready yet. The correct framing is:

- prototype;
- local demo;
- architecture proof;
- safety-first control loop;
- investor/reviewer demo package.

Avoid saying it already has:

- real SaaS tenancy;
- production RBAC;
- real Slack integration;
- real GitHub PR creation;
- persistent managed database;
- enterprise security hardening.

## Recommended next improvements

1. Add screenshots of the Incident Cockpit to the README.
2. Add a short demo GIF.
3. Add release notes for `v1.6` and future versions.
4. Add real PR creation behind approval.
5. Add real Slack approval integration.
6. Add API tests and coverage reporting.
