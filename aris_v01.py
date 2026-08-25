import os
import subprocess
import time
from datetime import datetime

VERSION = "0.1"
CHECK_EVERY = 15

PROJECT = os.path.expanduser("~/Arbitrage")
JOURNAL = os.path.join(PROJECT, "journal")
ARIS_LOG = os.path.join(JOURNAL, "aris.log")

WATCH = {
    "ARBITRAZHNIK": "main.py",
    "GUARDIAN": "guardian_v031.py",
    "MULTI_SCANNER": "multi_scanner_v02.py",
}

# ARIS v0.1:
# только безопасные операции чтения.
# Никаких kill/rm/торговых команд.
ALLOWED_ACTIONS = {
    "process_status",
    "data_status",
    "read_logs",
    "system_report",
}

def log(message):
    os.makedirs(JOURNAL, exist_ok=True)
    with open(ARIS_LOG, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now():%Y-%m-%d %H:%M:%S} | {message}\n"
        )

def process_running(pattern):
    try:
        result = subprocess.run(
            ["pgrep", "-af", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )

        lines = [
            line for line in result.stdout.splitlines()
            if "aris_v01.py" not in line
        ]

        return bool(lines)

    except Exception as e:
        log(f"PROCESS CHECK ERROR | {pattern} | {type(e).__name__}")
        return False

def file_status(relative_path):
    path = os.path.join(PROJECT, relative_path)

    try:
        stat = os.stat(path)
        return {
            "exists": True,
            "age": time.time() - stat.st_mtime,
            "size": stat.st_size,
        }
    except OSError:
        return {
            "exists": False,
            "age": None,
            "size": None,
        }

def system_report():
    processes = {
        name: process_running(pattern)
        for name, pattern in WATCH.items()
    }

    history = file_status("journal/multi_history_v02.csv")
    stats = file_status("journal/session_stats.json")

    print()
    print("=" * 66)
    print(f"A.R.I.S. v{VERSION} | SYSTEM REPORT")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("-" * 66)

    for name, ok in processes.items():
        print(f"{name:16}: {'ONLINE' if ok else 'OFFLINE'}")

    if history["exists"]:
        print(
            f"MULTI DATA      : age={history['age']:.0f}s "
            f"| size={history['size']} bytes"
        )
    else:
        print("MULTI DATA      : NOT FOUND")

    if stats["exists"]:
        print(
            f"MAIN STATS      : age={stats['age']:.0f}s "
            f"| size={stats['size']} bytes"
        )
    else:
        print("MAIN STATS      : NOT FOUND")

    print("-" * 66)
    print("CONTROL         : READ ONLY")
    print("REAL TRADING    : DISABLED")
    print("REMOTE SHELL    : DISABLED")
    print("=" * 66)

    return processes, history, stats

print("=" * 66)
print("A.R.I.S.")
print("Arbitrage Runtime Intelligence System")
print(f"VERSION: {VERSION}")
print("ROLE: SYSTEM ASSISTANT")
print("CONTROL: READ ONLY")
print("REAL TRADING: DISABLED")
print("=" * 66)

log("ARIS STARTED | v0.1 | READ ONLY")

try:
    while True:
        processes, history, stats = system_report()

        problems = []

        for name, ok in processes.items():
            if not ok:
                problems.append(f"{name}_OFFLINE")

        if history["exists"] and history["age"] > 120:
            problems.append("MULTI_DATA_STALE")

        if stats["exists"] and stats["age"] > 120:
            problems.append("MAIN_STATS_STALE")

        if problems:
            print("ARIS STATUS: ATTENTION")
            print("Detected:", ", ".join(problems))
        else:
            print("ARIS STATUS: ALL SYSTEMS NOMINAL")

        time.sleep(CHECK_EVERY)

except KeyboardInterrupt:
    log("ARIS STOPPED BY USER")
    print("\nARIS stopped safely.")
