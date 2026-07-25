#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

python3 scripts/safeops_update_readme_demo.py

echo ""
echo "SafeOps README demo section updated."
echo "Review the diff with:"
echo "  git diff -- README.md"
echo ""
echo "Backup created at: README.md.bak"
