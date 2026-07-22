# Investor Demo Example

This directory documents the output created by:

```bash
./scripts/demo_run_investor.sh
```

Runtime outputs are generated locally under:

```text
/tmp/safeops-demo/investor-demo-package
```

The generated package includes:

- `incident-cockpit.html` — visual incident cockpit
- `investor-summary.md` — readable summary for reviewers
- `investor-summary.json` — machine-readable demo facts
- `logs/full-demo-output.log` — complete terminal demo log
- `artifacts/` — raw JSON/TXT evidence
- `prevention-pr/` — simulated prevention PR draft

No external services are required for the demo. Slack and CI/CD are simulated locally so the safety workflow can be reviewed without creating production credentials.
