#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../agent/executor"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SAFEOPS_EXECUTOR_MODE=kubernetes
export SAFEOPS_ALLOWED_K8S_NAMESPACES=${SAFEOPS_ALLOWED_K8S_NAMESPACES:-demo}
export SAFEOPS_ALLOWED_K8S_SERVICES=${SAFEOPS_ALLOWED_K8S_SERVICES:-checkout-api}
exec uvicorn executor:app --host 0.0.0.0 --port 8010 --reload
