# Demo Scenario

## Incident

`checkout-api` enters `CrashLoopBackOff` after a deployment because the required environment variable `REDIS_URL` is missing.

## Expected SafeOps Behavior

1. Receive incident evidence.
2. Explain likely root cause.
3. Recommend rollback.
4. Record recommendation in audit log.
5. Receive human approval.
6. Check policy allowlist.
7. Execute action in simulated/dry-run mode.
8. Verify rollout, pod readiness, service health, and error rate recovery.
9. Save incident memory.
10. Verify audit chain.

## Run

Terminal 1:

```bash
./scripts/run_executor.sh
```

Terminal 2:

```bash
./scripts/run_backend.sh
```

Terminal 3:

```bash
./scripts/test_closed_loop.sh
```
