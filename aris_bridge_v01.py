import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT = Path.home() / "Arbitrage"
JOURNAL = PROJECT / "journal"
BACKUPS = PROJECT / "backups"
AUDIT = JOURNAL / "aris_bridge_audit.log"

JOURNAL.mkdir(exist_ok=True)
BACKUPS.mkdir(exist_ok=True)

ALLOWED = {
    "STATUS",
    "READ_ARIS_LOG",
    "CHECK_HISTORY",
    "BACKUP",
}

WATCH = {
    "ARBITRAZHNIK": "main.py",
    "GUARDIAN": "guardian_v031.py",
    "MULTI_SCANNER": "multi_scanner_v02.py",
    "ARIS": "aris_v01.py",
}

def audit(action, result):
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now():%Y-%m-%d %H:%M:%S} | "
            f"{action} | {result}\n"
        )

def running(pattern):
    try:
        r = subprocess.run(
            ["pgrep", "-af", pattern],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return bool(r.stdout.strip())
    except Exception:
        return False

def status():
    return {
        name: "ONLINE" if running(pattern) else "OFFLINE"
        for name, pattern in WATCH.items()
    }

def check_history():
    path = JOURNAL / "multi_history_v02.csv"

    if not path.exists():
        return {"exists": False}

    stat = path.stat()

    return {
        "exists": True,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(
            stat.st_mtime
        ).isoformat(timespec="seconds"),
    }

def read_aris_log():
    path = JOURNAL / "aris.log"

    if not path.exists():
        return []

    lines = path.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines()

    return lines[-20:]

def backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUPS / f"aris_backup_{stamp}"

    target.mkdir()

    files = [
        "main.py",
        "guardian_v031.py",
        "multi_scanner_v02.py",
        "aris_v01.py",
        "aris_bridge_v01.py",
    ]

    copied = []

    for name in files:
        src = PROJECT / name
        if src.exists():
            shutil.copy2(src, target / name)
            copied.append(name)

    return {
        "backup": str(target),
        "files": copied,
    }

def execute(action):
    action = action.strip().upper()

    if action not in ALLOWED:
        audit(action, "DENIED")
        return {
            "ok": False,
            "action": action,
            "error": "ACTION NOT ALLOWED",
        }

    try:
        if action == "STATUS":
            result = status()

        elif action == "CHECK_HISTORY":
            result = check_history()

        elif action == "READ_ARIS_LOG":
            result = read_aris_log()

        elif action == "BACKUP":
            result = backup()

        audit(action, "OK")

        return {
            "ok": True,
            "action": action,
            "result": result,
        }

    except Exception as e:
        audit(action, f"ERROR:{type(e).__name__}")

        return {
            "ok": False,
            "action": action,
            "error": f"{type(e).__name__}: {e}",
        }

print("=" * 64)
print("A.R.I.S. COMMAND BRIDGE v0.1")
print("SAFE MODE")
print("ALLOWED:", ", ".join(sorted(ALLOWED)))
print("SHELL COMMANDS: DISABLED")
print("REAL TRADING: DISABLED")
print("=" * 64)

while True:
    try:
        command = input("ARIS> ").strip()

        if not command:
            continue

        if command.upper() in {"EXIT", "QUIT"}:
            print("Bridge stopped safely.")
            break

        response = execute(command)
        print(json.dumps(response, indent=2, ensure_ascii=False))

    except KeyboardInterrupt:
        print("\nBridge stopped safely.")
        break
