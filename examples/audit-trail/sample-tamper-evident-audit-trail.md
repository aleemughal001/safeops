# Sample SafeOps Tamper-Evident Audit Trail

This example shows the expected shape of a SafeOps audit chain after an approved real Kubernetes rollback.

```text
SafeOps tamper-evident audit trail generated.
Events chained: 5
Verification valid: True
Chain head: <sha256>
JSON audit trail: /tmp/safeops-demo/real-k8s-audit-trail.json
Markdown audit trail: /tmp/safeops-demo/real-k8s-audit-trail.md
```

Expected chain:

1. `evidence_collected`
2. `remediation_plan_generated`
3. `approval_requested`
4. `approval_decision_recorded`
5. `approved_execution_completed`

Expected verification:

```text
SafeOps audit trail verification complete.
Verification valid: True
Events checked: 5
Artifact recheck: enabled
```

Expected tamper test:

```text
SafeOps tamper simulation complete.
Verification valid after tamper: False
Expected tamper detection: event_hash mismatch at event 1
```
