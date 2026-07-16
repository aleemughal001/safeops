# One-command repeatable demo

Milestone 7 turns the SafeOps prototype into a repeatable local demo.

The goal is to make the full flow easy to run without manually copying every command:

1. prepare the kind cluster and demo application,
2. start the SafeOps backend and Kubernetes-mode executor,
3. reset the application to a known-good state,
4. break the deployment by removing `REDIS_URL`,
5. collect real Kubernetes evidence,
6. approve the smart remediation,
7. verify that Kubernetes recovered,
8. verify the SafeOps audit chain.

## Full demo

```bash
./scripts/demo_run_full.sh
```

This leaves the backend and executor running in the background. Stop them with:

```bash
./scripts/demo_stop_services.sh
```

Logs are written under:

```text
/tmp/safeops-demo/logs/
```

The latest incident ID is saved at:

```text
/tmp/safeops-demo/latest_incident_id
```

## Step-by-step demo

```bash
./scripts/demo_setup.sh
./scripts/demo_start_services.sh
./scripts/demo_status.sh
./scripts/demo_reset_healthy.sh
./scripts/demo_break_app.sh
./scripts/demo_detect.sh
./scripts/demo_smart_fix.sh
./scripts/demo_verify.sh
```

## What this proves

The repeatable demo proves that SafeOps can perform a safe closed loop:

```text
real Kubernetes incident
→ evidence collection
→ root-cause explanation
→ recommended remediation
→ approval
→ policy allowlist
→ real Kubernetes action
→ verification
→ audit log
→ memory
```

## Safety boundaries

The current demo executor is intentionally narrow. It allows only the demo namespace and demo service:

```text
namespace: demo
service: checkout-api
env var: REDIS_URL
```

It does not support arbitrary shell commands, deleting resources, reading secrets, or touching production namespaces.
