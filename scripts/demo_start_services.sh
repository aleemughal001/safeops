#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${SAFEOPS_DEMO_STATE_DIR:-/tmp/safeops-demo}"
LOG_DIR="$STATE_DIR/logs"
PID_DIR="$STATE_DIR/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

wait_for_url() {
  local name="$1"
  local url="$2"
  local timeout="${3:-45}"
  local start
  start=$(date +%s)
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is healthy: $url"
      return 0
    fi
    if [ $(( $(date +%s) - start )) -ge "$timeout" ]; then
      echo "$name did not become healthy within ${timeout}s: $url" >&2
      echo "Recent logs for $name:" >&2
      tail -80 "$LOG_DIR/${name}.log" 2>/dev/null || true
      return 1
    fi
    sleep 1
  done
}

start_service() {
  local name="$1"
  local command="$2"
  local health_url="$3"
  local pid_file="$PID_DIR/${name}.pid"
  local log_file="$LOG_DIR/${name}.log"

  if curl -fsS "$health_url" >/dev/null 2>&1; then
    echo "$name already appears to be running: $health_url"
    return 0
  fi

  if [ -f "$pid_file" ]; then
    local old_pid
    old_pid=$(cat "$pid_file" || true)
    if [ -n "${old_pid:-}" ] && kill -0 "$old_pid" >/dev/null 2>&1; then
      echo "$name has a stale/unhealthy process. Stopping pid $old_pid first."
      kill -TERM -"$old_pid" >/dev/null 2>&1 || kill -TERM "$old_pid" >/dev/null 2>&1 || true
      sleep 2
    fi
  fi

  echo "Starting $name..."
  : > "$log_file"
  setsid bash -lc "cd '$ROOT_DIR' && $command" > "$log_file" 2>&1 &
  echo "$!" > "$pid_file"
  wait_for_url "$name" "$health_url" 60
}

start_service "executor" "./scripts/run_executor_kubernetes.sh" "http://localhost:8010/health"
start_service "backend" "./scripts/run_backend.sh" "http://localhost:8000/health"

echo
printf 'Services are running. Logs:\n'
printf '  Executor: %s\n' "$LOG_DIR/executor.log"
printf '  Backend:  %s\n' "$LOG_DIR/backend.log"

echo
./scripts/demo_status.sh || true
