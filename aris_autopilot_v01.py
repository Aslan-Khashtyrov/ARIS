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
VERSION = "0.4"
CONTROL_HEARTBEAT = STATE / "termux_control_heartbeat.json"
CONTROL_MAX_HEARTBEAT_AGE = 90

# A live PID is not enough: feed threads can stall inside the worker.  Run the
# existing read-only healthcheck periodically and restart only after a fault is
# continuous for several minutes.  Cooldowns prevent restart storms during an
# exchange or network outage.
HEALTHCHECK = ROOT / "aris_healthcheck.py"
HEALTHCHECK_EVERY = 60
HEALTH_FAILURE_GRACE = 180
RESTART_COOLDOWN = 900
STOP_TIMEOUT = 10

COMPONENTS = {
    "main": "main.py",
    "scanner": "multi_scanner_v03.py",
    "guardian": "guardian_v04.py",
    "worker": "aris_worker_v03.py",
    "termux_control": "aris_termux_control_v01.py",
    "foreman": "aris_foreman_v01.py",
}

MAIN_HEALTH_CHECKS = {
    "runtime:session_stats.json",
    "runtime:multi_history_v03.csv",
}
# Coverage can briefly fall below the health threshold when otherwise healthy
# markets are quiet.  It remains visible in healthcheck, but is not itself a
# restart trigger.  Runtime freshness catches a stalled worker, while each
# exchange collector owns reconnect/fallback handling.
WORKER_HEALTH_CHECKS = {
    "runtime:cycle_quotes_v01.json",
    "runtime:cycle_collector_status_v01.json",
    "runtime:cycle_report_v01.json",
    "runtime:cross_exchange_report_v01.json",
    "runtime:cross_exchange_metrics_v01.json",
    "cross_exchange_live",
    "paper_ledger_live",
    "cycle_metrics_live",
    "cycle_engine",
    "cycle_live",
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


def stop_component(name, script, reason):
    pid = tracked_pid(name)
    if not valid_process(pid, script):
        return True
    try:
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + STOP_TIMEOUT
        while time.time() < deadline:
            if not valid_process(pid, script):
                log("stopped", component=name, pid=pid, reason=reason)
                return True
            time.sleep(0.5)
        log("stop_timeout", component=name, pid=pid, reason=reason)
        return False
    except ProcessLookupError:
        return True
    except Exception as exc:
        log("stop_failed", component=name, pid=pid, reason=reason,
            error=f"{type(exc).__name__}: {exc}")
        return False


def stop_stale_control(pid, age):
    try:
        os.kill(pid, signal.SIGTERM)
        log("stale_control_stopped", component="termux_control", pid=pid, heartbeat_age_seconds=age)
        time.sleep(2)
    except ProcessLookupError:
        pass
    except Exception as exc:
        log("stale_control_stop_failed", component="termux_control", pid=pid,
            error=f"{type(exc).__name__}: {exc}")


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


def run_healthcheck():
    if not HEALTHCHECK.exists():
        log("healthcheck_missing", path=str(HEALTHCHECK))
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(HEALTHCHECK), "--summary"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        payload = json.loads(result.stdout)
        checks = payload.get("checks", [])
        if not isinstance(checks, list):
            raise ValueError("checks is not a list")
        return {str(item.get("check")): item for item in checks if isinstance(item, dict)}
    except Exception as exc:
        log("healthcheck_failed", error=f"{type(exc).__name__}: {exc}")
        return None


def health_faults(checks, selected):
    faults = []
    for name in sorted(selected):
        item = checks.get(name)
        if item is not None and not bool(item.get("ok")):
            faults.append({"check": name, "detail": item.get("detail", "")})
    return faults


def supervise_health(component, faults, now_mono, unhealthy_since, last_restart):
    if not faults:
        if component in unhealthy_since:
            log("health_recovered", component=component)
            unhealthy_since.pop(component, None)
        return

    if component not in unhealthy_since:
        unhealthy_since[component] = now_mono
        log("health_degraded", component=component, faults=faults)
        return

    bad_for = now_mono - unhealthy_since[component]
    cooldown = now_mono - last_restart.get(component, 0.0)
    if bad_for < HEALTH_FAILURE_GRACE or cooldown < RESTART_COOLDOWN:
        return

    script = COMPONENTS[component]
    reason = "persistent_health_failure"
    log("health_restart_requested", component=component,
        unhealthy_seconds=round(bad_for, 1), faults=faults)
    if stop_component(component, script, reason) and start_component(component, script):
        last_restart[component] = now_mono
        unhealthy_since.pop(component, None)


log("started", version=VERSION, mode="monitoring_and_paper_only", real_trading=False,
    shell_access=False, health_watchdog=True)
next_healthcheck = 0.0
unhealthy_since = {}
last_restart = {}

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

    now_mono = time.monotonic()
    if now_mono >= next_healthcheck:
        next_healthcheck = now_mono + HEALTHCHECK_EVERY
        checks = run_healthcheck()
        if checks is not None:
            supervise_health("main", health_faults(checks, MAIN_HEALTH_CHECKS),
                             now_mono, unhealthy_since, last_restart)
            supervise_health("worker", health_faults(checks, WORKER_HEALTH_CHECKS),
                             now_mono, unhealthy_since, last_restart)

    time.sleep(CHECK_EVERY)
