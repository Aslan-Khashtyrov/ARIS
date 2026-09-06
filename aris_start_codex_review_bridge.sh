#!/data/data/com.termux/files/usr/bin/bash
set -eu

MAIN_ROOT="/data/data/com.termux/files/home/Arbitrage"
WORKTREE="/data/data/com.termux/files/home/aris_codex_review_worktree"

if [ "${1-}" != "--inside-ubuntu" ]; then
  if ! command -v proot-distro >/dev/null 2>&1; then
    printf '%s\n' "[ОШИБКА] proot-distro не найден в Termux."
    exit 1
  fi
  printf '%s\n' "[1/4] Вхожу в Ubuntu для запуска официального Codex CLI..."
  exec proot-distro login ubuntu -- /bin/bash "${MAIN_ROOT}/aris_start_codex_review_bridge.sh" --inside-ubuntu
fi

if [ ! -x /usr/bin/codex ]; then
  printf '%s\n' "[ОШИБКА] /usr/bin/codex не найден."
  exit 1
fi
if [ ! -d "${MAIN_ROOT}/.git" ]; then
  printf '%s\n' "[ОШИБКА] Репозиторий A.R.I.S. не найден."
  exit 1
fi

printf '%s\n' "[2/4] Обновляю только сведения GitHub..."
git -C "${MAIN_ROOT}" fetch --quiet --no-tags origin   refs/heads/main:refs/remotes/origin/main

if [ -e "${WORKTREE}/.git" ]; then
  if [ -n "$(git -C "${WORKTREE}" status --porcelain --untracked-files=all)" ]; then
    printf '%s\n' "[ОШИБКА] Отдельная рабочая копия не чиста; ничего не изменено."
    exit 1
  fi
  git -C "${WORKTREE}" fetch --quiet --no-tags origin     refs/heads/main:refs/remotes/origin/main
  git -C "${WORKTREE}" -c core.hooksPath=/dev/null merge --ff-only origin/main
else
  if [ -e "${WORKTREE}" ]; then
    printf '%s\n' "[ОШИБКА] Путь отдельной копии уже занят: ${WORKTREE}"
    exit 1
  fi
  printf '%s\n' "[3/4] Создаю отдельную read-only рабочую копию..."
  git -C "${MAIN_ROOT}" worktree add --detach "${WORKTREE}" origin/main
fi

printf '%s\n' "[4/4] Запускаю GitHub ↔ Codex мост."
printf '%s\n' "Codex работает только с заранее заданными задачами в sandbox=read-only."
printf '%s\n' "Ctrl+C остановит только этот мост."
export ARIS_MAIN_ROOT="${MAIN_ROOT}"
export ARIS_CODEX_WORKTREE="${WORKTREE}"
cd "${WORKTREE}"
exec /usr/bin/python3 aris_codex_review_worker_v01.py
