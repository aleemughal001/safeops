#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ARTIFACT_DIR="${SAFEOPS_ARTIFACT_DIR:-/tmp/safeops-demo}"
TS="$(date -u +%Y%m%d-%H%M%S)"
CLONE_DIR="$ARTIFACT_DIR/safeops-fresh-clone-$TS"
CI_OUTPUT="$ARTIFACT_DIR/fresh-clone-ci-output.txt"
JSON_OUT="$ARTIFACT_DIR/safeops-fresh-clone-report.json"
MD_OUT="$ARTIFACT_DIR/safeops-fresh-clone-report.md"

mkdir -p "$ARTIFACT_DIR"
rm -rf "$CLONE_DIR"

echo "== SafeOps fresh clone validation =="
echo "Source repo: $REPO_ROOT"
echo "Clone dir: $CLONE_DIR"
echo

git clone --quiet "$REPO_ROOT" "$CLONE_DIR"

(
  cd "$CLONE_DIR"
  bash scripts/ci_smoke_test.sh
) > "$CI_OUTPUT" 2>&1

python3 "$REPO_ROOT/scripts/safeops_fresh_clone_report.py" \
  --clone-dir "$CLONE_DIR" \
  --ci-output "$CI_OUTPUT" \
  --source-repo "$REPO_ROOT" \
  --json-out "$JSON_OUT" \
  --markdown-out "$MD_OUT"

echo
echo "SafeOps fresh clone validation complete."
echo "Open/read the report:"
echo "  less $MD_OUT"
echo "Open/read the clean clone CI output:"
echo "  less $CI_OUTPUT"
