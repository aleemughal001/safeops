# SafeOps Incident Cockpit Demo

Milestone 14 adds a local HTML incident cockpit for the SafeOps demo.

The cockpit turns the terminal-heavy workflow into a browser-friendly report that can be shown to engineers, grant reviewers, or early investors. It does not require a SaaS dashboard, external hosting, or cloud credentials.

## What the cockpit shows

The generated HTML report includes:

- Incident summary
- Kubernetes service and namespace
- Root cause and confidence
- CI/CD correlation context
- Slack-style approval decision
- Policy allowlist decision
- Executed remediation command
- Verification checks
- Audit verification
- Kubernetes evidence
- Links to local raw demo artifacts

## Run the full cockpit demo

From the repository root:

```bash
./scripts/demo_stop_services.sh
DOCKER_BUILDKIT=0 ./scripts/demo_run_full_with_cockpit.sh
```

When the Slack approval simulation asks:

```text
Simulate Slack approval? Type 'approve' or 'yes' to click [Approve Fix]:
```

Type:

```text
approve
```

When the prevention PR simulation asks, type:

```text
yes
```

## Open the cockpit

After the demo completes, open this local file in a browser:

```text
/tmp/safeops-demo/incident-cockpit.html
```

On Ubuntu desktop, you can usually run:

```bash
xdg-open /tmp/safeops-demo/incident-cockpit.html
```

If `xdg-open` is unavailable, copy the file path and open it from your browser.

## Generate only the cockpit

If the latest demo artifacts already exist, you can regenerate the report without rerunning the whole demo:

```bash
./scripts/demo_incident_cockpit.sh
```

The script reads these local files when available:

```text
/tmp/safeops-demo/latest_remediation_output.json
/tmp/safeops-demo/latest_cicd_context.json
/tmp/safeops-demo/latest_slack_approval_card.json
/tmp/safeops-demo/latest_slack_approval_decision.json
/tmp/safeops-demo/latest_audit_verification.json
```

If the backend is running, it also attempts to call:

```text
http://localhost:8000/audit/verify
```

and saves the result to:

```text
/tmp/safeops-demo/latest_audit_verification.json
```

## Why this matters

Before this milestone, SafeOps proved a strong workflow, but most of the value was visible only in terminal output. The Incident Cockpit makes the same workflow easier to understand:

```text
detect Kubernetes failure
→ correlate with CI/CD
→ show Slack approval
→ policy validate
→ execute safe remediation
→ verify recovery
→ audit
→ remember
→ recommend prevention
→ show everything in one report
```

## Current limitation

This is a static local HTML report, not a full live SaaS dashboard. That is intentional for the prototype. It gives a realistic product demo without adding authentication, database migrations, tenancy, or frontend infrastructure too early.
