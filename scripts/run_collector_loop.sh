#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../agent/collector"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
SAFEOPS_POLL_SECONDS="${SAFEOPS_POLL_SECONDS:-30}" SAFEOPS_NAMESPACE="${SAFEOPS_NAMESPACE:-demo}" SAFEOPS_BACKEND_URL="${SAFEOPS_BACKEND_URL:-http://localhost:8000}" python3 collector.py
