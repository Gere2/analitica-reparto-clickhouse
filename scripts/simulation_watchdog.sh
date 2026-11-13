#!/bin/bash
# Keeps long Atlas simulations running on the demo host (Windows + Git Bash + Docker Desktop).
# Every 2 minutes: restarts Docker Desktop and the existing containers if they closed, and for each
# Atlas API port whose simulation stopped, saves that run to data/runs/ and starts a new one.
#
#   bash scripts/simulation_watchdog.sh 8001:hybrid 18001:traffic
#
# Each argument is <port>:<agent_mode>. New runs use 500 customers, 150 couriers and 1 s ticks
# (override with CUSTOMERS, FLEET, INTERVAL). EXTRA_CONTAINERS lists containers outside Compose
# (for example a second Atlas API) to start again after Docker comes back.
#
# Safety rules:
# - A stopped run is exported, and a new one started, only after that API reports pending=0.
#   If the queue does not drain or the export fails, nothing new starts; the next pass retries.
# - export_run.py writes to a temporary folder and renames it only when every file is complete.
# - Maintenance pause: while data/runs/WATCHDOG-PAUSE exists, the watchdog does nothing.
# - Disk reserve: when free space on this drive falls below DISK_RESERVE_GB (default 50), it stops
#   every run, saves them and creates WATCHDOG-PAUSE. Delete that file to resume.
# - Containers are started, never recreated, so the running version is kept.
#
# Stop it with `kill <pid>`: on Windows, stopping the terminal that started it may leave the bash
# loop running, and it will restart the runs you stopped. Create WATCHDOG-PAUSE first to be safe.
set -o pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO" || exit 1
CUSTOMERS=${CUSTOMERS:-500} FLEET=${FLEET:-150} INTERVAL=${INTERVAL:-1} DISK_RESERVE_GB=${DISK_RESERVE_GB:-50}
PAUSE=data/runs/WATCHDOG-PAUSE
RESERVE_PENDING=data/runs/WATCHDOG-PAUSE.reserve-pending
DRAIN_TIMEOUT_SECONDS=${DRAIN_TIMEOUT_SECONDS:-240}
DRAIN_POLL_SECONDS=${DRAIN_POLL_SECONDS:-2}
log() { echo "$(date +'%m-%d %H:%M:%S') $*"; }
field() { python -c "import sys,json; v=json.load(sys.stdin).get('$1'); print('' if v is None else v)" 2>/dev/null; }

queue_zero() {
  curl -fsS -m 5 "http://127.0.0.1:$1/api/status" | python -c \
    'import json,sys; v=json.load(sys.stdin).get("pending"); sys.exit(0 if type(v) is int and v == 0 else 1)' 2>/dev/null
}

drained() {  # An explicit zero is required. Unknown/error/timeout is never success.
  local pending begin=$SECONDS
  while true; do
    queue_zero "$1" && return 0
    [ $((SECONDS-begin)) -ge "$DRAIN_TIMEOUT_SECONDS" ] && break
    sleep "$DRAIN_POLL_SECONDS"
  done
  log "port $1: queue still has ${pending:-unknown} pending events"; return 1
}

save_run() {  # port run_id -> success if the run is (already) exported
  local run=$2
  [ -z "$run" ] && return 0
  # The exporter verifies existing archives; a directory alone proves nothing.
  if python scripts/export_run.py "$run" >/dev/null 2>&1; then log "port $1: saved run ${run:0:8}"; return 0; fi
  log "port $1: export of ${run:0:8} FAILED"; return 1
}

check_api() {  # port agent_mode
  local port=$1 mode=$2 sim run new current free
  [ -e "$PAUSE" ] && return 0
  sim=$(curl -fsS -m 10 "http://127.0.0.1:$port/api/simulation") || return 1
  [ -z "$sim" ] && return 1
  [ "$(echo "$sim" | field running)" = "True" ] && return 0
  [ "$(echo "$sim" | field running)" = "False" ] || return 1
  run=$(echo "$sim" | field run_id)
  drained "$port" && save_run "$port" "$run" || { log "port $port: not starting a new run yet"; return 0; }
  # Maintenance or a manual restart may have happened during drain/export.
  [ -e "$PAUSE" ] && return 0
  current=$(curl -fsS -m 10 "http://127.0.0.1:$port/api/simulation") || return 1
  [ "$(echo "$current" | field running)" = "False" ] || return 0
  [ "$(echo "$current" | field run_id)" = "$run" ] || return 0
  queue_zero "$port" || return 0
  free=$(free_gb)
  [[ "$free" =~ ^[0-9]+$ ]] && [ "$free" -ge "$DISK_RESERVE_GB" ] || { log "port $port: disk reserve unknown/reached; not starting"; return 0; }
  [ -e "$PAUSE" ] && return 0
  new=$(curl -fsS -m 20 -X POST "http://127.0.0.1:$port/api/simulation/start" -H 'Content-Type: application/json' \
    -d "{\"mode\":\"customers\",\"agent_mode\":\"$mode\",\"customers\":$CUSTOMERS,\"fleet\":$FLEET,\"interval\":$INTERVAL,\"seed\":$((RANDOM % 10000))}" \
    | python -c 'import json,sys; from uuid import UUID; v=json.load(sys.stdin); assert v["running"] is True; print(UUID(v["run_id"]))') || { log "port $port: start not confirmed; inspect API before retrying"; return 1; }
  log "port $port: simulation was stopped; started new run $new"
}

