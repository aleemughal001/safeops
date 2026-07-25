# SafeOps Investor Q&A

## Is this just another observability tool?

No. SafeOps sits after observability. Observability tells you something is wrong. SafeOps turns evidence into an approval-gated, policy-bounded recovery workflow.

## Does SafeOps run arbitrary AI commands?

No. The demo intentionally avoids arbitrary shell execution. The executor only runs typed, allowlisted actions.

## What does the current demo prove?

It proves a real Kubernetes recovery loop: real failure, detection, evidence, remediation plan, approval, allowlisted execution, verification, audit trail, and investor evidence bundle.

## What is not production-ready yet?

The demo is not yet a multi-tenant SaaS product. Production work still needs persistent storage, authentication, RBAC, real Slack or Teams approvals, richer integrations, deployment packaging, and customer onboarding.

## Why is the audit trail important?

Because production remediation needs trust. SafeOps records who approved, what was planned, what executed, what verified, and whether the audit chain was modified.

## What is the commercial path?

Start with Kubernetes and CI/CD incident recovery for small platform teams. Expand into enterprise controls, policy governance, team approvals, audit exports, and cross-tool incident memory.
