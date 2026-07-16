# SafeOps Roadmap

## Completed

### v0.3: Real Kubernetes dry-run closed loop

- Real Kubernetes evidence collection
- Root-cause analysis
- Approval workflow
- Policy check
- Simulated execution
- Simulated verification
- Audit log
- Incident memory

### v0.4: Real Kubernetes rollback executor

- Executor Kubernetes mode
- Real `kubectl rollout undo`
- Real rollout and pod readiness verification
- Safety allowlist for namespace and service

### v0.5: Smart REDIS_URL remediation

- Detect missing `REDIS_URL`
- Recommend `set_env_deployment`
- Validate env name and value
- Execute real `kubectl set env`
- Verify `REDIS_URL` is present
- Save healthy outcome to incident memory

## In progress

### v0.6: GitHub-ready repository

- Clean README
- Demo runbook
- Architecture overview
- Project status
- GitHub readiness checklist
- Roadmap

## Next

### v0.7: One-command repeatable demo

Add scripts:

```text
demo_setup.sh
demo_break_app.sh
demo_detect.sh
demo_fix_smart.sh
demo_verify.sh
demo_reset.sh
```

### v0.8: CLI incident report

Generate a clean report:

```text
Incident: checkout-api CrashLoopBackOff
Root cause: REDIS_URL missing
Confidence: 89%
Recommended action: Restore REDIS_URL
Approval: Required
Policy: Allowed
Execution: Successful
Verification: Healthy
Audit: Valid
```

### v0.9: Interactive approval

Add:

```text
Approve this action? yes/no
```

### v1.0 prototype: Complete local demo

- Repeatable demo
- Human approval prompt
- Clean report
- Tests
- GitHub Actions
- Screenshots
- Short demo video

## Later product roadmap

- Slack / Teams approval
- Web dashboard
- GitHub/GitLab/Jenkins connectors
- Observability connectors
- Incident database
- RBAC
- SSO/SAML
- Multi-cluster support
- Helm install
- Enterprise audit reports
- AURA commercial control plane
