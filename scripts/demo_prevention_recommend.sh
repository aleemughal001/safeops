#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

INCIDENT_FILE="/tmp/safeops-demo/latest_incident_id"
REMEDIATION_FILE="/tmp/safeops-demo/latest_remediation_output.json"

if [ ! -f "$REMEDIATION_FILE" ]; then
  echo "ERROR: Missing $REMEDIATION_FILE"
  echo "Run ./scripts/demo_run_full.sh first, or run remediation before requesting prevention."
  exit 1
fi

python3 - <<'PY'
from __future__ import annotations
import json
from pathlib import Path

TMP = Path('/tmp/safeops-demo')
remediation = json.loads((TMP / 'latest_remediation_output.json').read_text(errors='replace'))
incident_id = remediation.get('incident_id', 'unknown')
service = remediation.get('execution', {}).get('service') or remediation.get('memory', {}).get('service') or 'checkout-api'
namespace = remediation.get('execution', {}).get('namespace') or remediation.get('memory', {}).get('namespace') or 'demo'
root_cause = remediation.get('memory', {}).get('root_cause') or 'Required runtime configuration was missing.'
confidence = remediation.get('memory', {}).get('confidence')
params = remediation.get('policy_decision', {}).get('validated_parameters', {}) or remediation.get('execution', {}).get('parameters', {})
env_name = params.get('env_name', 'REDIS_URL')
env_value = params.get('env_value', 'redis://redis.demo.svc.cluster.local:6379')

print()
print('SafeOps Prevention Recommendation')
print('=================================')
print(f'Incident ID:        {incident_id}')
print(f'Service:            {service}')
print(f'Namespace:          {namespace}')
print(f'Root cause:         {root_cause}')
if confidence is not None:
    try:
        print(f'Confidence:         {float(confidence) * 100:.0f}%')
    except Exception:
        print(f'Confidence:         {confidence}')
print()
print('Why prevention is needed')
print('------------------------')
print(f'This service recovered after SafeOps restored {env_name}.')
print(f'Without a CI/CD guardrail, a future deployment can remove {env_name} again and repeat the same outage.')
print()
print('Suggested guardrails')
print('--------------------')
print(f'1. Add a required-env check for deployment/{service}.')
print(f'2. Fail CI/CD if {env_name} is missing from Kubernetes manifests.')
print('3. Add the incident fingerprint to SafeOps memory for faster future detection.')
print('4. Later: open this as a real GitHub/GitLab PR after approval.')
print()
print('Proposed prevention change')
print('--------------------------')
print(f'Required env:       {env_name}')
print(f'Expected value:     {env_value}')
print('PR mode:            simulated local PR draft')
PY

echo
read -r -p "Generate simulated prevention PR package? Type 'yes' to continue: " APPROVAL

if [ "$APPROVAL" != "yes" ]; then
  echo "Prevention PR draft skipped."
  exit 0
fi

echo
./scripts/demo_generate_prevention_pr.sh
