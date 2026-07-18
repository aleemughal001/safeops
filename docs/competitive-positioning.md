# SafeOps Competitive Positioning

## Short positioning

SafeOps is not a Datadog clone. Datadog is an observability and monitoring platform. SafeOps is a trust-first AI remediation layer that focuses on evidence-based diagnosis, human approval, policy-gated execution, recovery verification, audit logging, and incident memory.

## Where Datadog is strong

Datadog is strong at collecting, visualizing, correlating, and alerting on telemetry across infrastructure, applications, logs, security, real user monitoring, cloud costs, CI visibility, Kubernetes, and more.

## Where SafeOps fits

SafeOps fits after an alert or failure has been detected. It asks:

- What evidence explains the failure?
- What is the safest recommended action?
- What is the blast radius?
- Has a human approved it?
- Does policy allow it?
- Did the fix actually recover the system?
- Is every step auditable?

## Simple comparison

| Area | Datadog | SafeOps |
|---|---|---|
| Main category | Observability platform | AI-assisted remediation safety layer |
| Primary value | Monitor, alert, correlate telemetry | Explain, approve, safely fix, verify, audit |
| Telemetry storage | Core product area | Minimal in demo; uses evidence collection |
| Human approval | Exists in incident workflows and automations | Core product principle before remediation |
| Policy allowlist | Not the central positioning | Core safety mechanism |
| Safe execution | Automations/workflows exist | Narrow, policy-gated executor with blast radius |
| Verification after fix | Can observe resulting metrics/events | Explicit remediation verification step |
| Audit trail | Platform audit/incident records | Tamper-evident remediation audit log |
| Ideal relationship | Source of alerts/telemetry | Layer on top of Datadog/Kubernetes/CI/CD |

## Better phrasing

Do not say:

```text
SafeOps is better than Datadog.
```

Say:

```text
SafeOps is different from Datadog. Datadog helps teams observe what is happening. SafeOps helps teams safely decide what to do next, get approval, execute the fix, verify recovery, and audit the whole process.
```

## Future integration idea

A future SafeOps connector could ingest Datadog alerts/events as evidence, then run the SafeOps safety workflow for approval, policy, remediation, verification, and audit.
