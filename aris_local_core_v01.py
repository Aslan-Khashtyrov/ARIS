from pathlib import Path
from datetime import datetime
import json

VERSION="0.1"
ROOT=Path.home()/"Arbitrage"
JOURNAL=ROOT/"journal"
STATS=JOURNAL/"session_stats.json"
HISTORY=JOURNAL/"multi_history_v03.csv"

def info(path):
    try:
        s=path.stat();return {"exists":True,"size":s.st_size,"age_seconds":round(datetime.now().timestamp()-s.st_mtime,1)}
    except OSError:return {"exists":False,"size":None,"age_seconds":None}

def read_stats():
    try:return json.loads(STATS.read_text(encoding="utf-8"))
    except Exception:return None

def decide(ctx):
    h=ctx["history"];s=ctx["stats_file"]
    if not s["exists"] or (s["age_seconds"] is not None and s["age_seconds"]>180):return "STATUS"
    if h["exists"] and h["size"] and h["size"]>0:return "ANALYZE"
    return "STATUS"

ctx={"timestamp":datetime.now().isoformat(timespec="seconds"),"real_trading":False,"shell_access":False,"stats_file":info(STATS),"history":info(HISTORY),"stats":read_stats()}
print("="*64)
print(f"A.R.I.S. LOCAL CORE v{VERSION}")
print("API COST       : NONE")
print("SHELL          : DISABLED")
print("REAL TRADING   : DISABLED")
print("DECISION       :",decide(ctx))
print("="*64)
print(json.dumps(ctx,ensure_ascii=False,indent=2))
