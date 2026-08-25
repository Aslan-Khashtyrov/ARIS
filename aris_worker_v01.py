from pathlib import Path
from datetime import datetime
import json
import os
import shutil

BASE = Path("aris_queue")
PENDING = BASE / "pending"
DONE = BASE / "done"
REJECTED = BASE / "rejected"
RESULTS = BASE / "results"

for folder in (PENDING, DONE, REJECTED, RESULTS):
    folder.mkdir(parents=True, exist_ok=True)

# Worker v0.1 intentionally supports STATUS only.
ALLOWED_ACTIONS = {"STATUS"}

PROCESS_NAMES = {
    "ARBITRAZHNIK": "main.py",
    "GUARDIAN": "guardian_v031.py",
    "MULTI_SCANNER": "multi_scanner_v02.py",
}


def process_online(name):
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue

            cmdline = Path("/proc") / pid / "cmdline"

            try:
                data = cmdline.read_bytes().replace(b"\x00", b" ")
                text = data.decode("utf-8", errors="ignore")
            except (OSError, PermissionError):
                continue

            if name in text:
                return True

    except OSError:
        pass

    return False


def get_status():
    result = {}

    for label, process_name in PROCESS_NAMES.items():
        result[label] = (
            "ONLINE"
            if process_online(process_name)
            else "OFFLINE"
        )

    result["WORKER"] = "ONLINE"

    return result


def write_result(task_id, payload):
    path = RESULTS / f"{task_id}.json"

    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return path


def reject(task_file, reason):
    task_id = task_file.stem

    payload = {
        "ok": False,
        "task_id": task_id,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "error": reason,
    }

    result_path = write_result(task_id, payload)

    shutil.move(
        str(task_file),
        str(REJECTED / task_file.name),
    )

    print("REJECTED :", task_id)
    print("REASON   :", reason)
    print("RESULT   :", result_path)


def execute_task(task_file):
    try:
        task = json.loads(
            task_file.read_text(encoding="utf-8")
        )
    except Exception as e:
        reject(task_file, f"INVALID JSON: {type(e).__name__}")
        return

    task_id = task.get("task_id")

    if not task_id or task_id != task_file.stem:
        reject(task_file, "INVALID TASK ID")
        return

    if task.get("real_trading") is not False:
        reject(task_file, "REAL TRADING FLAG REJECTED")
        return

    action = str(task.get("action", "")).upper()

    if action not in ALLOWED_ACTIONS:
        reject(task_file, "ACTION NOT ALLOWED")
        return

    if action == "STATUS":
        result = get_status()
    else:
        reject(task_file, "NO HANDLER")
        return

    payload = {
        "ok": True,
        "task_id": task_id,
        "action": action,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "result": result,
    }

    result_path = write_result(task_id, payload)

    shutil.move(
        str(task_file),
        str(DONE / task_file.name),
    )

    print("DONE     :", task_id)
    print("ACTION   :", action)
    print("RESULT   :", result_path)
    print(json.dumps(result, indent=2))


def main():
    print("=" * 60)
    print("A.R.I.S. WORKER v0.1")
    print("MODE         : SAFE")
    print("ALLOWED      : STATUS")
    print("SHELL        : DISABLED")
    print("REAL TRADING : DISABLED")
    print("=" * 60)

    tasks = sorted(PENDING.glob("*.json"))

    if not tasks:
        print("NO PENDING TASKS")
        return

    print("PENDING TASKS:", len(tasks))

    for task_file in tasks:
        execute_task(task_file)

    print("=" * 60)
    print("WORKER CYCLE COMPLETE")


if __name__ == "__main__":
    main()
