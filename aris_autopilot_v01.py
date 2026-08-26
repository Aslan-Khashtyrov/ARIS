from pathlib import Path
from datetime import datetime
import json
import os
import signal
import subprocess
import sys
import time

ROOT = Path.home() / "Arbitrage"
STATE = ROOT / "guardian_state"
JOURNAL = ROOT / "journal"
STOP_FLAG = STATE / "intentional_stop"
LOG = JOURNAL / "autopilot_v01.log"
CHECK_EVERY = 15
VERSION = "0.2"
CONTROL_HEARTBEAT = STATE / "termux_control_heartbeat.json"
CONTROL_MAX_HEARTBEAT_AGE = 90

COMPONENTS = {
    "main": "main.py",
    "scanner": "multi_scanner_v03.py",
    "guardian": "guardian_v04.py",
    "worker": "aris_worker_v03.py",
    "termux_control": "aris_termux_control_v01.py",
    "foreman": "aris_foreman_v01.py",
}

STATE.mkdir(parents=True, exist_ok=True)
JOURNAL.mkdir(parents=True, exist_ok=True)

def log(event, **fields):
    record = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, **fields}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

def tracked_pid(name):
    path = STATE / f"{name}.pid"
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None

def valid_process(pid, script):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return script in cmdline
    except Exception:
        return False


def heartbeat_age(path):
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


def stop_stale_control(pid, age):
    try:
        os.kill(pid, signal.SIGTERM)
        log("stale_control_stopped", component="termux_control", pid=pid, heartbeat_age_seconds=age)
        time.sleep(2)
    except ProcessLookupError:
        pass
    except Exception as exc:
        log("stale_control_stop_failed", component="termux_control", pid=pid, error=f"{type(exc).__name__}: {exc}")

def start_component(name, script):
    logfile = JOURNAL / f"{name}.out.log"
    with logfile.open("ab") as output:
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / script)],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    (STATE / f"{name}.pid").write_text(str(proc.pid), encoding="utf-8")
    time.sleep(1)
    ok = valid_process(proc.pid, script)
    log("restart", component=name, script=script, pid=proc.pid, ok=ok)
    return ok

log("started", version=VERSION, mode="monitoring_only", real_trading=False, shell_access=False)
while True:
    if STOP_FLAG.exists():
        time.sleep(CHECK_EVERY)
        continue
    for name, script in COMPONENTS.items():
        pid = tracked_pid(name)
        online = valid_process(pid, script)
        if name == "termux_control" and online:
            age = heartbeat_age(CONTROL_HEARTBEAT)
            if age is None or age > CONTROL_MAX_HEARTBEAT_AGE:
                stop_stale_control(pid, age)
                online = False
        if not online:
            start_component(name, script)
    time.sleep(CHECK_EVERY)
