# SafeOps Final Investor Demo Script

## 30-second opening

SafeOps is an open-source safety layer for AI-assisted DevOps remediation. It does not blindly run AI-generated shell commands. It detects real Kubernetes incidents, gathers evidence, creates an approval-ready remediation plan, records human approval, executes only allowlisted actions, verifies recovery, and creates a tamper-evident audit trail.

## 2-minute pitch

Engineering teams already have observability tools, CI/CD tools, and Kubernetes dashboards, but when production breaks, humans still have to connect evidence across systems, decide what is safe, get approval, execute recovery, verify the result, and preserve an audit trail.

SafeOps turns that incident workflow into a controlled AI-assisted loop.

In the demo, SafeOps intentionally breaks a Kubernetes deployment with a bad image. It detects the image pull failure, groups the noisy Kubernetes symptoms into one root incident, creates evidence, recommends a safe rollback, records approval from an operator, executes only the allowlisted rollback action, verifies the workload is healthy again, and produces a tamper-evident audit trail.

The key difference is safety. SafeOps is not an autonomous bot with unrestricted cluster access. It is approval-gated, policy-bounded, evidence-driven, and auditable.

## 5-minute technical demo flow

Run:

```bash
./scripts/demo_create_investor_bundle.sh demo aleemughal001
```

Explain each step:

1. SafeOps resets the demo workload to a known-good image.
2. It injects a real bad-image rollout failure.
3. It detects and groups the Kubernetes incident.
4. It generates a remediation plan.
5. It creates an approval request.
6. It records approval.
7. It executes an allowlisted rollback action.
8. It verifies the deployment recovered.
9. It generates a tamper-evident audit trail.
10. It packages the evidence into an investor/customer bundle.

Expected result:

```text
Demo result: PASSED
Audit verification valid: True
Executed allowlisted actions: 1
```

## Closing line

This prototype proves the core SafeOps loop: real incident detection, evidence-based planning, human approval, restricted execution, verification, and auditability.
