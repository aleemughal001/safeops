# SafeOps Demo Video Script

## Goal

Record a short 2-3 minute video that shows SafeOps as a trust layer for AI-assisted DevOps remediation.

## Video structure

### 0:00-0:20 Opening

Say:

> Hi, this is SafeOps. It is an open-source safety layer for AI-assisted DevOps remediation. The goal is not to let AI run random commands in production. The goal is to detect incidents, collect evidence, request approval, execute only allowlisted actions, verify recovery, and preserve an audit trail.

Show:

- GitHub release page
- `v1.0.1-demo-polish`

### 0:20-0:50 Problem

Say:

> Today, teams have observability tools and CI/CD tools, but incident response is still manual. Engineers have to connect logs, Kubernetes events, rollout history, approval, rollback, verification, and audit evidence under pressure.

Show:

- README or release notes
- Mention the evidence bundle asset

### 0:50-1:45 Live demo

Run:

```bash
./scripts/demo_create_investor_bundle.sh demo aleemughal001
```

Say while it runs:

> The demo starts from a healthy Kubernetes deployment, injects a real bad-image rollout failure, detects the issue, groups noisy Kubernetes symptoms into one root incident, generates a remediation plan, records approval, executes an allowlisted rollback, verifies the workload is healthy, and creates a tamper-evident audit trail.

Point out:

- Root incidents detected: 1
- Remediation plan generated
- Approval decision recorded
- Execution handoff created
- Executed actions: 1
- Verified healthy: 1
- Audit verification valid: True
- Demo result: PASSED

### 1:45-2:20 Evidence bundle

Say:

> At the end, SafeOps packages the evidence into a bundle that can be shared with investors, customers, or technical reviewers.

Show:

- Bundle zip path
- GitHub release asset

### 2:20-2:45 Closing

Say:

> This version proves the core loop: real incident detection, evidence-based planning, human approval, safe execution, verification, and auditability. The next step is feedback from DevOps engineers, SREs, platform teams, and early design partners.

## Recording tips

- Keep the video under 3 minutes.
- Do not explain every file.
- Focus on the story: failure -> evidence -> approval -> safe recovery -> audit.
- Use the latest release link: `v1.0.1-demo-polish`.
