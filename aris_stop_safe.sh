#!/data/data/com.termux/files/usr/bin/bash
set -u
ROOT="$HOME/Arbitrage"
STATE="$ROOT/guardian_state"
mkdir -p "$STATE"
touch "$STATE/intentional_stop"

stop_one(){
  name="$1"; pidfile="$STATE/$name.pid"
  if [ ! -f "$pidfile" ]; then
    echo "$name not tracked"
    return 0
  fi
  pid="$(cat "$pidfile")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    sleep 1
  fi
  if kill -0 "$pid" 2>/dev/null; then
    echo "$name still running pid=$pid"
    return 1
  fi
  rm -f "$pidfile"
  echo "$name stopped"
}

stop_one termux_control
stop_one remote_agent
stop_one autopilot
stop_one worker
stop_one guardian
stop_one scanner
stop_one main
