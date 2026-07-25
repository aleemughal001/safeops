# SafeOps Investor Demo Evidence Bundle

Milestone 28 adds a clean evidence packaging workflow for the real SafeOps Kubernetes demo.

The bundle is designed for investor, customer, and internal review conversations. It packages the important artifacts from the real recovery flow into one timestamped folder and zip file.

## Command

```bash
./scripts/demo_create_investor_bundle.sh demo aleemughal001
```

## What it does

The script runs a full real SafeOps loop and then packages the evidence:

1. Resets the demo deployment to a known-good image.
2. Injects a real bad-image Kubernetes rollout failure.
3. Runs detection, grouping, remediation planning, approval, allowlisted execution, and verification.
4. Generates and verifies the tamper-evident audit trail.
5. Captures final Kubernetes cluster state.
6. Creates an investor/customer evidence bundle.

## Bundle contents

A generated bundle contains:

- `README.md` — explains what each artifact proves.
- `EXECUTIVE_SUMMARY.md` — investor-friendly outcome summary.
- `manifest.json` — machine-readable file list and SHA-256 hashes.
- `01-incident-evidence.md/json` — root incident evidence.
- `02-remediation-plan.md/json` — approval-ready plan.
- `03-approval-request.md/json` — human approval request.
- `04-approval-decision.md/json` — recorded decision and approver.
- `05-execution-record.md/json` — allowlisted action and verification result.
- `06-tamper-evident-audit-trail.md/json` — hash-chained audit trail.
- `07-final-cluster-state.txt` — final Kubernetes rollout and pod state.

## Expected result

```text
SafeOps investor demo evidence bundle created.
Demo result: PASSED
Audit verification valid: True
Executed allowlisted actions: 1
```

## Why this matters

Before this milestone, the demo generated useful artifacts in `/tmp/safeops-demo`, but they were spread across separate files. This milestone turns those artifacts into a clean review package that can support a pitch, customer technical review, or internal architecture discussion.

## Safety boundary

The packaging script does not run arbitrary commands. The real execution still goes through the existing SafeOps approval and allowlist path. The packager only copies, hashes, summarizes, and zips the generated artifacts.
