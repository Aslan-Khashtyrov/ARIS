#!/data/data/com.termux/files/usr/bin/bash
set -u

ARIS_ROOT="$HOME/Arbitrage"
STATE="$ARIS_ROOT/guardian_state"
mkdir -p "$STATE"
touch "$STATE/intentional_stop"

expected_script() {
  case "$1" in
    foreman) printf '%s\n' "aris_foreman_v01.py" ;;
    termux_control) printf '%s\n' "aris_termux_control_v01.py" ;;
    remote_agent) printf '%s\n' "aris_remote_agent_v0" ;;
    autopilot) printf '%s\n' "aris_autopilot_v01.py" ;;
    worker) printf '%s\n' "aris_worker_v03.py" ;;
    guardian) printf '%s\n' "guardian_v04.py" ;;
    scanner) printf '%s\n' "multi_scanner_v03.py" ;;
    main) printf '%s\n' "main.py" ;;
    *) return 1 ;;
  esac
}

stop_one() {
  name="$1"
  pidfile="$STATE/$name.pid"

  if [ ! -f "$pidfile" ]; then
    printf '%s\n' "$name not tracked"
    return 0
  fi

  pid="$(tr -d '[:space:]' <"$pidfile")"
  case "$pid" in
    ''|*[!0-9]*)
      printf '%s\n' "$name refused: invalid pid file"
      return 1
      ;;
  esac
  if [ "$pid" -le 1 ]; then
    printf '%s\n' "$name refused: unsafe pid=$pid"
    return 1
  fi

  expected="$(expected_script "$name")" || {
    printf '%s\n' "$name refused: unknown component"
    return 1
  }

  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f -- "$pidfile"
    printf '%s\n' "$name stale pid removed"
    return 0
  fi
  if [ ! -r "/proc/$pid/cmdline" ]; then
    printf '%s\n' "$name refused: cannot verify pid=$pid"
    return 1
  fi

  cmdline="$(tr '\000' ' ' <"/proc/$pid/cmdline")"
  case "$cmdline" in
    *"$expected"*) ;;
    *)
      printf '%s\n' "$name refused: pid=$pid belongs to another process"
      return 1
      ;;
  esac

  kill -TERM -- "$pid"
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    printf '%s\n' "$name still running pid=$pid"
    return 1
  fi

  rm -f -- "$pidfile"
  printf '%s\n' "$name stopped"
}

stop_one foreman
stop_one termux_control
stop_one remote_agent
stop_one autopilot
stop_one worker
stop_one guardian
stop_one scanner
stop_one main
