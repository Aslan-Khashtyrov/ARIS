from pathlib import Path
from datetime import datetime
import csv
import json
import subprocess
import sys

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
CONFIG = ROOT / "aris_config_v01.json"
P2P_HISTORY = JOURNAL / "p2p_history_v01.csv"

def run_json(script):
    proc = subprocess.run([sys.executable, script], cwd=ROOT, text=True, capture_output=True, timeout=90)
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout)[-2000:]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid_json_output"}

def p2p_summary(config):
    providers = config["p2p"]["providers"]
    enabled = [name for name, item in providers.items() if item.get("enabled")]
    rows = []
    if P2P_HISTORY.exists():
        with P2P_HISTORY.open(newline="", encoding="utf-8", errors="replace") as handle:
            rows = list(csv.DictReader(handle))
    return {
        "ok": True,
        "status": "COLLECTING" if enabled else "WAITING_FOR_OFFICIAL_PROVIDER_ACCESS",
        "fiat": config["p2p"]["fiat"],
        "assets": config["p2p"]["assets"],
        "enabled_providers": enabled,
        "quotes_collected": len(rows),
        "real_trading": False,
    }

def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    spot = run_json("aris_analyze_v01.py")
    p2p = p2p_summary(config)
    spot_positive = spot.get("taker_taker_positive_samples", 0) if spot.get("ok") else 0
    p2p_ready = bool(p2p["enabled_providers"] and p2p["quotes_collected"])
    decision = "NO_ACTION"
    reasons = []
    if not spot.get("ok"):
        reasons.append("spot_analysis_unavailable")
    elif spot_positive == 0:
        reasons.append("no_positive_spot_taker_taker_samples")
    if not p2p_ready:
        reasons.append("p2p_official_data_not_connected")
    report = {
        "ok": bool(spot.get("ok") and p2p.get("ok")),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "MONITORING_AND_PAPER_ONLY",
        "real_trading": False,
        "decision": decision,
        "reasons": reasons,
        "spot": spot,
        "p2p": p2p,
        "safety": config["safety"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    sys.exit(main())
