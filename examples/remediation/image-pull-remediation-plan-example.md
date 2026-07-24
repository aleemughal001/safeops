# Example: Image Pull Failure Remediation Plan

A real bad image deployment may generate one root incident with multiple raw Kubernetes findings:

- DeploymentUnavailable
- ErrImagePull or ImagePullBackOff
- Pending pod state

SafeOps groups those signals into one root incident and generates an approval-ready plan.

## Recommended strategy

Rollback to the previous working image or restore a known-good image tag after approval. Verify the CI/CD image build and registry push completed successfully before retrying rollout.

## Safe action options

1. Inspect image build and registry publication.
2. Rollback the deployment to the previous revision after approval.
3. Set the deployment image back to a known-good tag after approval.

## Safety boundary

The plan is read-only and does not execute commands. All production-changing actions require policy validation and human approval.
