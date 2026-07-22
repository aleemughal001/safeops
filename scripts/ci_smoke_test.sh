#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

section() {
  echo
  echo "== $1 =="
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
  echo "ok: $path"
}

require_dir() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    echo "Missing required directory: $path" >&2
    exit 1
  fi
  echo "ok: $path"
}

require_executable() {
  local path="$1"
  require_file "$path"
  if [[ ! -x "$path" ]]; then
    echo "Required script is not executable: $path" >&2
    echo "Fix with: chmod +x $path" >&2
    exit 1
  fi
  echo "executable: $path"
}

section "SafeOps CI smoke test"
echo "Repository: $ROOT_DIR"

section "Required project structure"
require_dir backend
require_dir agent
require_dir scripts
require_dir docs
require_dir demo/k8s
require_dir examples
require_dir examples/investor
require_dir examples/dashboard
require_dir .github/workflows

section "Required documentation"
require_file README.md
require_file docs/security-model.md
require_file docs/action-allowlist.md
require_file docs/audit-log-schema.md
require_file docs/demo-runbook.md
require_file docs/incident-cockpit-demo.md
require_file docs/investor-demo-package.md
require_file docs/github-actions-ci.md
require_file examples/investor/README.md
require_file examples/dashboard/sample-incident-cockpit.html

section "Required demo scripts"
require_executable scripts/demo_run_full.sh
require_executable scripts/demo_run_full_with_cicd.sh
require_executable scripts/demo_run_full_with_slack.sh
require_executable scripts/demo_run_full_with_cockpit.sh
require_executable scripts/demo_run_investor.sh
require_executable scripts/demo_stop_services.sh
require_executable scripts/demo_investor_summary.py
require_executable scripts/demo_incident_cockpit.py

section "Shell syntax check"
while IFS= read -r -d '' script; do
  bash -n "$script"
  echo "bash -n ok: $script"
done < <(find scripts -maxdepth 1 -name '*.sh' -print0 | sort -z)

section "Python syntax check"
python3 - <<'PY'
import py_compile
from pathlib import Path

roots = [Path('backend'), Path('agent'), Path('scripts')]
skip_parts = {'.git', '.venv', '__pycache__'}
files = []
for root in roots:
    if not root.exists():
        continue
    for path in root.rglob('*.py'):
        if any(part in skip_parts for part in path.parts):
            continue
        files.append(path)

if not files:
    raise SystemExit('No Python files found to compile')

for path in sorted(files):
    py_compile.compile(str(path), doraise=True)
    print(f'py_compile ok: {path}')
PY

section "JSON artifact validation"
python3 - <<'PY'
import json
from pathlib import Path

json_files = sorted(Path('examples').rglob('*.json'))
if not json_files:
    print('No example JSON files found; skipping JSON validation.')
else:
    for path in json_files:
        with path.open('r', encoding='utf-8') as f:
            json.load(f)
        print(f'json ok: {path}')
PY

section "Demo manifest guardrail check"
ENV_PATTERN='^[[:space:]]*-[[:space:]]*name:[[:space:]]*REDIS_URL[[:space:]]*$'
if ! grep -Eq "$ENV_PATTERN" demo/k8s/checkout-api-working.yaml; then
  echo "Working manifest must include REDIS_URL" >&2
  exit 1
fi
echo "ok: working manifest includes REDIS_URL"

if grep -Eq "$ENV_PATTERN" demo/k8s/checkout-api-broken.yaml; then
  echo "Broken manifest should intentionally omit REDIS_URL for the demo incident" >&2
  exit 1
fi
echo "ok: broken manifest intentionally omits REDIS_URL"

section "Secret and archive safety check"
FOUND_UNSAFE=""
while IFS= read -r -d '' path; do
  FOUND_UNSAFE="${FOUND_UNSAFE}${path}"$'\n'
done < <(
  find . \
    \( -path './.git' -o -path './.git/*' -o -name '.venv' -o -name 'venv' -o -name 'node_modules' -o -name '__pycache__' -o -name 'site-packages' \) -prune -o \
    \( -name '*.pem' -o -name '*credentials*.csv' -o -name 'rootkey.csv' -o -name '*.key' -o -name '*.zip' \) \
    -print0
)

if [[ -n "$FOUND_UNSAFE" ]]; then
  echo "Potential secret/archive files found. Do not commit these:" >&2
  printf '%s' "$FOUND_UNSAFE" >&2
  exit 1
fi
echo "ok: no pem/key/credentials/zip files found outside ignored generated folders"

section "SafeOps CI smoke test complete"
echo "All checks passed."
