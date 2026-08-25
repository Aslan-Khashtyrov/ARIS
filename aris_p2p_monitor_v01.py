from pathlib import Path
from datetime import datetime
import csv
import json
import sys

ROOT = Path.home() / "Arbitrage"
CONFIG = ROOT / "aris_config_v01.json"
JOURNAL = ROOT / "journal"
INBOX = JOURNAL / "p2p_quotes_inbox.json"
HISTORY = JOURNAL / "p2p_history_v01.csv"
STATUS = JOURNAL / "p2p_status_v01.json"
FIELDS = [
    "timestamp", "provider", "asset", "fiat", "side", "price",
    "min_amount", "max_amount", "payment_methods", "merchant",
    "completion_rate_percent", "completed_orders"
]

def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))

def validate(quote, config):
    required = ("provider", "asset", "fiat", "side", "price")
    missing = [name for name in required if quote.get(name) in (None, "")]
    if missing:
        return False, "missing:" + ",".join(missing)
    provider = str(quote["provider"]).lower()
    provider_cfg = config["p2p"]["providers"].get(provider)
    if not provider_cfg or not provider_cfg.get("enabled"):
        return False, f"provider_disabled:{provider}"
    if str(quote["asset"]).upper() not in config["p2p"]["assets"]:
        return False, "asset_not_allowed"
    if str(quote["fiat"]).upper() != config["p2p"]["fiat"]:
        return False, "fiat_not_allowed"
    if str(quote["side"]).upper() not in {"BUY", "SELL"}:
        return False, "invalid_side"
    try:
        if float(quote["price"]) <= 0:
            return False, "invalid_price"
    except (TypeError, ValueError):
        return False, "invalid_price"
    return True, "ok"

def append(rows):
    exists = HISTORY.exists()
    with HISTORY.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in FIELDS})

def main():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    config = load_config()
    accepted = []
    rejected = []
    if INBOX.exists():
        try:
            payload = json.loads(INBOX.read_text(encoding="utf-8"))
            quotes = payload if isinstance(payload, list) else payload.get("quotes", [])
        except Exception as exc:
            quotes = []
            rejected.append({"reason": f"invalid_inbox:{type(exc).__name__}"})
        for quote in quotes:
            ok, reason = validate(quote, config)
            if not ok:
                rejected.append({"provider": quote.get("provider"), "reason": reason})
                continue
            normalized = dict(quote)
            normalized["timestamp"] = quote.get("timestamp") or datetime.now().isoformat(timespec="seconds")
            normalized["provider"] = str(quote["provider"]).lower()
            normalized["asset"] = str(quote["asset"]).upper()
            normalized["fiat"] = str(quote["fiat"]).upper()
            normalized["side"] = str(quote["side"]).upper()
            normalized["payment_methods"] = ",".join(quote.get("payment_methods", [])) if isinstance(quote.get("payment_methods"), list) else quote.get("payment_methods", "")
            accepted.append(normalized)
    if accepted:
        append(accepted)
    report = {
        "ok": True,
        "time": datetime.now().isoformat(timespec="seconds"),
        "mode": "MONITORING_ONLY",
        "real_trading": False,
        "fiat": config["p2p"]["fiat"],
        "accepted_quotes": len(accepted),
        "rejected_quotes": len(rejected),
        "providers": config["p2p"]["providers"],
        "history_exists": HISTORY.exists(),
        "note": "Official provider access is required before live P2P ads can be ingested."
    }
    STATUS.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