free_gb() { python -c 'import shutil; print(shutil.disk_usage(".").free // 1000000000)'; }

reserve_reached() {  # stop and save every run, then pause
  log "DISK RESERVE: ${1} GB free, reserve ${DISK_RESERVE_GB} GB. Stopping all runs."
  date > "$PAUSE"
  touch "$RESERVE_PENDING"
  local target port sim run complete=1
  for target in $TARGETS; do
    port=${target%%:*}
    sim=$(curl -fsS -m 20 -X POST "http://127.0.0.1:$port/api/simulation/stop" -H 'Content-Type: application/json' -d '{}') || { complete=0; continue; }
    [ "$(echo "$sim" | field running)" = "False" ] || { complete=0; continue; }
    run=$(echo "$sim" | field run_id)
    drained "$port" && save_run "$port" "$run" || complete=0
  done
  if [ "$complete" = 1 ]; then
    rm -f "$RESERVE_PENDING"
    log "DISK RESERVE: runs stopped, verified and paused. Delete $PAUSE only after checking disk space."
  else
    log "DISK RESERVE: paused; stopping/export is incomplete and will be retried. Keep Docker/APIs available."
  fi
}

main() {
[ $# -eq 0 ] && set -- 8001:hybrid
for target in "$@"; do
  [[ "$target" =~ ^[0-9]+:(hybrid|traffic|ollama|policy)$ ]] || { log "Invalid port:mode: $target"; return 2; }
done
python -c 'import sys; c,f,i,r,*ports=sys.argv[1:]; assert 1<=int(c)<=500 and 1<=int(f)<=150 and 1<=float(i)<=10 and int(r)>0; assert all(1<=int(p.split(":")[0])<=65535 for p in ports)' "$CUSTOMERS" "$FLEET" "$INTERVAL" "$DISK_RESERVE_GB" "$@" || return 2
mkdir -p data/runs
TARGETS="$*"
trap 'date > "$PAUSE"; exit 0' INT TERM
log "watchdog started for $TARGETS (disk reserve ${DISK_RESERVE_GB} GB, $(free_gb) GB free)"
while true; do
  if [ -e "$PAUSE" ]; then
    [ -e "$RESERVE_PENDING" ] && reserve_reached "$(free_gb)"
    sleep 120; continue
  fi
  if ! docker info --format '{{.ServerVersion}}' 2>/dev/null | grep -q .; then
    log "Docker is down: opening Docker Desktop"
    powershell.exe -NoProfile -Command 'Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"' >/dev/null 2>&1
    for _ in $(seq 1 90); do docker info --format '{{.ServerVersion}}' 2>/dev/null | grep -q . && break; sleep 2; done
    docker info --format '{{.ServerVersion}}' 2>/dev/null | grep -q . || { log "Docker is still unavailable"; sleep 120; continue; }
    [ -e "$PAUSE" ] && continue
    docker compose -f compose.yaml --profile atlas --profile ai start >/dev/null 2>&1
    for container in $EXTRA_CONTAINERS; do docker start "$container" >/dev/null 2>&1; done
    log "Docker is back"
  fi
  free=$(free_gb)
  [[ "$free" =~ ^[0-9]+$ ]] || { log "Disk reserve unknown; no runs will be started"; sleep 120; continue; }
  if [ -n "$free" ] && [ "$free" -lt "$DISK_RESERVE_GB" ]; then reserve_reached "$free"; continue; fi
  for target in $TARGETS; do
    port=${target%%:*}
    for _ in $(seq 1 60); do curl -s -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/health" | grep -q 200 && break; sleep 2; done
    check_api "$port" "${target#*:}" || log "port $port: API not responding"
  done
  sleep 120
done
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then main "$@"; fi
