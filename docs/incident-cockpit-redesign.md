# SafeOps Incident Cockpit Redesign

Milestone 18 upgrades the local Incident Cockpit from a basic HTML report into a polished, Tabler-based dashboard layout.

## What changed

- Keeps the same SafeOps data sources and demo artifacts.
- Uses a single generated HTML file, so no Node.js, npm, frontend build, or hosted service is required.
- Loads Tabler dashboard CSS and Tabler icons from CDN for presentation styling.
- Adds a professional dashboard layout with sidebar navigation, hero summary, metric cards, timeline, evidence table, prevention section, and artifact cards.

## Data sources

The dashboard reads local demo artifacts from `/tmp/safeops-demo`:

- `latest_remediation_output.json`
- `latest_cicd_context.json`
- `latest_slack_approval_card.json`
- `latest_slack_approval_decision.json`
- `latest_audit_verification.json`
- `prevention-pr/`

## Generate the dashboard

Run the full investor demo:

```bash
DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh
```

Or regenerate only the cockpit from existing artifacts:

```bash
./scripts/demo_incident_cockpit.sh
```

Output:

```text
/tmp/safeops-demo/incident-cockpit.html
```

The investor package copies the redesigned cockpit to:

```text
/tmp/safeops-demo/investor-demo-package/incident-cockpit.html
```

## Open in browser

```bash
python3 -m http.server 8088 --directory /tmp/safeops-demo/investor-demo-package
```

Then open:

```text
http://127.0.0.1:8088/incident-cockpit.html
```

## Why this design

The cockpit is meant to help a reviewer understand the complete SafeOps flow quickly:

1. Incident detected
2. Kubernetes evidence collected
3. CI/CD change correlated
4. Slack-style approval captured
5. Policy allowlist passed
6. Remediation executed
7. Recovery verified
8. Audit chain validated
9. Prevention PR package generated
10. Raw artifacts preserved

The goal is to make the prototype more credible for demos without adding unnecessary frontend complexity.
