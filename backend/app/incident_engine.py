from typing import Dict, Any, List


SAFE_REDIS_URL = "redis://redis.demo.svc.cluster.local:6379"


def _contains(texts: List[str], keyword: str) -> bool:
    joined = " ".join(texts).lower()
    return keyword.lower() in joined


def analyze_incident(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Simple MVP rule-based incident explanation.

    Later this will call an AI agent with sanitized evidence, RAG, incident memory,
    and policy context. For the prototype, deterministic rules keep the demo safe.
    """
    symptoms = payload.get("symptoms", [])
    evidence_summaries = [e.get("summary", "") for e in payload.get("evidence", [])]
    all_text = symptoms + evidence_summaries

    service = payload.get("service", "unknown-service")
    namespace = payload.get("namespace", "default")

    has_crashloop_signal = any(
        _contains(all_text, phrase)
        for phrase in [
            "crashloopbackoff",
            "back-off restarting failed container",
            "last_terminated_reason=error",
            "restart_count=",
        ]
    )
    has_redis_signal = any(
        _contains(all_text, phrase)
        for phrase in [
            "redis_url",
            "missing required environment variable redis_url",
            "missing expected environment variable redis_url",
            "env_names=[]",
            "environment:\t<none>",
        ]
    )

    suggested_parameters: Dict[str, Any] = {}

    if has_crashloop_signal and has_redis_signal:
        root_cause = f"The latest deployment likely removed or misconfigured REDIS_URL for {service}."
        confidence = 0.89
        recommendation = (
            "Restore the missing REDIS_URL environment variable on the deployment, "
            "then verify the rollout and pod readiness."
        )
        action_id = "set_env_deployment"
        risk_level = "low"
        blast_radius = f"{service} in namespace {namespace} only"
        suggested_parameters = {
            "env_name": "REDIS_URL",
            "env_value": SAFE_REDIS_URL,
        }
    elif has_crashloop_signal:
        root_cause = f"{service} is repeatedly crashing after deployment. SafeOps found restart/backoff evidence, but needs stronger config/log/CI-CD context for exact root cause."
        confidence = 0.62
        recommendation = "Rollback the deployment or collect more evidence before remediation."
        action_id = "rollout_undo_deployment"
        risk_level = "medium"
        blast_radius = f"{service} in namespace {namespace} only"
    elif _contains(all_text, "imagepullbackoff") or _contains(all_text, "errimagepull"):
        root_cause = f"{service} cannot pull its container image. Check image name, tag, registry auth, or image availability."
        confidence = 0.78
        recommendation = "Verify image tag and registry access before redeploying."
        action_id = "create_issue"
        risk_level = "none"
        blast_radius = f"{service} deployment only"
    else:
        root_cause = "SafeOps found a Kubernetes incident but does not have enough evidence for a high-confidence root cause yet."
        confidence = 0.45
        recommendation = "Collect more logs, events, deployment history, and CI/CD context."
        action_id = "collect_more_evidence"
        risk_level = "unknown"
        blast_radius = "unknown"

    recommended_action: Dict[str, Any] = {
        "action_id": action_id,
        "description": recommendation,
        "approval_required": True,
        "risk_level": risk_level,
        "blast_radius": blast_radius,
    }
    if suggested_parameters:
        recommended_action["parameters"] = suggested_parameters

    return {
        "incident_id": payload.get("incident_id"),
        "service": service,
        "namespace": namespace,
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence": payload.get("evidence", []),
        "recommended_action": recommended_action,
        "verification_plan": [
            "Check rollout status",
            "Check pod readiness",
            "Confirm REDIS_URL is present on the deployment",
            "Check service health endpoint",
            "Check error rate recovery",
        ],
    }
