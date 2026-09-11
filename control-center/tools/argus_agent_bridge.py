#!/usr/bin/env python3
import json, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST, PORT = "127.0.0.1", 8765
WORKSPACE = Path("/data/data/com.termux/files/home/Arbitrage-control-center/control-center").resolve()
HERMES = Path.home() / ".hermes/hermes-agent/venv/bin/hermes"
MAX_PROMPT, MAX_OUTPUT = 16000, 1000000
DENY = ("api_key", "apikey", ".env", "secret", "password", "wallet", "withdraw", "deposit", "real_trading=true")

def guarded_prompt(value):
    low = value.lower()
    if any(word in low for word in DENY):
        raise ValueError("argus_blocked")
    return ("Project One guarded read-only task. Never reveal credentials, tokens, API keys or secrets. "
            "Do not perform financial actions or real trading. Do not modify files or processes. "
            "Work only with the Project One workspace.\n\nUSER TASK:\n" + value)

def run_agent(agent, prompt):
    safe = guarded_prompt(prompt)
    if agent == "codex":
        cmd = ["proot-distro", "login", "ubuntu", "--", "bash", "-lc",
               'cd "$1" && codex exec -s read-only --ephemeral --color never -', "bridge", str(WORKSPACE)]
        result = subprocess.run(cmd, input=safe, text=True, capture_output=True, timeout=180)
    elif agent == "hermes":
        if not HERMES.is_file(): raise RuntimeError("hermes_unavailable")
        cmd = [str(HERMES), "chat", "--oneshot", "--quiet", "--safe-mode", "--query-file", "-"]
        result = subprocess.run(cmd, input=safe, text=True, capture_output=True, cwd=WORKSPACE, timeout=180)
    else: raise ValueError("agent_blocked")
    text = (result.stdout or "").strip()[-MAX_OUTPUT:]
    if result.returncode != 0 and not text: raise RuntimeError("agent_failed")
    return text

class Handler(BaseHTTPRequestHandler):
    server_version = "ProjectOneArgus/1"
    def log_message(self, *_): pass
    def send_json(self, code, body):
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "http://localhost")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers(); self.wfile.write(raw)
    def do_OPTIONS(self):
        if self.headers.get("Origin") != "http://localhost": return self.send_json(403, {"ok": False})
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://localhost")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()
    def do_GET(self):
        if self.path != "/health": return self.send_json(404, {"ok": False})
        self.send_json(200, {"ok": True, "mode": "guarded-read-only", "agents": ["codex", "hermes"]})
    def do_POST(self):
        if self.path != "/v1/agent": return self.send_json(404, {"ok": False})
        if self.headers.get("Origin") not in ("http://localhost", None): return self.send_json(403, {"ok": False, "error": "origin_blocked"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 2 or size > MAX_PROMPT + 1024: raise ValueError("request_invalid")
            data = json.loads(self.rfile.read(size))
            prompt = str(data.get("prompt", "")).strip(); agent = str(data.get("agent", ""))
            if not prompt or len(prompt) > MAX_PROMPT: raise ValueError("prompt_invalid")
            self.send_json(200, {"ok": True, "agent": agent, "text": run_agent(agent, prompt)})
        except ValueError as exc: self.send_json(400, {"ok": False, "error": str(exc)})
        except subprocess.TimeoutExpired: self.send_json(504, {"ok": False, "error": "agent_timeout"})
        except Exception: self.send_json(500, {"ok": False, "error": "agent_failed"})

if __name__ == "__main__":
    print(f"Project One Argus bridge: http://{HOST}:{PORT} (guarded read-only)", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
