#!/data/data/com.termux/files/usr/bin/bash
set -eu

ROOT="${HOME}/Arbitrage"
LOG="${ROOT}/journal/codex_github_steps.log"

mkdir -p "${ROOT}/journal"
touch "${LOG}"

printf '%s\n' "=== Шаги ChatGPT через GitHub (Ctrl+C — закрыть просмотр) ==="
printf '%s\n' "Файл: ${LOG}"
exec tail -n 40 -F "${LOG}"
