# SafeOps Final Demo Checklist

## Before the demo

- Confirm Docker is running.
- Confirm Kubernetes context points to the SafeOps kind cluster.
- Confirm the demo namespace exists.
- Confirm GitHub Actions is green.
- Confirm working tree is clean.

## Commands to run

```bash
git status
gh run list --limit 5
./scripts/demo_release_candidate_check.sh
./scripts/demo_fresh_clone_check.sh
./scripts/demo_create_investor_bundle.sh demo aleemughal001
```

## What to show

- GitHub README top demo section
- One-command demo output
- Investor evidence bundle output
- Execution record
- Tamper-evident audit trail
- Release-candidate report
- Fresh clone validation report

## Success criteria

- Final cluster state is healthy.
- Open root incidents after recovery is 0.
- Executed allowlisted actions is 1.
- Verified healthy actions is 1.
- Audit verification valid is True.
- Investor evidence bundle zip is created.
