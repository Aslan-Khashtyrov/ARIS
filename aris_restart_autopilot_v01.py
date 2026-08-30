#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.home() / "Arbitrage"
STATE = ROOT / "guardian_state"
JOURNAL = ROOT / "journal"
SCRIPT = "aris_autopilot_v01.py"
PIDFILE = STATE / "autopilot.pid"
STOP_TIMEOUT = 10


def valid_process(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return SCRIPT in cmdline
    except Exception:
        return False


def tracked_pid() -> int | None:
    try:
        return int(PIDFILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def main() -> int:
    old_pid = tracked_pid()
    if valid_process(old_pid):
        os.kill(old_pid, signal.SIGTERM)
        deadline = time.time() + STOP_TIMEOUT
        while time.time() < deadline and valid_process(old_pid):
            time.sleep(0.5)
        if valid_process(old_pid):
            print(json.dumps({"ok": False, "error": "old_autopilot_did_not_stop", "pid": old_pid}))
            return 2

    logfile = JOURNAL / "autopilot.out.log"
    with logfile.open("ab") as output:
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / SCRIPT)],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PIDFILE.write_text(str(proc.pid), encoding="utf-8")
    time.sleep(2)
    ok = valid_process(proc.pid)
    print(json.dumps({"ok": ok, "old_pid": old_pid, "new_pid": proc.pid, "version": "0.3"}))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
