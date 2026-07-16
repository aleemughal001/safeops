from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .audit_log import read_audit_events, verify_audit_chain, write_audit_event
from .executor_client import ExecutorUnavailable, execute_action, verify_action
from .incident_engine import analyze_incident
from .incident_memory import find_similar_incidents, read_memory, save_incident_memory
from .policy import PolicyError, check_action_policy

app = FastAPI(title="SafeOps Backend", version="0.2.0")

# Prototype state. In production this becomes PostgreSQL.
incident_results: Dict[str, Dict[str, Any]] = {}
execution_results: Dict[str, Dict[str, Any]] = {}
verification_results: Dict[str, Dict[str, Any]] = {}


class Evidence(BaseModel):
    source: str
    summary: str
    raw_ref: Optional[str] = None


class IncidentInput(BaseModel):
    incident_id: str = Field(..., examples=["inc_checkout_001"])
    service: str = Field(..., examples=["checkout-api"])
    namespace: str = Field(..., examples=["demo"])
    symptoms: List[str]
    evidence: List[Evidence]


class ApprovalInput(BaseModel):
    incident_id: str
    action_id: str
    approved_by: str
    approved: bool
    dry_run: bool = Field(
        default=True,
        description="Keep true for prototype safety. Real K8s execution must be enabled explicitly.",
    )
    parameters: Dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/incidents/analyze")
def analyze(payload: IncidentInput) -> Dict[str, Any]:
    raw_payload = payload.model_dump()
    result = analyze_incident(raw_payload)
    similar = find_similar_incidents(
        {
            "incident_id": payload.incident_id,
            "service": payload.service,
            "namespace": payload.namespace,
            "root_cause": result.get("root_cause"),
            "recommended_action": result.get("recommended_action", {}).get("action_id"),
            "evidence": raw_payload.get("evidence", []),
        }
    )
    result["similar_incidents"] = similar
    incident_results[payload.incident_id] = result

    write_audit_event(
        event_type="recommendation.created",
        incident_id=payload.incident_id,
        actor="safeops.incident_engine",
        details=result,
    )
    return result


@app.post("/approvals")
def approve(payload: ApprovalInput) -> Dict[str, Any]:
    incident = incident_results.get(payload.incident_id)
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident has not been analyzed yet. Call /incidents/analyze first.",
        )

    recommended_action = incident.get("recommended_action", {})
    if payload.action_id != recommended_action.get("action_id"):
        write_audit_event(
            event_type="approval.rejected_by_system",
            incident_id=payload.incident_id,
            actor="safeops.policy_engine",
            details={
                "reason": "Requested action does not match current recommendation.",
                "requested_action_id": payload.action_id,
                "recommended_action_id": recommended_action.get("action_id"),
            },
        )
        raise HTTPException(
            status_code=400,
            detail="Requested action_id does not match the current recommended action.",
        )

    approval_event_type = "approval.granted" if payload.approved else "approval.rejected"
    approval_event = write_audit_event(
        event_type=approval_event_type,
        incident_id=payload.incident_id,
        actor=payload.approved_by,
        details=payload.model_dump(),
    )

    if not payload.approved:
        return {
            "status": "approval_rejected",
            "message": "Human rejected the action. Nothing executed.",
            "audit_event": approval_event,
        }

    try:
        policy_decision = check_action_policy(
            action_id=payload.action_id,
            approved=payload.approved,
            namespace=incident.get("namespace"),
            service=incident.get("service"),
            parameters=payload.parameters,
        )
    except PolicyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    write_audit_event(
        event_type="policy.checked",
        incident_id=payload.incident_id,
        actor="safeops.policy_engine",
        details=policy_decision,
    )

    if not policy_decision["allowed"]:
        write_audit_event(
            event_type="execution.blocked",
            incident_id=payload.incident_id,
            actor="safeops.policy_engine",
            details=policy_decision,
        )
        raise HTTPException(status_code=403, detail=policy_decision)

    executor_payload = {
        "incident_id": payload.incident_id,
        "action_id": payload.action_id,
        "approved": payload.approved,
        "approved_by": payload.approved_by,
        "service": incident.get("service"),
        "namespace": incident.get("namespace"),
        "dry_run": payload.dry_run,
        "parameters": payload.parameters,
    }

    write_audit_event(
        event_type="execution.requested",
        incident_id=payload.incident_id,
        actor="safeops.backend",
        details=executor_payload,
    )

    try:
        execution_result = execute_action(executor_payload)
    except ExecutorUnavailable as exc:
        write_audit_event(
            event_type="execution.failed",
            incident_id=payload.incident_id,
            actor="safeops.executor_client",
            details={"error": str(exc), "payload": executor_payload},
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    execution_results[payload.incident_id] = execution_result
    write_audit_event(
        event_type="execution.completed",
        incident_id=payload.incident_id,
        actor="safeops.executor",
        details=execution_result,
    )

    verify_payload = {
        "incident_id": payload.incident_id,
        "action_id": payload.action_id,
        "execution_id": execution_result.get("execution_id"),
        "service": incident.get("service"),
        "namespace": incident.get("namespace"),
        "parameters": payload.parameters,
    }

    try:
        verification_result = verify_action(verify_payload)
    except ExecutorUnavailable as exc:
        write_audit_event(
            event_type="verification.failed",
            incident_id=payload.incident_id,
            actor="safeops.executor_client",
            details={"error": str(exc), "payload": verify_payload},
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    verification_results[payload.incident_id] = verification_result
    write_audit_event(
        event_type="verification.completed",
        incident_id=payload.incident_id,
        actor="safeops.executor",
        details=verification_result,
    )

    memory_record = save_incident_memory(
        {
            "incident_id": payload.incident_id,
            "service": incident.get("service"),
            "namespace": incident.get("namespace"),
            "root_cause": incident.get("root_cause"),
            "confidence": incident.get("confidence"),
            "recommended_action": payload.action_id,
            "evidence": incident.get("evidence", []),
            "execution": execution_result,
            "verification": verification_result,
            "outcome": verification_result.get("status"),
            "approved_by": payload.approved_by,
        }
    )
    write_audit_event(
        event_type="memory.saved",
        incident_id=payload.incident_id,
        actor="safeops.incident_memory",
        details=memory_record,
    )

    return {
        "status": "closed_loop_completed",
        "incident_id": payload.incident_id,
        "approval": approval_event,
        "policy_decision": policy_decision,
        "execution": execution_result,
        "verification": verification_result,
        "memory": memory_record,
    }


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> Dict[str, Any]:
    incident = incident_results.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found in prototype state.")
    return {
        "analysis": incident,
        "execution": execution_results.get(incident_id),
        "verification": verification_results.get(incident_id),
    }


@app.get("/memory")
def get_memory() -> List[Dict[str, Any]]:
    return read_memory()


@app.get("/audit-log")
def get_audit_log(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    return read_audit_events(limit=limit)


@app.get("/audit-log/verify")
def verify_audit_log() -> Dict[str, Any]:
    return verify_audit_chain()
