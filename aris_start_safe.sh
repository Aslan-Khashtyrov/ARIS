#!/data/data/com.termux/files/usr/bin/bash
set -u
ROOT="$HOME/Arbitrage"
STATE="$ROOT/guardian_state"
JOURNAL="$ROOT/journal"
mkdir -p "$STATE" "$JOURNAL"
rm -f "$STATE/intentional_stop"
cd "$ROOT" || exit 1

start_one(){
  name="$1"; script="$2"; pidfile="$STATE/$name.pid"; logfile="$JOURNAL/$name.out.log"
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running pid=$(cat "$pidfile")"
    return 0
  fi
  nohup python "$script" >>"$logfile" 2>&1 &
  pid=$!
  echo "$pid" >"$pidfile"
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    echo "$name started pid=$pid"
  else
    echo "$name failed; see $logfile"
    return 1
  fi
}

start_one main main.py
start_one scanner multi_scanner_v03.py
start_one guardian guardian_v04.py
start_one worker aris_worker_v03.py
start_one autopilot aris_autopilot_v01.py
start_one remote_agent aris_remote_agent_v02.py
start_one termux_control aris_termux_control_v01.py
python aris_local_core_v01.py
