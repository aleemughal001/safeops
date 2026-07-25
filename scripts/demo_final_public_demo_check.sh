#!/usr/bin/env bash
set -euo pipefail

echo "== SafeOps final public demo check =="
echo "Repository: $(pwd)"
echo

echo "1/4 Git status"
git status --short
if [ -n "$(git status --short)" ]; then
  echo "Working tree is not clean. Commit changes before final public demo check."
  exit 1
fi

echo
echo "2/4 CI smoke test"
bash scripts/ci_smoke_test.sh

echo
echo "3/4 Release candidate check"
bash scripts/demo_release_candidate_check.sh

echo
echo "4/4 Fresh clone check"
bash scripts/demo_fresh_clone_check.sh

echo
echo "SafeOps final public demo check passed."
echo "Ready for v1.0-public-demo tag."
