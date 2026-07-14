"""SafeOps action policy enforcement.

The policy layer is deliberately simple in the prototype but important: the
backend must never treat documentation-only allowlists as security. Every
approved action is checked here before being sent to an executor.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "examples" / "policies" / "safe-actions.yaml"
POLICY_PATH = Path(os.getenv("SAFEOPS_POLICY_PATH", str(DEFAULT_POLICY_PATH)))


class PolicyError(RuntimeError):
    pass


def load_policy() -> Dict[str, Any]:
    if not POLICY_PATH.exists():
        raise PolicyError(f"Policy file not found: {POLICY_PATH}")
    with POLICY_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _allowed_actions(policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(policy.get("allowed_actions", []))


def _blocked_actions(policy: Dict[str, Any]) -> List[str]:
    return list(policy.get("blocked_actions", []))


def find_allowed_action(action_id: str) -> Optional[Dict[str, Any]]:
    policy = load_policy()
    if action_id in _blocked_actions(policy):
        return None
    for action in _allowed_actions(policy):
        if action.get("id") == action_id:
            return action
    return None


def check_action_policy(
    action_id: str,
    approved: bool,
    namespace: Optional[str] = None,
    service: Optional[str] = None,
) -> Dict[str, Any]:
    policy = load_policy()
    blocked = _blocked_actions(policy)

    if action_id in blocked:
        return {
            "allowed": False,
            "reason": "Action is explicitly blocked by policy.",
            "action_id": action_id,
        }

    action = find_allowed_action(action_id)
    if action is None:
        return {
            "allowed": False,
            "reason": "Action is not allowlisted.",
            "action_id": action_id,
        }

    approval_required = bool(action.get("approval_required", True))
    if approval_required and not approved:
        return {
            "allowed": False,
            "reason": "Human approval is required by policy.",
            "action_id": action_id,
            "approval_required": True,
        }

    namespace_rules = action.get("namespaces")
    if namespace_rules and namespace not in namespace_rules:
        return {
            "allowed": False,
            "reason": f"Namespace {namespace!r} is not permitted for this action.",
            "action_id": action_id,
        }

    service_rules = action.get("services")
    if service_rules and service not in service_rules:
        return {
            "allowed": False,
            "reason": f"Service {service!r} is not permitted for this action.",
            "action_id": action_id,
        }

    return {
        "allowed": True,
        "reason": "Action is allowlisted and approval requirements are satisfied.",
        "action_id": action_id,
        "resource": action.get("resource"),
        "approval_required": approval_required,
        "risk_level": action.get("risk_level", "unknown"),
    }
