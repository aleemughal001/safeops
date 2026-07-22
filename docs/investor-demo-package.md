# SafeOps Investor Demo Package

Milestone 15 adds a one-command investor demo package.

## Goal

Make the complete SafeOps story easy to run and easy to show:

```bash
./scripts/demo_run_investor.sh
```

The script runs the full cockpit demo and packages the output into:

```text
/tmp/safeops-demo/investor-demo-package
```

## What it demonstrates

The demo proves the complete SafeOps loop:

```text
Kubernetes failure
→ CI/CD correlation
→ Slack-style approval
→ policy validation
→ scoped Kubernetes remediation
→ verification
→ audit validation
→ incident memory
→ prevention PR draft
→ Incident Cockpit dashboard
→ investor summary package
```

## Generated artifacts

The package contains:

```text
incident-cockpit.html
investor-summary.md
investor-summary.json
logs/full-demo-output.log
artifacts/latest_remediation_output.json
artifacts/latest_cicd_context.json
artifacts/latest_slack_approval_card.json
artifacts/latest_slack_approval_decision.json
artifacts/latest_audit_verification.json
prevention-pr/
```

## Run

```bash
cd ~/safeops-starter/safeops-starter
./scripts/demo_stop_services.sh
DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh
```

The investor demo provides non-interactive approvals:

```text
Slack approval: approve
Prevention PR: yes
```

## Open the cockpit

```bash
xdg-open /tmp/safeops-demo/investor-demo-package/incident-cockpit.html
```

If browser file opening does not work:

```bash
python3 -m http.server 8088 --directory /tmp/safeops-demo/investor-demo-package
```

Then open:

```text
http://127.0.0.1:8088/incident-cockpit.html
```

## Why this matters

Before this milestone, SafeOps required multiple terminal commands and manual artifact inspection. Milestone 15 turns the project into a repeatable demo package that can be shown to investors, grant reviewers, technical mentors, or early users.

The prototype is still not production-ready, but it now has a clear product narrative and a repeatable demonstration path.
