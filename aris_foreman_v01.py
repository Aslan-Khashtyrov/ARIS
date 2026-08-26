#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

VERSION = "0.1"
ROOT = Path.home() / "Arbitrage"
STATE = ROOT / "guardian_state"
JOURNAL = ROOT / "journal"
PIDFILE = STATE / "foreman.pid"
STATUS = JOURNAL / "foreman_status_v01.json"
EVENTS = JOURNAL / "foreman_events_v01.jsonl"
STOP = False
INTERVAL = 10

COMPONENTS = {
    "main": "main.py",
    "scanner": "multi_scanner_v03.py",
    "guardian": "guardian_v04.py",
    "worker": "aris_worker_v03.py",
    "autopilot": "aris_autopilot_v01.py",
    "termux_control": "aris_termux_control_v01.py",
}

RUNTIME_FILES = {
    "session_stats": (JOURNAL / "session_stats.json", 180),
    "spot_history": (JOURNAL / "multi_history_v03.csv", 180),
    "cycle_quotes": (JOURNAL / "cycle_quotes_v01.json", 30),
    "cycle_report": (JOURNAL / "cycle_report_v01.json", 30),
}


def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def event(name: str, **fields) -> None:
    with EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"time": timestamp(), "event": name, **fields}, ensure_ascii=False) + "\n")


def process_state(name: str, script: str) -> dict:
    pidfile = STATE / f"{name}.pid"
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return {"online": script in cmdline, "pid": pid, "script": script}
    except Exception:
        return {"online": False, "pid": None, "script": script}


def file_state(path: Path, maximum_age: int) -> dict:
    try:
        age = round(time.time() - path.stat().st_mtime, 1)
        return {"fresh": age <= maximum_age, "age_seconds": age, "maximum_age": maximum_age}
    except OSError:
        return {"fresh": False, "age_seconds": None, "maximum_age": maximum_age}


def disk_state() -> dict:
    stats = os.statvfs(ROOT)
    total = stats.f_blocks * stats.f_frsize
    free = stats.f_bavail * stats.f_frsize
    return {"total_mb": round(total / 1048576, 1), "free_mb": round(free / 1048576, 1), "free_percent": round((free / total) * 100, 2) if total else 0}


def snapshot(cycle: int) -> dict:
    processes = {name: process_state(name, script) for name, script in COMPONENTS.items()}
    runtime = {name: file_state(path, age) for name, (path, age) in RUNTIME_FILES.items()}
    disk = disk_state()
    problems = []
    for name, info in processes.items():
        if not info["online"]:
            problems.append(f"process_offline:{name}")
    for name, info in runtime.items():
        if not info["fresh"]:
            problems.append(f"runtime_stale:{name}")
    if disk["free_percent"] < 10:
        problems.append("disk_space_low")
    return {
        "ok": not problems,
        "time": timestamp(),
        "version": VERSION,
        "mode": "CONTINUOUS_SAFE_OPERATIONS",
        "cycle": cycle,
        "interval_seconds": INTERVAL,
        "processes": processes,
        "runtime": runtime,
        "disk": disk,
        "problems": problems,
        "safety": {"real_trading": False, "orders": False, "payments": False, "withdrawals": False, "api_secrets": False},
    }


def stop_handler(_signum, _frame) -> None:
    global STOP
    STOP = True


def already_running() -> bool:
    try:
        pid = int(PIDFILE.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def daemonize() -> None:
    if already_running():
        print("foreman already running")
        return
    pid = os.fork()
    if pid:
        print(f"foreman starting pid={pid}")
        return
    os.setsid()
    null = os.open("/dev/null", os.O_RDWR)
    os.dup2(null, 0)
    os.dup2(null, 1)
    os.dup2(null, 2)
    run_loop()
    os._exit(0)


def run_loop() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    JOURNAL.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()), encoding="utf-8")
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    event("started", version=VERSION, pid=os.getpid())
    previous = set()
    cycle = 0
    try:
        while not STOP:
            cycle += 1
            report = snapshot(cycle)
            atomic_json(STATUS, report)
            current = set(report["problems"])
            for problem in sorted(current - previous):
                event("problem_detected", problem=problem)
            for problem in sorted(previous - current):
                event("problem_resolved", problem=problem)
            if cycle % 6 == 0:
                event("heartbeat", cycle=cycle, ok=report["ok"], problems=report["problems"])
            previous = current
            time.sleep(INTERVAL)
    finally:
        event("stopped", pid=os.getpid())
        try:
            PIDFILE.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemonize()
    else:
        if already_running():
            print("foreman already running")
            raise SystemExit(0)
        run_loop()
