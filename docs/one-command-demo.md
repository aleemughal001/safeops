# One-Command Demo

SafeOps includes a repeatable local demo that breaks a Kubernetes deployment, analyzes the incident, requests human approval, applies a safe remediation, verifies recovery, and prints a clean incident report.

## Full interactive demo

```bash
./scripts/demo_run_full.sh
```

The script will:

1. Check or create the local kind cluster.
2. Build and load the checkout-api demo image.
3. Apply the known-good Kubernetes manifest.
4. Start the SafeOps executor and backend.
5. Reset checkout-api to a healthy state.
6. Apply a broken manifest that removes `REDIS_URL`.
7. Run the Kubernetes collector.
8. Analyze the incident.
9. Show a human approval prompt.
10. Apply the approved safe remediation.
11. Verify Kubernetes recovery.
12. Verify the audit log.
13. Print a clean CLI incident report.

When prompted, type:

```text
yes
```

## Non-interactive demo

For recordings or scripted runs:

```bash
SAFEOPS_AUTO_APPROVE=true ./scripts/demo_run_full.sh
```

## Stop demo services

```bash
./scripts/demo_stop_services.sh
```

## Individual steps

```bash
./scripts/demo_setup.sh
./scripts/demo_start_services.sh
./scripts/demo_reset_healthy.sh
./scripts/demo_break_app.sh
./scripts/demo_detect.sh
./scripts/demo_approve_prompt.sh
./scripts/demo_verify.sh
./scripts/demo_report.sh
```

## Expected result

The final report should show:

```text
Verification: healthy
Audit valid: PASS
REDIS_URL present=True
```
