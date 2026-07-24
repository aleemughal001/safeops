# SafeOps Real-World Kubernetes Incident Detector

Milestone 20 starts moving SafeOps from a controlled demo toward a real engineer-ready prototype.

The detector is read-only. It connects to the current Kubernetes context through `kubectl`, scans live cluster state, classifies abnormal resources, collects sanitized evidence, and writes JSON + Markdown reports.

## What it detects first

The first real detector focuses on Kubernetes and release-related failure signals:

- `CrashLoopBackOff`
- `ImagePullBackOff`
- `ErrImagePull`
- `InvalidImageName`
- `CreateContainerConfigError`
- `CreateContainerError`
- `OOMKilled`
- `Pending` pods
- readiness probe failures from Kubernetes events
- deployments with unavailable replicas or failed progress conditions
- services with selectors but zero ready endpoints

These are not dummy incidents. They are live Kubernetes states gathered from a real cluster.

## Run it

```bash
./scripts/demo_detect_real_k8s_incidents.sh
```

Scan one namespace:

```bash
./scripts/demo_detect_real_k8s_incidents.sh demo
```

Output files:

```text
/tmp/safeops-demo/real-k8s-incidents.json
/tmp/safeops-demo/real-k8s-incidents.md
```

## Safety model

The detector does not execute any action.

It only recommends safe next steps. Execution must still go through SafeOps policy, approval, scoped executor, verification, and audit.

## Evidence collected

For each incident, SafeOps records:

- resource kind, namespace, and name
- reason and category
- root-cause hypothesis
- recommended safe action
- approval requirement
- pod/deployment/service evidence
- high-signal Kubernetes events
- sanitized logs tail when available
- verification plan
- prevention ideas

## Why this matters

The old demo proved the SafeOps workflow. This detector starts proving real-world usefulness:

1. SafeOps can inspect an actual Kubernetes cluster.
2. SafeOps can detect failures without being told the exact scenario.
3. SafeOps can classify the incident type.
4. SafeOps can attach real evidence.
5. SafeOps can recommend controlled remediation without blindly executing commands.

## Next milestones

After this detector works, the next upgrades should be:

1. Connect detector output into the backend incident engine.
2. Add a real GitHub Actions connector for recent failed workflows and deployment commits.
3. Add a scenario library with multiple reproducible Kubernetes failures.
4. Add real Slack approval.
5. Add real GitHub prevention PR creation.
