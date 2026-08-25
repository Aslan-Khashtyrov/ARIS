from pathlib import Path
from datetime import datetime
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path.home() / "Arbitrage"
STATE = ROOT / "guardian_state"
JOURNAL = ROOT / "journal"
COMMAND_PATH = "remote/command.json"
REPORT_PATH = ROOT / "remote" / "device_status.json"
LAST_ID = STATE / "remote_last_id"
RESULT = JOURNAL / "remote_last_result.json"
AUDIT = JOURNAL / "remote_agent_audit.log"
POLL_EVERY = 30

ALLOWED = {"PING", "STATUS", "HEALTHCHECK", "BACKUP", "RESTART_COMPONENTS"}
COMPONENTS = {
    "main": "main.py",
    "scanner": "multi_scanner_v03.py",
    "guardian": "guardian_v04.py",
    "worker": "aris_worker_v03.py",
    "autopilot": "aris_autopilot_v01.py",
}

STATE.mkdir(parents=True, exist_ok=True)
JOURNAL.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

def audit(event, **fields):
    record = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, **fields}
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

def run(args, timeout=60):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)

def current_status():
    result = {}
    for name, script in COMPONENTS.items():
        pidfile = STATE / f"{name}.pid"
        try:
            pid = int(pidfile.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            result[name] = {"online": script in cmd, "pid": pid, "script": script}
        except Exception:
            result[name] = {"online": False, "pid": None, "script": script}
    return result

def execute(action):
    if action == "PING":
        return {"pong": True, "components": current_status()}
    if action == "STATUS":
        return current_status()
    if action == "HEALTHCHECK":
        proc = run([sys.executable, "aris_healthcheck.py"])
        return {"returncode": proc.returncode, "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-4000:]}
    if action == "BACKUP":
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = ROOT / "backups" / f"remote_{stamp}"
        target.mkdir(parents=True)
        copied = []
        for name in ["main.py", "multi_scanner_v03.py", "guardian_v04.py", "aris_worker_v03.py"]:
            source = ROOT / name
            if source.exists():
                shutil.copy2(source, target / name)
                copied.append(name)
        return {"path": str(target), "files": copied}
    if action == "RESTART_COMPONENTS":
        stopped = []
        for name in ("worker", "guardian", "scanner", "main"):
            pidfile = STATE / f"{name}.pid"
            try:
                pid = int(pidfile.read_text(encoding="utf-8").strip())
                os.kill(pid, 15)
                stopped.append({"name": name, "pid": pid})
            except Exception:
                pass
        return {"stopped": stopped, "note": "autopilot will restart missing components"}
    raise ValueError("action not allowed")

def publish(payload):
    merge = run(["git", "merge", "--ff-only", "origin/main"], timeout=45)
    if merge.returncode != 0:
        raise RuntimeError("cannot fast-forward before report: " + merge.stderr[-300:])
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    add = run(["git", "add", "remote/device_status.json"])
    if add.returncode != 0:
        raise RuntimeError("git add failed: " + add.stderr[-300:])
    commit = run(["git", "commit", "-m", f"ARIS device report {payload.get('id', 'unknown')}"])
    if commit.returncode != 0 and "nothing to commit" not in (commit.stdout + commit.stderr).lower():
        raise RuntimeError("git commit failed: " + commit.stderr[-300:])
    push = run(["git", "push", "origin", "HEAD:main"], timeout=60)
    if push.returncode != 0:
        rebase = run(["git", "pull", "--rebase", "origin", "main"], timeout=60)
        if rebase.returncode != 0:
            raise RuntimeError("git rebase failed: " + rebase.stderr[-300:])
        push = run(["git", "push", "origin", "HEAD:main"], timeout=60)
        if push.returncode != 0:
            raise RuntimeError("git push failed: " + push.stderr[-300:])

audit("started", version="0.2", allowed=sorted(ALLOWED), real_trading=False, shell_access=False)
while True:
    try:
        fetch = run(["git", "fetch", "--quiet", "origin", "main"], timeout=45)
        if fetch.returncode != 0:
            audit("fetch_error", detail=fetch.stderr[-500:])
            time.sleep(POLL_EVERY)
            continue
        shown = run(["git", "show", f"origin/main:{COMMAND_PATH}"])
        if shown.returncode != 0:
            time.sleep(POLL_EVERY)
            continue
        command = json.loads(shown.stdout)
        command_id = str(command.get("id", "")).strip()
        action = str(command.get("action", "")).strip().upper()
        previous = LAST_ID.read_text(encoding="utf-8").strip() if LAST_ID.exists() else ""
        if not command_id or command_id == previous:
            time.sleep(POLL_EVERY)
            continue
        if action not in ALLOWED:
            payload = {"ok": False, "id": command_id, "action": action, "time": datetime.now().isoformat(timespec="seconds"), "error": "ACTION_NOT_ALLOWED"}
            audit("denied", id=command_id, action=action)
        else:
            try:
                payload = {"ok": True, "id": command_id, "action": action, "time": datetime.now().isoformat(timespec="seconds"), "result": execute(action)}
                audit("executed", id=command_id, action=action)
            except Exception as exc:
                payload = {"ok": False, "id": command_id, "action": action, "time": datetime.now().isoformat(timespec="seconds"), "error": f"{type(exc).__name__}: {exc}"}
                audit("error", id=command_id, action=action, detail=payload["error"])
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        LAST_ID.write_text(command_id, encoding="utf-8")
        try:
            publish(payload)
            audit("published", id=command_id, action=action)
        except Exception as exc:
            audit("publish_error", id=command_id, detail=f"{type(exc).__name__}: {exc}")
    except Exception as exc:
        audit("loop_error", detail=f"{type(exc).__name__}: {exc}")
    time.sleep(POLL_EVERY)
