# SafeOps Milestone 11: Prevention Suggestion / Prevention PR Simulation

Milestone 11 moves the demo beyond remediation.

Before this milestone, SafeOps could detect a Kubernetes incident, recommend a safe fix, ask for human approval, execute a scoped remediation, verify recovery, audit the workflow, and remember the incident.

This milestone adds the next DevOps-engineer behavior:

> After fixing the incident, SafeOps recommends a prevention guardrail so the same mistake does not happen again.

## Why this matters

A remediation-only product can look like an automation script.

A prevention loop makes SafeOps feel more like an AI DevOps Engineer:

1. It fixes the incident.
2. It remembers the cause and outcome.
3. It proposes a guardrail.
4. It prepares a PR-style change that an engineer can review.

## Demo flow

Run the normal full demo:

```bash
./scripts/demo_run_full.sh
```

After the clean incident report, SafeOps prints a prevention recommendation:

```text
SafeOps Prevention Recommendation
=================================
Incident ID:        inc_checkout-api_...
Service:            checkout-api
Root cause:         REDIS_URL was missing or misconfigured

Suggested guardrails
--------------------
1. Add a required-env check for deployment/checkout-api.
2. Fail CI/CD if REDIS_URL is missing from Kubernetes manifests.
3. Add the incident fingerprint to SafeOps memory.
4. Later: open this as a real GitHub/GitLab PR after approval.
```

If the user approves, SafeOps generates a simulated prevention PR package under:

```bash
/tmp/safeops-demo/prevention-pr
```

## Generated PR draft files

The simulation creates:

```text
/tmp/safeops-demo/prevention-pr/.safeops/prevention/checkout-api-required-env.yaml
/tmp/safeops-demo/prevention-pr/ci/check_required_env.py
/tmp/safeops-demo/prevention-pr/.github/workflows/safeops-required-env-check.yml
/tmp/safeops-demo/prevention-pr/PR_TITLE.txt
/tmp/safeops-demo/prevention-pr/PR_BODY.md
/tmp/safeops-demo/prevention-pr/README.md
```

These files are intentionally generated outside the repository so the demo does not dirty the Git working tree.

## Why simulated PR first?

A real PR requires a GitHub/GitLab connector, token handling, branch creation, commit creation, API calls, and permission management.

That belongs in Milestone 12.

Milestone 11 proves the product behavior safely:

```text
fix -> remember -> suggest prevention -> prepare reviewable PR draft
```

## Future Milestone 12 behavior

Milestone 12 should turn the simulated PR into a real connector workflow:

1. Detect successful remediation.
2. Generate prevention patch.
3. Ask approval to open PR.
4. Create GitHub/GitLab branch.
5. Commit generated prevention files.
6. Open PR with SafeOps incident context.
7. Link PR back to the SafeOps incident report.

## Positioning

This is an important differentiation step. SafeOps is not only answering “what broke?” or “how do I fix it?”

It starts answering:

> How do we stop this same failure from happening again?
