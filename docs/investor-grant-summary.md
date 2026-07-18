# SafeOps / AURA Investor and Grant Summary

## One-line summary

SafeOps is an open-source trust and safety layer for AI-assisted DevOps, focused on evidence-based incident analysis, human-approved remediation, verification, and auditability.

## Problem

Modern cloud-native teams already have monitoring, logs, dashboards, and alerts. The hard part is not only knowing that something is broken. The hard part is safely deciding what to do next, proving why that action is safe, getting approval, executing the fix, verifying recovery, and preserving an audit trail.

## Solution

SafeOps demonstrates a closed-loop safety workflow:

1. Detect a Kubernetes incident.
2. Collect evidence from Kubernetes.
3. Explain the likely root cause.
4. Recommend a scoped remediation.
5. Require human approval.
6. Enforce policy allowlists.
7. Execute only approved safe actions.
8. Verify recovery.
9. Record a tamper-evident audit log.
10. Save incident memory for future comparison.

## Why now

AI can help DevOps teams move faster, but unrestricted autonomous infrastructure changes are risky. Enterprises need a safety layer that puts evidence, approval, policy, verification, and auditability around AI-assisted operations.

## Current demo capability

The current demo runs locally against a real Kubernetes kind cluster. It breaks a sample `checkout-api` deployment by removing `REDIS_URL`, detects the incident, recommends restoring the config, asks for human approval, executes a real Kubernetes fix, verifies recovery, and prints a clean incident report.

## Open-source vs commercial direction

SafeOps can remain the open-source trust foundation: collector, policy model, demo workflows, audit schema, and safety patterns.

AURA can become the commercial managed platform: dashboard, advanced connectors, Slack/Teams approval, enterprise RBAC, SSO, persistent incident memory, multi-cluster support, compliance exports, and organization-specific reliability intelligence.

## Differentiation

SafeOps is not a traditional observability platform. It is an AI-assisted operational safety layer. It can sit above existing tools such as Datadog, Prometheus, Grafana, PagerDuty, GitHub Actions, Jenkins, and Kubernetes.

## Near-term roadmap

- v1.0 demo release package
- CLI approval and report polish
- Dashboard prototype
- Slack approval simulation
- Persistent database storage
- GitHub Actions CI
- Helm-based collector installation
- Signed audit export
- Multi-cluster support
