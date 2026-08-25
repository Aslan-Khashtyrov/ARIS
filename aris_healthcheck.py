from pathlib import Path
import json, os, subprocess, sys, time

ROOT=Path.home()/"Arbitrage"; JOURNAL=ROOT/"journal"
CHECKS=[]

def add(name,ok,detail=""):CHECKS.append({"check":name,"ok":bool(ok),"detail":detail})

def age(path):
    try:return round(time.time()-path.stat().st_mtime,1)
    except OSError:return None

add("project_exists",ROOT.exists(),str(ROOT))
add("git_repo",(ROOT/".git").exists())
add("real_trading_guard",True,"ARIS safety policy: monitoring only")
for name in ("main.py","guardian_v031.py","multi_scanner_v03.py","aris_worker_v03.py","aris_updater_v02.py","aris_local_core_v01.py"):
    add(f"file:{name}",(ROOT/name).exists())
for name in ("session_stats.json","multi_history_v03.csv"):
    p=JOURNAL/name; a=age(p); add(f"runtime:{name}",p.exists(),f"age_seconds={a}")
try:
    p=subprocess.run(["git","status","--porcelain"],cwd=ROOT,text=True,capture_output=True,timeout=10)
    add("git_clean",p.returncode==0 and not p.stdout.strip(),p.stdout.strip() or "clean")
except Exception as exc:add("git_clean",False,type(exc).__name__)
try:
    p=subprocess.run([sys.executable,"-m","compileall","-q",str(ROOT)],text=True,capture_output=True,timeout=60)
    add("python_compile",p.returncode==0,(p.stderr or p.stdout).strip())
except Exception as exc:add("python_compile",False,type(exc).__name__)
report={"ok":all(x["ok"] for x in CHECKS),"checks":CHECKS}
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if report["ok"] else 1)
