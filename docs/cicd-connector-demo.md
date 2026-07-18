# SafeOps Milestone 12: GitHub/GitLab CI/CD Connector Demo

Milestone 12 adds a CI/CD context step to the SafeOps demo. The goal is to show that SafeOps does not only look at Kubernetes runtime symptoms. It can also correlate those symptoms with deployment evidence from a CI/CD system.

In this demo, the connector is simulated locally. It compares the known-good Kubernetes manifest with the broken deployment manifest and produces a CI/CD context record that explains whether a deployment likely removed a required environment variable.

## What this milestone proves

SafeOps can now show a stronger story:

```text
Kubernetes symptom: checkout-api is unhealthy / CrashLoopBackOff
Deployment evidence: the latest deployed manifest is missing REDIS_URL
Likely root cause: the deployment removed or failed to include REDIS_URL
Safe action: restore REDIS_URL after human approval
Verification: rollout and pod readiness are healthy
Prevention: generate a PR draft that fails CI/CD if REDIS_URL is missing
```

This moves SafeOps closer to a real AI DevOps Engineer because it connects runtime evidence with delivery evidence.

## Files added

```text
scripts/demo_cicd_context.sh
scripts/demo_run_full_with_cicd.sh
docs/cicd-connector-demo.md
examples/cicd/sample-github-actions-deployment-context.json
```

## Run the CI/CD-aware demo

From the repository root:

```bash
./scripts/demo_stop_services.sh
./scripts/demo_run_full_with_cicd.sh
```

Approve the remediation when prompted:

```text
yes
```

Approve the simulated prevention PR package when prompted:

```text
yes
```

## Generated output

The CI/CD connector writes:

```text
/tmp/safeops-demo/latest_cicd_context.txt
/tmp/safeops-demo/latest_cicd_context.json
/tmp/safeops-demo/latest_cicd_manifest_diff.txt
```

The report should say that `REDIS_URL` exists in the known-good manifest but is missing from the deployed/broken manifest.

## Why this matters

Without CI/CD context, SafeOps can say:

```text
checkout-api is failing because REDIS_URL is missing.
```

With CI/CD context, SafeOps can say:

```text
checkout-api is failing because REDIS_URL is missing, and the latest deployment is likely where REDIS_URL disappeared.
```

That is much closer to how a DevOps engineer investigates incidents.

## Real connector roadmap

This milestone is a local simulation. The production version should add real connectors for:

- GitHub Actions workflow runs
- GitLab CI pipelines
- Jenkins builds
- Bitbucket Pipelines
- deployment events
- commit diffs
- changed Kubernetes manifests
- PR authors and approvers
- failed/successful pipeline stages

The real connector should provide evidence to the incident engine, not just print local context.

## Safety notes

The CI/CD connector is read-only in this milestone. It does not change GitHub, GitLab, Jenkins, or Kubernetes state. Remediation still goes through the SafeOps approval, policy, scoped executor, verification, audit, and memory loop.
