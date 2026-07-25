#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "== SafeOps public demo release-candidate check =="
echo "Repository: $REPO_ROOT"
echo

python3 scripts/safeops_release_candidate_report.py

echo
echo "Open/read the release-candidate report:"
echo "  less /tmp/safeops-demo/safeops-release-candidate-report.md"
