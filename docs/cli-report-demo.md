# SafeOps CLI Incident Report

Milestone 8 adds a clean CLI report for the repeatable Kubernetes demo.

The full demo still runs the real workflow:

1. Reset the `checkout-api` deployment to a known-good manifest.
2. Apply the broken manifest that removes `REDIS_URL`.
3. Collect Kubernetes evidence.
4. Analyze the incident.
5. Recommend the safe remediation action.
6. Require approval.
7. Execute the allowlisted Kubernetes fix.
8. Verify rollout health, pod readiness, deployment config, and audit validity.

The new report turns the raw collector/remediation JSON into a readable summary:

```text
SafeOps Incident Report
========================
Incident ID:        inc_checkout-api_...
Service:            checkout-api
Namespace:          demo
Root cause:         The latest deployment likely removed or misconfigured REDIS_URL
Confidence:         89%

Recommendation
--------------
Action:             set_env_deployment
Risk:               low
Blast radius:       checkout-api in namespace demo only

Verification
------------
Overall:            healthy
- rollout_status: passed
- deployment_env: passed
- pod_readiness: passed

Audit
-----
Audit valid:        PASS
```

Run it after a demo:

```bash
./scripts/demo_report.sh
```

Or run the full demo with the report included:

```bash
./scripts/demo_run_full.sh
```
