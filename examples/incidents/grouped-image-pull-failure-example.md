# Grouped Image Pull Failure Example

This example describes the target engineer experience for Milestone 21.

## Raw Kubernetes symptoms

A bad image tag may produce several Kubernetes signals:

```text
Deployment demo/checkout-api reason=DeploymentUnavailable
Pod demo/checkout-api-xxxx reason=ErrImagePull
Pod demo/checkout-api-xxxx reason=Pending
```

## Grouped SafeOps root incident

SafeOps groups those symptoms into one root incident:

```text
Title: Image pull failure / bad image or registry access
Affected workload: demo/checkout-api
Primary category: image_or_registry
Raw findings grouped: 3
```

## Evidence pack

The evidence pack should show:

- deployment unavailable or not progressing
- new pod unable to pull image
- image/tag involved
- high-signal Kubernetes events
- old pod may still be running during rollout
- rollout timeout

## Safe action options

SafeOps should recommend controlled next steps, not execute blindly:

1. Check image name/tag and registry access.
2. Verify CI/CD image build and push completed.
3. Roll back to previous revision after approval.
4. Restore last known-good image tag after approval.

## Verification

After remediation, SafeOps should verify:

- rollout status succeeds
- desired replicas equal available replicas
- related pods are Ready
- service endpoints are healthy
- alerts/error rate recover if telemetry is connected
