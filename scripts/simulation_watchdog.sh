#!/bin/bash
# Keeps long Atlas simulations running on the demo host (Windows + Git Bash + Docker Desktop).
# Every 2 minutes: reopens Docker Desktop if it closed, and for each Atlas API port whose
# simulation stopped, waits for the queue to drain, exports the run to data/runs/ and starts a new one.
#
#   bash scripts/simulation_watchdog.sh 8001:hybrid 18001:traffic
#
# Each argument is <port>:<agent_mode>. New runs use 500 customers, 150 couriers and 1 s ticks
# (override with CUSTOMERS, FLEET, INTERVAL). EXTRA_CONTAINERS lists containers outside Compose
# (for example a second Atlas API) to start again after Docker comes back.
# Stop it with `kill <pid>`: on Windows, stopping the terminal that started it may leave the bash
# loop running, and it will restart the runs you stopped.
REPO=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO" || exit 1
CUSTOMERS=${CUSTOMERS:-500} FLEET=${FLEET:-150} INTERVAL=${INTERVAL:-1}
[ $# -eq 0 ] && set -- 8001:hybrid
log() { echo "$(date +'%m-%d %H:%M:%S') $*"; }
field() { python -c "import sys,json; v=json.load(sys.stdin).get('$1'); print('' if v is None else v)" 2>/dev/null; }

check_api() {  # port agent_mode
  local port=$1 mode=$2 sim run pending new
  sim=$(curl -s -m 10 "http://127.0.0.1:$port/api/simulation") || return 1
  [ -z "$sim" ] && return 1
  [ "$(echo "$sim" | field running)" = "True" ] && return 0
  run=$(echo "$sim" | field run_id)
  for _ in $(seq 1 60); do
    pending=$(curl -s -m 5 "http://127.0.0.1:$port/api/status" | field pending)
    [ "$pending" = "0" ] && break; sleep 2
  done
  if [ -n "$run" ] && ! ls -d data/runs/*_"${run:0:8}" >/dev/null 2>&1; then
    python scripts/export_run.py "$run" >/dev/null 2>&1 && log "port $port: saved run ${run:0:8}" \
      || log "port $port: export of ${run:0:8} FAILED"
  fi
  new=$(curl -s -m 20 -X POST "http://127.0.0.1:$port/api/simulation/start" -H 'Content-Type: application/json' \
    -d "{\"mode\":\"customers\",\"agent_mode\":\"$mode\",\"customers\":$CUSTOMERS,\"fleet\":$FLEET,\"interval\":$INTERVAL,\"seed\":$((RANDOM % 10000))}" \
    | field run_id)
  log "port $port: simulation was stopped; started new run ${new:-?}"
}

log "watchdog started for $*"
while true; do
  if ! docker info --format '{{.ServerVersion}}' 2>/dev/null | grep -q .; then
    log "Docker is down: opening Docker Desktop"
    powershell.exe -NoProfile -Command 'Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"' >/dev/null 2>&1
    for _ in $(seq 1 90); do docker info --format '{{.ServerVersion}}' 2>/dev/null | grep -q . && break; sleep 2; done
    docker compose -f compose.yaml --profile atlas --profile ai up -d >/dev/null 2>&1
    for container in $EXTRA_CONTAINERS; do docker start "$container" >/dev/null 2>&1; done
    log "Docker is back"
  fi
  for target in "$@"; do
    port=${target%%:*}
    for _ in $(seq 1 60); do curl -s -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/health" | grep -q 200 && break; sleep 2; done
    check_api "$port" "${target#*:}" || log "port $port: API not responding"
  done
  sleep 120
done
