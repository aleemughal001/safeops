# One-Command Real SafeOps Demo

Milestone 27 adds a single command that runs the complete real Kubernetes SafeOps loop.

```bash
./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
```

The demo performs the following flow:

1. Reset the demo workload to a known-good image.
2. Inject a real bad-image Kubernetes rollout failure.
3. Detect the grouped root incident from the live cluster.
4. Generate an evidence-backed remediation plan.
5. Generate an approval request.
6. Record an approval decision.
7. Execute only the approved, allowlisted Kubernetes rollback action.
8. Verify the deployment recovered.
9. Generate and verify a tamper-evident audit trail.
10. Print an executive summary with artifact paths.

## Safety model

The script does not run arbitrary commands from a plan. It delegates to the approved executor from Milestone 25, which supports typed, allowlisted Kubernetes actions.

For this milestone the expected recovery action is:

```text
kubernetes_rollout_undo
```

The audit trail from Milestone 26 records the full chain of evidence, planning, approval, execution, and verification.

## Usage

```bash
./scripts/demo_run_real_safeops_loop.sh <namespace> <approver>
```

Defaults:

```text
namespace: demo
approver: current shell user
```

Example:

```bash
./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
```

## Optional environment overrides

```bash
SAFEOPS_DEMO_DEPLOYMENT=checkout-api \
SAFEOPS_DEMO_GOOD_IMAGE=safeops/checkout-api-demo:0.1.0 \
SAFEOPS_DEMO_BAD_IMAGE=safeops/checkout-api-demo:bad-tag-does-not-exist \
./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
```

## Main artifacts

The demo writes artifacts under `/tmp/safeops-demo` by default:

```text
real-k8s-incidents.md
real-k8s-remediation-plan.md
real-k8s-approval-request.md
real-k8s-approval-decision.md
real-k8s-execution-record.md
real-k8s-audit-trail.md
```

## Expected success signal

The final summary should end with:

```text
Result: PASSED
```

A healthy run proves:

```text
real Kubernetes incident
→ evidence pack
→ remediation plan
→ approval decision
→ policy check
→ allowlisted execution
→ verification
→ tamper-evident audit trail
```
