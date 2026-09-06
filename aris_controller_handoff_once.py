#!/usr/bin/env python3
"""One-shot, exact handoff from the legacy bridge to the reviewed PING-only bridge."""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

EXPECTED_NONCE = "activate-ping-only-bridge-20260906"
HOME = Path.home().resolve()
ROOT = (HOME / "Arbitrage").resolve()
CONTROLLER = ROOT / "aris_termux_control_v01.py"
STATE = ROOT / "guardian_state"
JOURNAL = ROOT / "journal"
PIDFILE = STATE / "termux_control.pid"
MARKER = STATE / "termux_control_handoff_20260906.json"
STEPS = JOURNAL / "codex_github_steps.log"


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    JOURNAL.mkdir(parents=True, exist_ok=True)
    with STEPS.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp()} {message}\n")


def fail(message: str) -> "NoReturn":
    log(f"[ОТМЕНА] Перезапуск контроллера: {message}")
    raise SystemExit(message)


def main() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    JOURNAL.mkdir(parents=True, exist_ok=True)

    if sys.argv[1:] != [EXPECTED_NONCE]:
        fail("неверное одноразовое подтверждение")
    if MARKER.exists():
        fail("эта одноразовая передача уже выполнялась")

    parent_pid = os.getppid()
    if parent_pid <= 1:
        fail("не найден родительский процесс")

    try:
        parent_cmdline = (
            Path(f"/proc/{parent_pid}/cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode("utf-8", errors="replace")
        )
    except OSError as exc:
        fail(f"не удалось проверить родительский процесс: {type(exc).__name__}")

    if "aris_termux_control_v01.py" not in parent_cmdline:
        fail("родитель не является контроллером A.R.I.S.")

    source = CONTROLLER.read_text(encoding="utf-8")
    if 'VERSION = "0.7"' not in source:
        fail("на диске ещё не установлена версия 0.7")
    if 'ALLOWED_ACTIONS = frozenset({"PING"})' not in source:
        fail("проверка режима PING-only не пройдена")

    log(
        f"[ПЕРЕЗАПУСК] Проверен старый контроллер pid={parent_pid}; "
        "остальные процессы A.R.I.S. не затрагиваются."
    )

    with MARKER.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "time": timestamp(),
                "old_pid": parent_pid,
                "new_pid": os.getpid(),
                "scope": "termux_controller_only",
                "real_trading": False,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")

    null_input = open(os.devnull, "rb")
    runtime_log = (JOURNAL / "termux_control.out.log").open(
        "a", encoding="utf-8", buffering=1
    )
    os.dup2(null_input.fileno(), 0)
    os.dup2(runtime_log.fileno(), 1)
    os.dup2(runtime_log.fileno(), 2)
    try:
        os.setsid()
    except OSError:
        pass

    PIDFILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    log(
        f"[ПЕРЕЗАПУСК] Новый защищённый контроллер готовится, pid={os.getpid()}."
    )

    os.kill(parent_pid, signal.SIGTERM)
    time.sleep(1)
    log("[ПЕРЕЗАПУСК] Старая v0.5 завершена; запускается PING-only v0.7.")
    os.execv(sys.executable, [sys.executable, str(CONTROLLER)])


if __name__ == "__main__":
    main()
