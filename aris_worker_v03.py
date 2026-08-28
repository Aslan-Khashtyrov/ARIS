from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time

VERSION = "1.4"
CHECK_EVERY = 3
ROOT = Path.home() / "Arbitrage"
BASE = ROOT / "aris_queue"
PENDING = BASE / "pending"
DONE = BASE / "done"
REJECTED = BASE / "rejected"
RESULTS = BASE / "results"
JOURNAL = ROOT / "journal"
LOG = JOURNAL / "aris_worker.log"

for folder in (PENDING, DONE, REJECTED, RESULTS, JOURNAL):
    folder.mkdir(parents=True, exist_ok=True)

ALLOWED_ACTIONS = {"STATUS", "ANALYZE"}
PROCESSES = {
    "MAIN": "main.py",
    "SCANNER": "multi_scanner_v03.py",
    "GUARDIAN": "guardian_v04.py",
    "WORKER": "aris_worker_v03.py",
    "AUTOPILOT": "aris_autopilot_v01.py",
    "TERMUX_CONTROL": "aris_termux_control_v01.py",
    "FOREMAN": "aris_foreman_v01.py",
}

def log(message):
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {message}\n")

def process_online(script):
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                text = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
                if script in text:
                    return True
            except (OSError, PermissionError):
                pass
    except OSError:
        pass
    return False

def status():
    return {name: ("ONLINE" if process_online(script) else "OFFLINE") for name, script in PROCESSES.items()}

def analyze():
    proc = subprocess.run([sys.executable, "aris_analyze_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout)[-2000:]}
    return json.loads(proc.stdout)

def write_result(task_id, payload):
    path = RESULTS / f"{task_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

def reject(task_file, reason):
    task_id = task_file.stem
    payload = {"ok": False, "task_id": task_id, "finished_at": datetime.now().isoformat(timespec="seconds"), "error": reason}
    write_result(task_id, payload)
    shutil.move(str(task_file), str(REJECTED / task_file.name))
    log(f"REJECTED | {task_id} | {reason}")

def execute(task_file):
    try:
        task = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as exc:
        reject(task_file, f"INVALID JSON: {type(exc).__name__}")
        return
    task_id = task.get("task_id")
    if not task_id or task_id != task_file.stem:
        reject(task_file, "INVALID TASK ID")
        return
    if task.get("real_trading") is not False:
        reject(task_file, "REAL TRADING FLAG REJECTED")
        return
    action = str(task.get("action", "")).strip().upper()
    if action not in ALLOWED_ACTIONS:
        reject(task_file, "ACTION NOT ALLOWED")
        return
    result = status() if action == "STATUS" else analyze()
    payload = {
        "ok": True,
        "task_id": task_id,
        "action": action,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "result": result,
        "real_trading": False,
    }
    write_result(task_id, payload)
    shutil.move(str(task_file), str(DONE / task_file.name))
    log(f"DONE | {task_id} | {action}")

def cross_exchange_supervisor():
    while True:
        try:
            from aris_cross_exchange_v01 import run_forever
            run_forever()
        except Exception as exc:
            log(f"CROSS EXCHANGE ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)


def cross_paper_ledger_supervisor():
    while True:
        try:
            from aris_cross_paper_ledger_v01 import run_forever
            run_forever()
        except Exception as exc:
            log(f"CROSS PAPER LEDGER ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)


def cross_inventory_ledger_supervisor():
    while True:
        try:
            from aris_cross_inventory_ledger_v01 import run_forever
            run_forever()
        except Exception as exc:
            log(f"CROSS INVENTORY LEDGER ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)


def cross_inventory_low_risk_supervisor():
    while True:
        try:
            from aris_cross_inventory_low_risk_v01 import run_forever
            run_forever()
        except Exception as exc:
            log(f"CROSS INVENTORY LOW RISK ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)


def cycle_metrics_supervisor():
    while True:
        try:
            from aris_cycle_metrics_v02 import run_forever
            run_forever()
        except Exception as exc:
            log(f"CYCLE METRICS ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)


def operational_report_supervisor():
    while True:
        try:
            from aris_operational_report_v01 import run_forever
            run_forever()
        except Exception as exc:
            log(f"OPERATIONAL REPORT ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)


def paper_ledger_supervisor():
    while True:
        try:
            from aris_paper_ledger_v01 import run_forever
            run_forever()
        except Exception as exc:
            log(f"PAPER LEDGER ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)


def cycle_collector_supervisor():
    while True:
        try:
            from aris_cycle_collector_v01 import run_forever
            run_forever()
        except Exception as exc:
            log(f"CYCLE COLLECTOR ERROR | {type(exc).__name__}: {exc}")
            time.sleep(10)

print(f"A.R.I.S. WORKER v{VERSION} | SAFE QUEUE | SHELL DISABLED | REAL TRADING DISABLED")
log(f"WORKER STARTED | v{VERSION} | SAFE MODE")
threading.Thread(target=cycle_collector_supervisor, daemon=True, name="cycle-collector-supervisor").start()
threading.Thread(target=paper_ledger_supervisor, daemon=True, name="paper-ledger-supervisor").start()
threading.Thread(target=operational_report_supervisor, daemon=True, name="operational-report-supervisor").start()
threading.Thread(target=cycle_metrics_supervisor, daemon=True, name="cycle-metrics-supervisor").start()
threading.Thread(target=cross_exchange_supervisor, daemon=True, name="cross-exchange-supervisor").start()
threading.Thread(target=cross_paper_ledger_supervisor, daemon=True, name="cross-paper-ledger-supervisor").start()
log("STANDARD INVENTORY MODEL DISABLED | LOW RISK MODEL PRIMARY")
threading.Thread(target=cross_inventory_low_risk_supervisor, daemon=True, name="cross-inventory-low-risk-supervisor").start()
try:
    while True:
        for task_file in sorted(PENDING.glob("*.json")):
            execute(task_file)
        time.sleep(CHECK_EVERY)
except KeyboardInterrupt:
    log("WORKER STOPPED BY USER")
