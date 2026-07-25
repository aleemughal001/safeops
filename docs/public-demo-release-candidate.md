# SafeOps Public Demo Release Candidate

This milestone prepares SafeOps for a public/investor demo review after the real Kubernetes recovery loop and investor evidence bundle are working.

## What this milestone adds

- A release-candidate checklist for the public demo state.
- A read-only release-candidate report generator.
- A demo command that verifies key repo assets, expected tags, README markers, and safety documentation.
- A sample report for investors, engineers, and early users.

## Command

```bash
./scripts/demo_release_candidate_check.sh
```

The command writes:

```text
/tmp/safeops-demo/safeops-release-candidate-report.json
/tmp/safeops-demo/safeops-release-candidate-report.md
```

## What the report checks

- README has the real Kubernetes demo section.
- One-command real demo is documented.
- Investor evidence bundle command is documented.
- Core safety docs exist.
- Real remediation planner, approval gate, approved executor, audit trail, and bundle docs exist.
- Expected v2.3 through v2.9 tags exist locally.
- Working tree is clean.

## Release-candidate standard

SafeOps is ready for a public demo release candidate when:

- Local CI passes.
- GitHub Actions passes.
- The one-command real SafeOps loop passes.
- The investor evidence bundle command passes.
- The release-candidate check reports `Release candidate ready: True`.

## Known limits

This is still a prototype/demo release candidate, not a production SaaS. Production work still requires auth, RBAC, tenant isolation, durable persistence, real Slack/Teams integrations, hosted deployment, customer onboarding, and security review.
