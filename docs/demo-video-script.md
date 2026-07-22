# SafeOps Demo Video Script

This guide is for recording a short reviewer/investor demo of SafeOps.

## Goal

Record a 2-3 minute screen walkthrough that shows SafeOps as a safe AI-assisted DevOps remediation prototype.

## Recording flow

1. Open the GitHub repository README.
2. Show the Actions tab with SafeOps CI passing.
3. Run the one-command investor demo.
4. Open the redesigned Incident Cockpit dashboard.
5. Explain the safety model: evidence, approval, policy, execution, verification, audit, prevention.

## Command to run before recording

```bash
cd ~/safeops-starter/safeops-starter
./scripts/demo_stop_services.sh
DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh
```

## Command to open the dashboard

```bash
python3 -m http.server 8088 --directory /tmp/safeops-demo/investor-demo-package
```

Open:

```text
http://127.0.0.1:8088/incident-cockpit.html
```

## 30-second pitch

SafeOps is an open-source safety layer for AI-assisted DevOps remediation. It detects production-style Kubernetes failures, explains the root cause with evidence, correlates the incident with CI/CD changes, requests human approval, checks policy, executes only scoped approved actions, verifies recovery, records an audit trail, and creates a prevention handoff so the same outage does not repeat.

## 2-minute narration

Hi, this is SafeOps, an open-source safety layer for AI-assisted DevOps remediation.

The problem is that production incidents are fragmented across Kubernetes logs, CI/CD history, chat approvals, manual commands, and audit records. SafeOps brings these pieces into one controlled workflow.

In this demo, the checkout-api service breaks because a required environment variable, REDIS_URL, is missing after a deployment.

SafeOps collects Kubernetes evidence including pod status, logs, events, and deployment configuration. It identifies that REDIS_URL is missing from the deployment.

Next, SafeOps correlates the failure with CI/CD context. It compares the known-good manifest with the broken manifest and finds that REDIS_URL existed before but is missing in the deployed version.

SafeOps does not blindly change infrastructure. It generates a Slack-style approval request with the root cause, proposed command, risk level, blast radius, and safety controls.

After approval, SafeOps checks the action against its policy allowlist. The fix is scoped only to checkout-api in the demo namespace. SafeOps then restores REDIS_URL using kubectl set env.

After execution, SafeOps verifies the rollout, confirms the environment variable is restored, checks pod readiness, writes an audit log, saves incident memory, and creates a prevention PR draft.

Finally, the redesigned Incident Cockpit shows the full story in one place: incident summary, CI/CD correlation, Slack approval, policy decision, remediation, verification, audit, Kubernetes evidence, and prevention artifacts.

The core idea is simple: AI should not directly operate production infrastructure without controls. SafeOps makes AI-assisted remediation evidence-driven, approval-gated, policy-controlled, verified, auditable, and preventive.
