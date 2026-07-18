# GitHub Release Checklist

Use this checklist before creating a public GitHub release.

## Repository safety

```bash
git status
find . -maxdepth 4 \( -name "*.pem" -o -name "*credentials*.csv" -o -name "rootkey.csv" -o -name "*.key" -o -name "*.zip" \) -print
```

Expected:

- Working tree clean
- No secret/key/archive output

## Demo validation

```bash
./scripts/demo_stop_services.sh
./scripts/demo_run_full.sh
./scripts/demo_stop_services.sh
```

Expected final output:

```text
Overall:            healthy
Audit valid:        PASS
Full demo completed.
```

## Tag release

For v1.0-style demo release:

```bash
git tag -a v1.0-demo -m "SafeOps v1.0 demo package"
git push origin main
git push origin --tags
```

## Suggested GitHub release title

```text
SafeOps v1.0 Demo — Human-approved Kubernetes remediation with verification and audit
```

## Suggested GitHub release summary

```text
This release demonstrates SafeOps as an open-source trust layer for AI-assisted DevOps. The demo detects a real Kubernetes rollout failure, collects evidence, identifies a missing REDIS_URL configuration, asks for human approval, enforces policy, executes a scoped Kubernetes remediation, verifies recovery, and records the workflow in a tamper-evident audit log.
```
