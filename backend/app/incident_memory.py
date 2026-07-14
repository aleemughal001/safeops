"""Tiny persistent incident memory for the SafeOps prototype.

This is intentionally basic. It stores closed incidents in JSONL and provides a
simple token-overlap similarity search. Later this becomes pgvector + service
knowledge graph + Adaptive Reliability Engine.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

DEFAULT_MEMORY_PATH = "/tmp/safeops/incident-memory.jsonl"
MEMORY_PATH = Path(os.getenv("SAFEOPS_MEMORY_PATH", DEFAULT_MEMORY_PATH))
TOKEN_RE = re.compile(r"[a-zA-Z0-9_:-]+")


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2}


def _incident_text(record: Dict[str, Any]) -> str:
    parts = [
        str(record.get("service", "")),
        str(record.get("namespace", "")),
        str(record.get("root_cause", "")),
        str(record.get("recommended_action", "")),
        str(record.get("outcome", "")),
    ]
    for evidence in record.get("evidence", []) or []:
        parts.append(str(evidence.get("summary", "")))
    return " ".join(parts)


def read_memory() -> List[Dict[str, Any]]:
    if not MEMORY_PATH.exists():
        return []
    records: List[Dict[str, Any]] = []
    with MEMORY_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_incident_memory(record: Dict[str, Any]) -> Dict[str, Any]:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    memory_record = {
        "memory_id": f"mem_{uuid4().hex[:12]}",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "safeops.memory.v1",
        **record,
    }
    with MEMORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(memory_record, sort_keys=True, default=str) + "\n")
    return memory_record


def find_similar_incidents(candidate: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    candidate_tokens = _tokens(_incident_text(candidate))
    if not candidate_tokens:
        return []

    scored: List[Dict[str, Any]] = []
    for record in read_memory():
        record_tokens = _tokens(_incident_text(record))
        if not record_tokens:
            continue
        overlap = candidate_tokens & record_tokens
        union = candidate_tokens | record_tokens
        score = len(overlap) / len(union) if union else 0.0
        if score > 0:
            scored.append(
                {
                    "memory_id": record.get("memory_id"),
                    "incident_id": record.get("incident_id"),
                    "service": record.get("service"),
                    "root_cause": record.get("root_cause"),
                    "outcome": record.get("outcome"),
                    "similarity": round(score, 3),
                }
            )

    return sorted(scored, key=lambda item: item["similarity"], reverse=True)[:limit]
