"""Backend client for the customer-side SafeOps executor service."""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx

EXECUTOR_URL = os.getenv("SAFEOPS_EXECUTOR_URL", "http://localhost:8010")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("SAFEOPS_EXECUTOR_TIMEOUT_SECONDS", "10"))


class ExecutorUnavailable(RuntimeError):
    pass


def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{EXECUTOR_URL.rstrip('/')}{path}"
    try:
        response = httpx.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise ExecutorUnavailable(f"Executor request failed: {exc}") from exc


def execute_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post("/execute", payload)


def verify_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _post("/verify", payload)
