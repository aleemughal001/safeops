#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUT_DIR="/tmp/safeops-demo"
mkdir -p "$OUT_DIR"

INCIDENT_ID="${1:-}"
if [[ -z "$INCIDENT_ID" && -f "$OUT_DIR/latest_incident_id" ]]; then
  INCIDENT_ID="$(cat "$OUT_DIR/latest_incident_id")"
fi
if [[ -z "$INCIDENT_ID" ]]; then
  INCIDENT_ID="pending-detection"
fi

PROVIDER="${SAFEOPS_CICD_PROVIDER:-github-actions}"
SERVICE="${SAFEOPS_SERVICE:-checkout-api}"
NAMESPACE="${SAFEOPS_NAMESPACE:-demo}"
REQUIRED_ENV="${SAFEOPS_REQUIRED_ENV:-REDIS_URL}"
EXPECTED_VALUE="${SAFEOPS_REQUIRED_ENV_VALUE:-redis://redis.demo.svc.cluster.local:6379}"
WORKING_MANIFEST="demo/k8s/checkout-api-working.yaml"
BROKEN_MANIFEST="demo/k8s/checkout-api-broken.yaml"
DIFF_FILE="$OUT_DIR/latest_cicd_manifest_diff.txt"
JSON_FILE="$OUT_DIR/latest_cicd_context.json"
TXT_FILE="$OUT_DIR/latest_cicd_context.txt"

GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
GIT_REMOTE="$(git remote get-url origin 2>/dev/null || echo local-repo)"
COMMIT_SUBJECT="$(git log -1 --pretty=%s 2>/dev/null || echo unknown)"
NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# git diff --no-index returns 1 when files differ, which is expected here.
git diff --no-index "$WORKING_MANIFEST" "$BROKEN_MANIFEST" > "$DIFF_FILE" 2>/dev/null || true

WORKING_HAS_ENV="false"
BROKEN_HAS_ENV="false"
ENV_NAME_PATTERN="^[[:space:]]*-[[:space:]]*name:[[:space:]]*${REQUIRED_ENV}[[:space:]]*$"

if grep -Eq "$ENV_NAME_PATTERN" "$WORKING_MANIFEST" 2>/dev/null; then
  WORKING_HAS_ENV="true"
fi
if grep -Eq "$ENV_NAME_PATTERN" "$BROKEN_MANIFEST" 2>/dev/null; then
  BROKEN_HAS_ENV="true"
fi

if [[ "$WORKING_HAS_ENV" == "true" && "$BROKEN_HAS_ENV" == "false" ]]; then
  DETECTED_CHANGE="Required environment variable $REQUIRED_ENV exists in the known-good manifest but is missing from the deployed/broken manifest."
  LIKELY_CONTRIBUTION="The latest deployment likely removed or failed to include $REQUIRED_ENV, matching the Kubernetes CrashLoopBackOff evidence."
  RISK_LEVEL="high-correlation"
else
  DETECTED_CHANGE="No required-env removal detected by the demo CI/CD connector."
  LIKELY_CONTRIBUTION="CI/CD evidence is inconclusive for this incident."
  RISK_LEVEL="unknown"
fi

python3 - <<PY
import json
from pathlib import Path
payload = {
    "schema_version": "safeops.cicd_context.v1",
    "incident_id": "${INCIDENT_ID}",
    "provider": "${PROVIDER}",
    "repository": "${GIT_REMOTE}",
    "branch": "${GIT_BRANCH}",
    "commit_sha": "${GIT_SHA}",
    "commit_subject": "${COMMIT_SUBJECT}",
    "deployment_status": "simulated_success",
    "deployment_time_utc": "${NOW_UTC}",
    "service": "${SERVICE}",
    "namespace": "${NAMESPACE}",
    "changed_files": [
        "${WORKING_MANIFEST}",
        "${BROKEN_MANIFEST}"
    ],
    "required_env": "${REQUIRED_ENV}",
    "expected_value": "${EXPECTED_VALUE}",
    "working_manifest_has_required_env": json.loads("${WORKING_HAS_ENV}"),
    "deployed_manifest_has_required_env": json.loads("${BROKEN_HAS_ENV}"),
    "detected_change": "${DETECTED_CHANGE}",
    "likely_contribution": "${LIKELY_CONTRIBUTION}",
    "correlation_level": "${RISK_LEVEL}",
    "diff_ref": "${DIFF_FILE}",
    "next_prevention_step": "Open a prevention PR that adds a CI/CD required-env check for ${REQUIRED_ENV}."
}
Path("${JSON_FILE}").write_text(json.dumps(payload, indent=2) + "\n")
PY

cat > "$TXT_FILE" <<TXT
SafeOps CI/CD Connector Context
===============================
Incident ID:        $INCIDENT_ID
Provider:           $PROVIDER
Repository:         $GIT_REMOTE
Branch:             $GIT_BRANCH
Commit:             $GIT_SHA
Commit subject:     $COMMIT_SUBJECT
Service:            $SERVICE
Namespace:          $NAMESPACE
Deployment status:  simulated_success
Checked at:         $NOW_UTC

Detected deployment signal
--------------------------
$DETECTED_CHANGE

Correlation
-----------
$LIKELY_CONTRIBUTION

Files compared
--------------
Known-good:         $WORKING_MANIFEST
Deployed/broken:    $BROKEN_MANIFEST
Diff saved to:      $DIFF_FILE
JSON saved to:      $JSON_FILE

Prevention handoff
------------------
Suggested next step: create a prevention PR that fails CI/CD if $REQUIRED_ENV is missing.
TXT

cat "$TXT_FILE"
