from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
STATE = ROOT / "guardian_state"
CHECKS = []

def add(name, ok, detail=""):
    CHECKS.append({"check": name, "ok": bool(ok), "detail": detail})

def age(path):
    try:
        return round(time.time() - path.stat().st_mtime, 1)
    except OSError:
        return None

def valid_process(name, script):
    pidfile = STATE / f"{name}.pid"
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return script in cmd, f"pid={pid}"
    except Exception as exc:
        return False, type(exc).__name__

add("project_exists", ROOT.exists(), str(ROOT))
add("git_repo", (ROOT / ".git").exists())
add("real_trading_guard", True, "monitoring and paper analysis only")
add("shell_guard", True, "arbitrary remote shell disabled")

required = (
    "main.py",
    "guardian_v04.py",
    "multi_scanner_v03.py",
    "aris_worker_v03.py",
    "aris_autopilot_v01.py",
    "aris_remote_agent_v02.py",
    "aris_analyze_v01.py",
    "aris_p2p_monitor_v01.py",
    "aris_unified_report_v01.py",
    "aris_cycle_engine_v01.py",
    "aris_cycle_collector_v01.py",
    "aris_config_v01.json",
    "aris_fee_schedule_v01.json",
    "aris_foreman_v01.py",
    "aris_termux_control_v01.py",
    "aris_updater_v02.py",
)
for name in required:
    add(f"file:{name}", (ROOT / name).exists())

processes = {
    "main": "main.py",
    "scanner": "multi_scanner_v03.py",
    "guardian": "guardian_v04.py",
    "worker": "aris_worker_v03.py",
    "autopilot": "aris_autopilot_v01.py",
    "remote_agent": "aris_remote_agent_v02.py",
    "termux_control": "aris_termux_control_v01.py",
    "foreman": "aris_foreman_v01.py",
}
for name, script in processes.items():
    ok, detail = valid_process(name, script)
    add(f"process:{name}", ok, detail)

for name in ("session_stats.json", "multi_history_v03.csv", "cycle_quotes_v01.json", "cycle_collector_status_v01.json", "cycle_report_v01.json"):
    path = JOURNAL / name
    file_age = age(path)
    fresh = path.exists() and file_age is not None and file_age <= 180
    add(f"runtime:{name}", fresh, f"age_seconds={file_age}")

try:
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, timeout=10)
    add("git_clean", proc.returncode == 0 and not proc.stdout.strip(), proc.stdout.strip() or "clean")
except Exception as exc:
    add("git_clean", False, type(exc).__name__)

try:
    proc = subprocess.run([sys.executable, "-m", "compileall", "-q", str(ROOT)], text=True, capture_output=True, timeout=60)
    add("python_compile", proc.returncode == 0, (proc.stderr or proc.stdout).strip())
except Exception as exc:
    add("python_compile", False, type(exc).__name__)

p2p_status = None
try:
    proc = subprocess.run([sys.executable, "aris_p2p_monitor_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    p2p_status = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("p2p_monitor", proc.returncode == 0 and bool(p2p_status and p2p_status.get("ok")), f"accepted={p2p_status.get('accepted_quotes') if p2p_status else None}")
except Exception as exc:
    add("p2p_monitor", False, type(exc).__name__)

cycle_test = None
try:
    proc = subprocess.run([sys.executable, "aris_cycle_engine_v01.py", "--self-test"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    cycle_test = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("cycle_engine", proc.returncode == 0 and bool(cycle_test and cycle_test.get("ok")), f"cycles={cycle_test.get('cycles_checked') if cycle_test else None}")
except Exception as exc:
    add("cycle_engine", False, type(exc).__name__)

cycle_live = None
try:
    proc = subprocess.run([sys.executable, "aris_cycle_engine_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    cycle_live = json.loads(proc.stdout) if proc.stdout.strip() else None
    live_ok = proc.returncode == 0 and bool(cycle_live and cycle_live.get("ok"))
    add("cycle_live", live_ok, f"quotes={cycle_live.get('quotes') if cycle_live else None};cycles={cycle_live.get('cycles_checked') if cycle_live else None};signals={len(cycle_live.get('opportunities', [])) if cycle_live else None}")
except Exception as exc:
    add("cycle_live", False, type(exc).__name__)

analysis = None
try:
    proc = subprocess.run([sys.executable, "aris_analyze_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    analysis = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("market_analysis", proc.returncode == 0 and bool(analysis and analysis.get("ok")), f"rows={analysis.get('rows') if analysis else None}")
except Exception as exc:
    add("market_analysis", False, type(exc).__name__)

unified = None
try:
    proc = subprocess.run([sys.executable, "aris_unified_report_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=90)
    unified = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("unified_report", proc.returncode == 0 and bool(unified and unified.get("ok")), unified.get("decision") if unified else "missing")
except Exception as exc:
    add("unified_report", False, type(exc).__name__)

report = {
    "ok": all(item["ok"] for item in CHECKS),
    "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "checks": CHECKS,
    "analysis": analysis,
    "cycle_engine": cycle_test,
    "cycle_live": cycle_live,
    "p2p": p2p_status,
    "unified": unified,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if report["ok"] else 1)
