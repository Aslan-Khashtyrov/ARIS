from pathlib import Path
from datetime import datetime
import json,time

VERSION="0.4";ROOT=Path.home()/"Arbitrage";JOURNAL=ROOT/"journal";JOURNAL.mkdir(parents=True,exist_ok=True)
STATS=JOURNAL/"session_stats.json";HISTORY=JOURNAL/"multi_history_v03.csv";EVENTS=JOURNAL/"events.log";LOG=JOURNAL/"guardian_v04.log"
CHECK_EVERY=10;DEGRADED_AFTER=180;HANG_AFTER=420

def age(p):
    try:return time.time()-p.stat().st_mtime
    except OSError:return None

def stats():
    try:return json.loads(STATS.read_text(encoding="utf-8"))
    except Exception:return {}

def last_event():
    try:
        lines=EVENTS.read_text(encoding="utf-8",errors="replace").splitlines();return lines[-1] if lines else "none"
    except Exception:return "unavailable"

def log(msg):
    with LOG.open("a",encoding="utf-8") as f:f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}\n")

def fmt(a):return "missing" if a is None else f"{a:.0f}s"

print(f"ARBITRAGE GUARDIAN v{VERSION} | OBSERVE ONLY | AUTO-RESTART DISABLED")
state="STARTING";problem_since=None;start_cycles=None
while True:
    s=stats();cycles=s.get("cycles");sa=age(STATS);ha=age(HISTORY)
    stale=sa is None or ha is None or sa>=DEGRADED_AFTER or ha>=DEGRADED_AFTER
    if not stale:new="OK"
    else:
        if problem_since is None:problem_since=time.time();start_cycles=cycles
        moved=cycles is not None and start_cycles is not None and cycles>start_cycles
        new="POSSIBLE_HANG" if time.time()-problem_since>=HANG_AFTER and not moved else "NETWORK_DEGRADED"
    if new!=state:
        if new=="OK" and problem_since is not None:log(f"RECOVERED | previous={state} | duration={int(time.time()-problem_since)}s")
        log(f"STATE {state}->{new} | cycles={cycles} | stats_age={fmt(sa)} | history_age={fmt(ha)} | last_event={last_event()}")
        state=new
        if state=="OK":problem_since=None;start_cycles=None
    now=datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {state} | cycles={cycles} | stats={fmt(sa)} | history={fmt(ha)}")
    time.sleep(CHECK_EVERY)
