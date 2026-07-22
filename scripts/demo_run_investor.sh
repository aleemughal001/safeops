#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUT_DIR="/tmp/safeops-demo"
PACKAGE_DIR="$OUT_DIR/investor-demo-package"
RUN_LOG="/tmp/safeops-investor-demo-run.log"

mkdir -p "$OUT_DIR"
rm -f "$RUN_LOG"

cat <<'BANNER'
=== SafeOps Investor Demo Package ===
This one-command demo will run the full SafeOps flow:
  detect -> CI/CD correlation -> Slack approval simulation -> remediation -> verification -> audit -> prevention -> cockpit

Auto-inputs used by this investor demo:
  Slack approval: approve
  Prevention PR: yes
BANNER

echo
# Run the full cockpit demo non-interactively while still showing the output.
# The full demo asks for Slack approval and prevention PR generation.
if ! printf 'approve\nyes\n' | DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-0}" "$SCRIPT_DIR/demo_run_full_with_cockpit.sh" | tee "$RUN_LOG"; then
  echo
  echo "Investor demo failed. Review log: $RUN_LOG" >&2
  exit 1
fi

echo
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/artifacts" "$PACKAGE_DIR/logs"
cp "$RUN_LOG" "$PACKAGE_DIR/logs/full-demo-output.log"

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [[ -f "$src" ]]; then
    cp "$src" "$dst"
    echo "copied: $src -> $dst"
  else
    echo "missing optional artifact: $src"
  fi
}

copy_if_exists "$OUT_DIR/incident-cockpit.html" "$PACKAGE_DIR/incident-cockpit.html"
copy_if_exists "$OUT_DIR/latest_remediation_output.json" "$PACKAGE_DIR/artifacts/latest_remediation_output.json"
copy_if_exists "$OUT_DIR/latest_cicd_context.json" "$PACKAGE_DIR/artifacts/latest_cicd_context.json"
copy_if_exists "$OUT_DIR/latest_cicd_context.txt" "$PACKAGE_DIR/artifacts/latest_cicd_context.txt"
copy_if_exists "$OUT_DIR/latest_slack_approval_card.json" "$PACKAGE_DIR/artifacts/latest_slack_approval_card.json"
copy_if_exists "$OUT_DIR/latest_slack_approval_card.txt" "$PACKAGE_DIR/artifacts/latest_slack_approval_card.txt"
copy_if_exists "$OUT_DIR/latest_slack_approval_decision.json" "$PACKAGE_DIR/artifacts/latest_slack_approval_decision.json"
copy_if_exists "$OUT_DIR/latest_audit_verification.json" "$PACKAGE_DIR/artifacts/latest_audit_verification.json"
copy_if_exists "$OUT_DIR/latest_incident_id" "$PACKAGE_DIR/artifacts/latest_incident_id"
copy_if_exists "$OUT_DIR/latest_cicd_manifest_diff.txt" "$PACKAGE_DIR/artifacts/latest_cicd_manifest_diff.txt"

if [[ -d "$OUT_DIR/prevention-pr" ]]; then
  cp -R "$OUT_DIR/prevention-pr" "$PACKAGE_DIR/prevention-pr"
  echo "copied: $OUT_DIR/prevention-pr -> $PACKAGE_DIR/prevention-pr"
else
  echo "missing optional artifact: $OUT_DIR/prevention-pr"
fi

python3 "$SCRIPT_DIR/demo_investor_summary.py" --package-dir "$PACKAGE_DIR"

cat <<EOF2

SafeOps investor demo package ready.
Package directory:
  $PACKAGE_DIR

Open cockpit:
  xdg-open $PACKAGE_DIR/incident-cockpit.html

Or serve it in a browser:
  python3 -m http.server 8088 --directory $PACKAGE_DIR
  http://127.0.0.1:8088/incident-cockpit.html

Key files:
  $PACKAGE_DIR/investor-summary.md
  $PACKAGE_DIR/investor-summary.json
  $PACKAGE_DIR/incident-cockpit.html
  $PACKAGE_DIR/logs/full-demo-output.log
  $PACKAGE_DIR/artifacts/
EOF2
