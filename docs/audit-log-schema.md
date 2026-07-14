# Audit Log Schema

The current prototype uses append-only JSONL with a hash chain.

Each event includes:

```json
{
  "event_id": "evt_xxx",
  "incident_id": "inc_checkout_001",
  "timestamp": "2026-07-07T00:00:00Z",
  "event_type": "recommendation.created",
  "actor": "safeops.incident_engine",
  "details": {},
  "prev_hash": "...",
  "schema_version": "safeops.audit.v1",
  "event_hash": "..."
}
```

## Event Types

- `recommendation.created`
- `approval.granted`
- `approval.rejected`
- `approval.rejected_by_system`
- `policy.checked`
- `execution.requested`
- `execution.blocked`
- `execution.completed`
- `execution.failed`
- `verification.completed`
- `verification.failed`
- `memory.saved`

## Verification

Call:

```bash
curl http://localhost:8000/audit-log/verify | python -m json.tool
```

Expected result:

```json
{
  "valid": true,
  "event_count": 7,
  "latest_hash": "...",
  "issues": []
}
```

This is tamper-evident, not tamper-proof. Production should use PostgreSQL append-only tables, object-lock storage, or WORM-compatible storage.
