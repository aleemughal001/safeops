#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p /tmp/safeops-demo
OUTPUT_FILE="/tmp/safeops-demo/demo-output-$(date +%Y%m%d-%H%M%S).txt"

echo "Capturing SafeOps demo output to: $OUTPUT_FILE"
echo "The demo is interactive. Type 'yes' when the approval prompt appears."
echo

./scripts/demo_run_full.sh | tee "$OUTPUT_FILE"

echo
echo "Demo output saved to: $OUTPUT_FILE"
