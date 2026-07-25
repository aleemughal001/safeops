# SafeOps First Feedback Call Guide

## Goal of the call

The goal is not to sell immediately. The goal is to learn whether the SafeOps workflow matches a real pain point and what would be required for trust in production.

## 15-minute call structure

### 1. Intro: 2 minutes

Say:

> I’m building SafeOps, a safety layer for AI-assisted DevOps remediation. The demo shows a real Kubernetes incident being detected, planned, approved, safely remediated, verified, and audited.

### 2. Show demo/release: 5 minutes

Show:

- GitHub release page
- Short demo video or terminal output
- Evidence bundle
- Audit trail

### 3. Ask feedback questions: 6 minutes

Ask:

1. Would this have helped in your last incident?
2. Which part feels most useful: detection, planning, approval, execution, verification, or audit?
3. Which part feels risky?
4. Would your team trust allowlisted execution after approval?
5. What system would need to integrate first: Slack, GitHub Actions, Jenkins, Datadog, Kubernetes, PagerDuty, or something else?
6. Who would own this inside your organization?
7. Would this be more useful as open source, hosted SaaS, or enterprise deployment?
8. What would make this worth paying for?

### 4. Close: 2 minutes

Ask:

> Who else should I talk to?

> Would you be open to reviewing the next version or becoming a design partner?

## What to listen for

Strong validation signs:

- They describe a recent incident where this would have helped.
- They ask for a specific integration.
- They ask about security, RBAC, audit, or approval workflow.
- They ask to try it in their own environment.
- They introduce you to another DevOps/SRE person.

Weak validation signs:

- They only say “cool idea.”
- They do not describe a real incident.
- They cannot identify who would use it.
- They see it as a toy demo only.

## Notes template

```text
Name:
Role:
Company/team type:
Current incident tools:
Pain level 1-10:
Most useful feature:
Biggest concern:
Needed integration:
Would they try it:
Would they pay:
Introductions offered:
Next step:
```
