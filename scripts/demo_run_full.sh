#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== SafeOps full repeatable demo ==="
echo

./scripts/demo_setup.sh
./scripts/demo_start_services.sh
./scripts/demo_status.sh
./scripts/demo_reset_healthy.sh
./scripts/demo_break_app.sh
./scripts/demo_detect.sh
./scripts/demo_approve_prompt.sh
./scripts/demo_verify.sh
./scripts/demo_report.sh

echo
echo "Full demo completed."
echo "To stop backend/executor started by this demo, run: ./scripts/demo_stop_services.sh"
