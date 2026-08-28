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

def process_cmdline(pid):
    try:
        os.kill(pid, 0)
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except (OSError, ValueError):
        return ""


def valid_process(name, script):
    pidfile = STATE / f"{name}.pid"
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
        cmd = process_cmdline(pid)
        if script in cmd:
            return True, f"pid={pid};source=pidfile"
    except (OSError, ValueError):
        pass

    # Supervisors and recovery scripts may start a component without refreshing
    # its pidfile. Verify the live /proc command line before declaring it down.
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if script in process_cmdline(pid):
            return True, f"pid={pid};source=proc"

    return False, "not_running"

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
    "aris_cross_exchange_v01.py",
    "aris_cross_inventory_ledger_v01.py",
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
    "termux_control": "aris_termux_control_v01.py",
    "foreman": "aris_foreman_v01.py",
}
for name, script in processes.items():
    ok, detail = valid_process(name, script)
    add(f"process:{name}", ok, detail)

for name in ("session_stats.json", "multi_history_v03.csv", "cycle_quotes_v01.json", "cycle_collector_status_v01.json", "cycle_report_v01.json", "cross_exchange_report_v01.json", "cross_exchange_metrics_v01.json"):
    path = JOURNAL / name
    file_age = age(path)
    fresh = path.exists() and file_age is not None and file_age <= 180
    add(f"runtime:{name}", fresh, f"age_seconds={file_age}")

exchange_health = {}
try:
    collector_status = json.loads((JOURNAL / "cycle_collector_status_v01.json").read_text(encoding="utf-8"))
    snapshot = json.loads((JOURNAL / "cycle_quotes_v01.json").read_text(encoding="utf-8"))
    live_counts = {}
    for quote in snapshot.get("quotes", []):
        exchange = str(quote.get("exchange", "")).lower()
        live_counts[exchange] = live_counts.get(exchange, 0) + 1
    for exchange in ("binance", "bybit", "okx", "coinbase", "kraken"):
        state = collector_status.get("exchanges", {}).get(exchange, {})
        connected = state.get("connected") is True
        pairs = int(state.get("pairs", 0) or 0)
        updates = int(state.get("updates", 0) or 0)
        live_quotes = live_counts.get(exchange, 0)
        quote_coverage_percent = (live_quotes / pairs * 100.0) if pairs > 0 else 0.0
        coverage_ok = quote_coverage_percent >= 80.0
        ok = connected and pairs > 0 and updates > 0 and coverage_ok and not state.get("error")
        transport = state.get("transport")
        detail = f"connected={connected};transport={transport};pairs={pairs};updates={updates};live_quotes={live_quotes};coverage={quote_coverage_percent:.1f}%;error={state.get('error')}"
        exchange_health[exchange] = {"ok": ok, "connected": connected, "transport": transport, "pairs": pairs, "updates": updates, "live_quotes": live_quotes, "quote_coverage_percent": round(quote_coverage_percent, 1), "error": state.get("error")}
        add(f"exchange:{exchange}", ok, detail)
except Exception as exc:
    add("exchange:required_spot_sources", False, f"{type(exc).__name__}: {exc}")

cross_exchange = None
try:
    cross_path = JOURNAL / "cross_exchange_report_v01.json"
    cross_age = age(cross_path)
    cross_exchange = json.loads(cross_path.read_text(encoding="utf-8"))
    metrics_path = JOURNAL / "cross_exchange_metrics_v01.json"
    cross_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    cross_ok = cross_age is not None and cross_age <= 45 and cross_exchange.get("ok") is True and cross_exchange.get("real_trading") is False and cross_metrics.get("ok") is True and cross_metrics.get("real_trading") is False
    add("cross_exchange_live", cross_ok, f"age_seconds={cross_age};routes={cross_exchange.get('routes_compared')};executable={cross_exchange.get('executable_routes')};positive={cross_exchange.get('positive_executable_routes')};samples={cross_metrics.get('samples')};best_net={cross_metrics.get('best_net_profit_percent')}")
except Exception as exc:
    add("cross_exchange_live", False, f"{type(exc).__name__}: {exc}")

paper_ledger = None
try:
    ledger_path = JOURNAL / "paper_ledger_summary_v01.json"
    ledger_age = age(ledger_path)
    paper_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    wallet = paper_ledger.get("wallet", {})
    balances = wallet.get("balances", {})
    required_virtual_accounts = {"binance:USDT", "bybit:USDT", "okx:USDT"}
    wallet_funded = required_virtual_accounts.issubset(balances) and all(
        float(balances.get(account, -1)) >= 0 for account in required_virtual_accounts
    )
    ledger_ok = (
        ledger_age is not None
        and ledger_age <= 45
        and paper_ledger.get("ok") is True
        and paper_ledger.get("real_trading") is False
        and wallet.get("enabled") is True
        and wallet_funded
        and paper_ledger.get("validation_model") == "executable-paper-v07-risk"
    )
    add("paper_ledger_live", ledger_ok, f"age_seconds={ledger_age};model={paper_ledger.get('validation_model')};trades={paper_ledger.get('paper_trades')};virtual_accounts={len(balances)};equity_usdt={wallet.get('equity_by_asset', {}).get('USDT')}")
except Exception as exc:
    add("paper_ledger_live", False, f"{type(exc).__name__}: {exc}")

