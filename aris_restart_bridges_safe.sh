#!/data/data/com.termux/files/usr/bin/bash
set -u

ARIS_ROOT="$HOME/Arbitrage"
STATE="$ARIS_ROOT/guardian_state"
JOURNAL="$ARIS_ROOT/journal"
CONTROL_SCRIPT="$ARIS_ROOT/aris_termux_control_v01.py"
BRIDGE_SCRIPT="$ARIS_ROOT/aris_start_codex_review_bridge.sh"
CONTROL_PIDFILE="$STATE/termux_control.pid"
CONTROL_LOG="$JOURNAL/termux_control.out.log"

fail() {
  printf '%s\n' "[ОШИБКА] $1"
  exit 1
}

positive_pid() {
  case "${1-}" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$1" -gt 1 ]
}

process_matches() {
  checked_pid="$1"
  expected="$2"
  positive_pid "$checked_pid" || return 1
  [ -r "/proc/$checked_pid/cmdline" ] || return 1
  checked_cmdline="$(tr '\000' ' ' <"/proc/$checked_pid/cmdline")"
  case "$checked_cmdline" in
    *"$expected"*) return 0 ;;
    *) return 1 ;;
  esac
}

review_worker_running() {
  for proc_dir in /proc/[0-9]*; do
    [ -r "$proc_dir/cmdline" ] || continue
    proc_cmdline="$(tr '\000' ' ' <"$proc_dir/cmdline" 2>/dev/null)" || continue
    case "$proc_cmdline" in
      *"aris_codex_review_worker_v01.py"*) return 0 ;;
    esac
  done
  return 1
}

[ -f "$CONTROL_SCRIPT" ] || fail "Контроллер не найден: $CONTROL_SCRIPT"
[ -f "$BRIDGE_SCRIPT" ] || fail "Codex-мост не найден: $BRIDGE_SCRIPT"
command -v python >/dev/null 2>&1 || fail "Python не найден в Termux"
mkdir -p "$STATE" "$JOURNAL"

if review_worker_running; then
  fail "Сначала останови видимый Codex-мост клавишами Ctrl+C и повтори команду."
fi

printf '%s\n' "[1/3] Проверяю действующий PING-контроллер..."
if [ -f "$CONTROL_PIDFILE" ]; then
  old_pid="$(tr -d '[:space:]' <"$CONTROL_PIDFILE")"
  positive_pid "$old_pid" || fail "Небезопасное значение PID; остановка отменена."
  if kill -0 "$old_pid" 2>/dev/null; then
    process_matches "$old_pid" "aris_termux_control_v01.py" ||
      fail "PID $old_pid принадлежит другому процессу; остановка отменена."
    printf '%s\n' "[2/3] Останавливаю только PING-контроллер pid=$old_pid..."
    kill -TERM -- "$old_pid"
    attempts=0
    while kill -0 "$old_pid" 2>/dev/null && [ "$attempts" -lt 20 ]; do
      sleep 0.5
      attempts=$((attempts + 1))
    done
    if kill -0 "$old_pid" 2>/dev/null; then
      fail "Контроллер не остановился; новый экземпляр не запущен."
    fi
  fi
  rm -f -- "$CONTROL_PIDFILE"
fi

printf '%s\n' "[3/3] Запускаю изолированный PING-контроллер v0.8..."
nohup python "$CONTROL_SCRIPT" >>"$CONTROL_LOG" 2>&1 &
new_pid=$!
printf '%s\n' "$new_pid" >"$CONTROL_PIDFILE"
sleep 2

if ! kill -0 "$new_pid" 2>/dev/null ||
   ! process_matches "$new_pid" "aris_termux_control_v01.py"; then
  printf '%s\n' "[ОШИБКА] Новый контроллер не запустился. Последние строки журнала:"
  tail -n 20 "$CONTROL_LOG" 2>/dev/null || true
  exit 1
fi

printf '%s\n' "[OK] PING-контроллер v0.8 запущен: pid=$new_pid"
printf '%s\n' "[OK] A.R.I.S. и торговые процессы не затронуты."
printf '%s\n' "[СТАРТ] Запускаю закреплённый GitHub ↔ Codex read-only мост..."
exec bash "$BRIDGE_SCRIPT"
