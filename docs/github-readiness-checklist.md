# GitHub Readiness Checklist

Use this checklist before pushing SafeOps publicly.

## Repository hygiene

Run:

```bash
git status
find . -maxdepth 4 \( -name "*.pem" -o -name "*credentials*.csv" -o -name "rootkey.csv" -o -name "*.key" -o -name "*.zip" \) -print
```

Expected:

```text
working tree clean
no output from find command
```

## Required files

- [ ] README.md explains the project clearly
- [ ] docs/demo-runbook.md exists
- [ ] docs/project-status.md exists
- [ ] docs/architecture-overview.md exists
- [ ] docs/security-model.md exists
- [ ] docs/action-allowlist.md exists
- [ ] docs/smart-remediation.md exists
- [ ] examples/policies/safe-actions.yaml exists

## Demo quality

- [ ] Demo app starts healthy
- [ ] Broken manifest creates CrashLoopBackOff
- [ ] Collector creates an incident
- [ ] Backend recommends `set_env_deployment`
- [ ] Approval script works
- [ ] Executor runs in Kubernetes mode
- [ ] Verification returns healthy
- [ ] Audit log verifies successfully
- [ ] Memory stores successful incident

## Before public release

- [ ] Add license
- [ ] Add screenshots or terminal demo output
- [ ] Add architecture diagram image
- [ ] Add contribution guidelines
- [ ] Add issue templates
- [ ] Add GitHub Actions test workflow
- [ ] Remove local-only assumptions where possible

## Suggested first GitHub release tag

```bash
git tag -a v0.6-github-ready -m "SafeOps v0.6 GitHub-ready demo documentation"
```