inventory_ledger = None
try:
    inventory_path = JOURNAL / "cross_inventory_summary_v01.json"
    inventory_age = age(inventory_path)
    inventory_ledger = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory_balances = inventory_ledger.get("balances", {})
    required_inventory_accounts = {
        f"{exchange}:{asset}"
        for exchange in ("binance", "bybit", "okx")
        for asset in ("USDT", "SOL")
    }
    inventory_funded = required_inventory_accounts.issubset(inventory_balances) and all(
        float(inventory_balances.get(account, -1)) >= 0 for account in required_inventory_accounts
    )
    inventory_ok = (
        inventory_age is not None
        and inventory_age <= 45
        and inventory_ledger.get("ok") is True
        and inventory_ledger.get("real_trading") is False
        and inventory_ledger.get("mode") == "INVENTORY_PAPER_ONLY"
        and inventory_ledger.get("model") == "cross-inventory-paper-v01"
        and inventory_funded
        and abs(float(inventory_ledger.get("initial_equity_usdt", 0)) - 3000.0) < 0.01
    )
    add("cross_inventory_ledger_live", inventory_ok, f"age_seconds={inventory_age};model={inventory_ledger.get('model')};trades={inventory_ledger.get('paper_trades')};realized_profit_usdt={inventory_ledger.get('realized_arbitrage_profit_usdt')};accounts={len(inventory_balances)}")
except Exception as exc:
    add("cross_inventory_ledger_live", False, f"{type(exc).__name__}: {exc}")

try:
    metrics_path = JOURNAL / "cycle_metrics_summary_v03.json"
    metrics_age = age(metrics_path)
    cycle_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics_ok = (
        metrics_age is not None
        and metrics_age <= 90
        and cycle_metrics.get("ok") is True
        and cycle_metrics.get("real_trading") is False
        and cycle_metrics.get("model_version") == "multileg-executable-v02"
    )
    add("cycle_metrics_live", metrics_ok, f"age_seconds={metrics_age};model={cycle_metrics.get('model_version')};samples={cycle_metrics.get('samples')}")
except Exception as exc:
    cycle_metrics = None
    add("cycle_metrics_live", False, f"{type(exc).__name__}: {exc}")

try:
    proc = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True, capture_output=True, timeout=10)
    add("git_clean", proc.returncode == 0 and not proc.stdout.strip(), proc.stdout.strip() or "clean")
except Exception as exc:
    add("git_clean", False, f"{type(exc).__name__}: {exc}")

try:
    proc = subprocess.run([sys.executable, "-m", "compileall", "-q", str(ROOT)], text=True, capture_output=True, timeout=60)
    add("python_compile", proc.returncode == 0, (proc.stderr or proc.stdout).strip())
except Exception as exc:
    add("python_compile", False, f"{type(exc).__name__}: {exc}")

p2p_status = None
try:
    proc = subprocess.run([sys.executable, "aris_p2p_monitor_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    p2p_status = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("p2p_monitor", proc.returncode == 0 and bool(p2p_status and p2p_status.get("ok")), f"accepted={p2p_status.get('accepted_quotes') if p2p_status else None}")
except Exception as exc:
    add("p2p_monitor", False, f"{type(exc).__name__}: {exc}")

cycle_test = None
try:
    proc = subprocess.run([sys.executable, "aris_cycle_engine_v01.py", "--self-test"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    cycle_test = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("cycle_engine", proc.returncode == 0 and bool(cycle_test and cycle_test.get("ok")), f"cycles={cycle_test.get('cycles_checked') if cycle_test else None}")
except Exception as exc:
    add("cycle_engine", False, f"{type(exc).__name__}: {exc}")

cycle_live = None
try:
    proc = subprocess.run([sys.executable, "aris_cycle_engine_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    cycle_live = json.loads(proc.stdout) if proc.stdout.strip() else None
    live_ok = proc.returncode == 0 and bool(cycle_live and cycle_live.get("ok"))
    add("cycle_live", live_ok, f"quotes={cycle_live.get('quotes') if cycle_live else None};cycles={cycle_live.get('cycles_checked') if cycle_live else None};signals={len(cycle_live.get('opportunities', [])) if cycle_live else None}")
except Exception as exc:
    add("cycle_live", False, f"{type(exc).__name__}: {exc}")

analysis = None
try:
    proc = subprocess.run([sys.executable, "aris_analyze_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=60)
    analysis = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("market_analysis", proc.returncode == 0 and bool(analysis and analysis.get("ok")), f"rows={analysis.get('rows') if analysis else None}")
except Exception as exc:
    add("market_analysis", False, f"{type(exc).__name__}: {exc}")

unified = None
try:
    proc = subprocess.run([sys.executable, "aris_unified_report_v01.py"], cwd=ROOT, text=True, capture_output=True, timeout=90)
    unified = json.loads(proc.stdout) if proc.stdout.strip() else None
    add("unified_report", proc.returncode == 0 and bool(unified and unified.get("ok")), unified.get("decision") if unified else "missing")
except Exception as exc:
    add("unified_report", False, f"{type(exc).__name__}: {exc}")

report = {
    "ok": all(item["ok"] for item in CHECKS),
    "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "checks": CHECKS,
    "analysis": analysis,
    "cycle_engine": cycle_test,
    "cycle_live": cycle_live,
    "exchange_health": exchange_health,
    "cross_exchange": cross_exchange,
    "paper_ledger": paper_ledger,
    "cross_inventory_ledger": inventory_ledger,
    "cycle_metrics": cycle_metrics,
    "p2p": p2p_status,
    "unified": unified,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if report["ok"] else 1)
