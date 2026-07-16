#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${SAFEOPS_DEMO_STATE_DIR:-/tmp/safeops-demo}"
PID_DIR="$STATE_DIR/pids"

stop_service() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  if [ ! -f "$pid_file" ]; then
    echo "$name: no pid file found"
    return 0
  fi
  local pid
  pid=$(cat "$pid_file" || true)
  if [ -z "${pid:-}" ]; then
    rm -f "$pid_file"
    return 0
  fi
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Stopping $name pid=$pid"
    kill -TERM -"$pid" >/dev/null 2>&1 || kill -TERM "$pid" >/dev/null 2>&1 || true
    sleep 2
  else
    echo "$name: process already stopped"
  fi
  rm -f "$pid_file"
}

stop_service executor
stop_service backend

echo "Service stop requested."
