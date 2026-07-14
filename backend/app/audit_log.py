"""Tamper-evident audit log for the SafeOps prototype.

The MVP uses an append-only JSONL file with a hash chain. This is not a
replacement for PostgreSQL/WORM storage, but it proves the trust-layer design:
every recommendation, approval, policy decision, execution, verification, and
memory write is recorded and can be checked for tampering.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

DEFAULT_AUDIT_LOG_PATH = "/tmp/safeops/audit-log.jsonl"
AUDIT_LOG_PATH = Path(os.getenv("SAFEOPS_AUDIT_LOG_PATH", DEFAULT_AUDIT_LOG_PATH))
GENESIS_HASH = "0" * 64


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _hash_event(event_without_hash: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(event_without_hash).encode("utf-8")).hexdigest()


def _read_events_from_file() -> List[Dict[str, Any]]:
    if not AUDIT_LOG_PATH.exists():
        return []

    events: List[Dict[str, Any]] = []
    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                events.append(
                    {
                        "event_id": f"corrupt_line_{line_number}",
                        "event_type": "audit.corrupt_line",
                        "error": str(exc),
                        "raw_line": line,
                    }
                )
    return events


def read_audit_events(limit: int | None = None) -> List[Dict[str, Any]]:
    events = _read_events_from_file()
    if limit is not None:
        return events[-limit:]
    return events


def _last_hash() -> str:
    events = _read_events_from_file()
    if not events:
        return GENESIS_HASH
    return str(events[-1].get("event_hash", GENESIS_HASH))


def write_audit_event(
    event_type: str,
    incident_id: str,
    actor: str,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    event_without_hash = {
        "event_id": f"evt_{uuid4().hex[:12]}",
        "incident_id": incident_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "actor": actor,
        "details": details,
        "prev_hash": _last_hash(),
        "schema_version": "safeops.audit.v1",
    }
    event = dict(event_without_hash)
    event["event_hash"] = _hash_event(event_without_hash)

    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    return event


def verify_audit_chain() -> Dict[str, Any]:
    events = _read_events_from_file()
    issues: List[Dict[str, Any]] = []
    expected_prev_hash = GENESIS_HASH

    for index, event in enumerate(events):
        event_hash = event.get("event_hash")
        prev_hash = event.get("prev_hash")

        if prev_hash != expected_prev_hash:
            issues.append(
                {
                    "index": index,
                    "event_id": event.get("event_id"),
                    "issue": "prev_hash_mismatch",
                    "expected_prev_hash": expected_prev_hash,
                    "actual_prev_hash": prev_hash,
                }
            )

        if "event_hash" not in event:
            issues.append(
                {
                    "index": index,
                    "event_id": event.get("event_id"),
                    "issue": "missing_event_hash",
                }
            )
            expected_prev_hash = GENESIS_HASH
            continue

        event_without_hash = {k: v for k, v in event.items() if k != "event_hash"}
        recomputed_hash = _hash_event(event_without_hash)
        if recomputed_hash != event_hash:
            issues.append(
                {
                    "index": index,
                    "event_id": event.get("event_id"),
                    "issue": "event_hash_mismatch",
                    "expected_event_hash": recomputed_hash,
                    "actual_event_hash": event_hash,
                }
            )

        expected_prev_hash = str(event_hash)

    return {
        "valid": len(issues) == 0,
        "event_count": len(events),
        "latest_hash": expected_prev_hash if events else GENESIS_HASH,
        "audit_log_path": str(AUDIT_LOG_PATH),
        "issues": issues,
    }
