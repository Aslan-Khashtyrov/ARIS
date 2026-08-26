#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

VERSION = "0.4"
HOME = Path.home().resolve()
ROOT = (HOME / "Arbitrage").resolve()
STATE = ROOT / "guardian_state"
JOURNAL = ROOT / "journal"
COMMAND_PATH = "remote/termux_command.json"
REPORT_PATH = ROOT / "remote" / "termux_status.json"
LAST_ID = STATE / "termux_control_last_id"
AUDIT = JOURNAL / "termux_control_audit.jsonl"
POLL_EVERY = 20
MAX_OUTPUT = 48_000
MAX_READ = 128_000
MAX_WRITE = 256_000

PROTECTED_PARTS = {
    ".env", ".ssh", ".gnupg", ".aws", ".config/gh", ".git-credentials",
    "credentials", "credential", "secrets", "secret", "api_key", "apikey",
    "private_key", "keystore", "wallet", "seed", "mnemonic",
}
FINANCIAL_WORDS = {
    "withdraw", "withdrawal", "deposit", "payout", "payment", "transfer_funds",
    "place_order", "create_order", "market_order", "limit_order", "buy_order",
    "sell_order", "send_money", "cashout", "вывод", "пополнение", "перевод_средств",
}
DENIED_PROGRAMS = {
    "curl", "wget", "nc", "netcat", "socat", "ssh", "scp", "sftp", "ftp",
    "telnet", "openssl", "gpg", "su", "sudo", "termux-api-start",
}
ALLOWED_PROGRAMS = {
    "pwd", "ls", "whoami", "id", "uname", "date", "uptime", "df", "du", "stat",
    "find", "rg", "grep", "sed", "head", "tail", "wc", "sort", "uniq", "cut",
    "tr", "xargs", "basename", "dirname", "realpath", "readlink", "file", "md5sum",
    "sha256sum", "ps", "pgrep", "pkill", "kill", "top", "free", "lsof",
    "git", "python", "python3", "pip", "pip3", "pytest", "ruff", "mypy",
    "pkg", "apt", "apt-get", "dpkg", "termux-info", "chmod", "mkdir", "touch",
    "cp", "mv", "rm", "tar", "gzip", "gunzip", "zip", "unzip",
}

STATE.mkdir(parents=True, exist_ok=True)
JOURNAL.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def audit(event: str, **fields) -> None:
    record = {"time": now(), "event": event, **fields}
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def git_run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def normalized_text(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def reject_forbidden_text(values: list[object]) -> None:
    joined = " ".join(normalized_text(v) for v in values)
    if any(word in joined for word in FINANCIAL_WORDS):
        raise PermissionError("FINANCIAL_ACTION_BLOCKED")
    if any(part in joined for part in PROTECTED_PARTS):
        raise PermissionError("PROTECTED_SECRET_PATH_BLOCKED")


def safe_path(raw: object, *, must_exist: bool = False) -> Path:
    value = str(raw or "").strip()
    if not value:
        raise ValueError("path is required")
    reject_forbidden_text([value])
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = HOME / candidate
    resolved = candidate.resolve(strict=must_exist)
    if resolved != HOME and HOME not in resolved.parents:
        raise PermissionError("PATH_OUTSIDE_TERMUX_HOME")
    reject_forbidden_text([str(resolved.relative_to(HOME))])
    return resolved


def redact(text: str) -> str:
    patterns = [
        r"(?i)(api[_-]?key|api[_-]?secret|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*\S+",
        r"(?i)bearer\s+[A-Za-z0-9._~+/-]{12,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    ]
    result = text
    for pattern in patterns:
        result = re.sub(pattern, "[REDACTED]", result)
    return result[-MAX_OUTPUT:]


def list_dir(command: dict) -> dict:
    path = safe_path(command.get("path", str(HOME)), must_exist=True)
    if not path.is_dir():
        raise NotADirectoryError(str(path))
    limit = max(1, min(int(command.get("limit", 500)), 2000))
    entries = []
    for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if any(part in normalized_text(item.name) for part in PROTECTED_PARTS):
            continue
        try:
            stat = item.stat()
            entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file", "size": stat.st_size, "mtime": int(stat.st_mtime)})
        except OSError:
            entries.append({"name": item.name, "type": "unavailable"})
        if len(entries) >= limit:
            break
    return {"path": str(path), "entries": entries, "truncated": len(entries) >= limit}


def read_text(command: dict) -> dict:
    path = safe_path(command.get("path"), must_exist=True)
    if not path.is_file():
        raise ValueError("not a regular file")
    size = path.stat().st_size
    if size > MAX_READ:
        raise ValueError(f"file exceeds {MAX_READ} bytes")
    content = path.read_text(encoding="utf-8", errors="replace")
    return {"path": str(path), "size": size, "content": redact(content)}


def write_text(command: dict) -> dict:
    path = safe_path(command.get("path"), must_exist=False)
    content = str(command.get("content", ""))
    reject_forbidden_text([path, content[:4000]])
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_WRITE:
        raise ValueError(f"content exceeds {MAX_WRITE} bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)
    return {"path": str(path), "bytes": len(encoded)}


def validate_exec(argv: object) -> list[str]:
    if not isinstance(argv, list) or not argv or not all(isinstance(v, str) for v in argv):
        raise ValueError("argv must be a non-empty string array")
    if len(argv) > 80:
        raise ValueError("too many arguments")
    reject_forbidden_text(argv)
    program = Path(argv[0]).name
    if program in DENIED_PROGRAMS or program not in ALLOWED_PROGRAMS:
        raise PermissionError(f"PROGRAM_NOT_ALLOWED: {program}")
    if program in {"python", "python3"}:
        if len(argv) < 2 or argv[1].startswith("-"):
            raise PermissionError("python requires a script path; -c and stdin are blocked")
        argv = list(argv)
        argv[1] = str(safe_path(argv[1], must_exist=True))
    if program in {"pip", "pip3", "pkg", "apt", "apt-get"} and any(v in {"remove", "uninstall", "purge"} for v in argv[1:]):
        raise PermissionError("PACKAGE_REMOVAL_BLOCKED")
    if program == "git" and any(v in {"credential", "credential-store"} for v in argv[1:]):
        raise PermissionError("GIT_CREDENTIAL_ACCESS_BLOCKED")
    return argv


def exec_argv(command: dict) -> dict:
    argv = validate_exec(command.get("argv"))
    cwd = safe_path(command.get("cwd", str(HOME)), must_exist=True)
    if not cwd.is_dir():
        raise NotADirectoryError(str(cwd))
    timeout = max(1, min(int(command.get("timeout", 60)), 300))
    safe_env_keys = (
        "PATH", "PREFIX", "TMPDIR", "LD_PRELOAD", "SHELL", "TERM", "COLORTERM",
        "ANDROID_DATA", "ANDROID_ROOT", "ANDROID_RUNTIME_ROOT", "BOOTCLASSPATH",
        "DEX2OATBOOTCLASSPATH",
    )
    safe_env = {key: os.environ[key] for key in safe_env_keys if os.environ.get(key)}
    for key, value in os.environ.items():
        if key.startswith(("TERMUX_", "TERMUX__", "ANDROID__")):
            safe_env[key] = value
    safe_env.update({"HOME": str(HOME), "LANG": os.environ.get("LANG", "C.UTF-8")})
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=safe_env)
    return {"argv": argv, "cwd": str(cwd), "returncode": proc.returncode, "stdout": redact(proc.stdout), "stderr": redact(proc.stderr)}


def execute(command: dict) -> dict:
    action = str(command.get("action", "")).strip().upper()
    if action == "PING":
        return {"pong": True, "version": VERSION, "home": str(HOME)}
    if action == "LIST_DIR":
        return list_dir(command)
    if action == "READ_TEXT":
        return read_text(command)
    if action == "WRITE_TEXT":
        return write_text(command)
    if action == "EXEC":
        return exec_argv(command)
    raise PermissionError("ACTION_NOT_ALLOWED")


def publish(payload: dict) -> None:
    merge = git_run(["git", "merge", "--ff-only", "origin/main"], timeout=45)
    if merge.returncode != 0:
        raise RuntimeError("cannot fast-forward: " + merge.stderr[-300:])
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git_run(["git", "add", "remote/termux_status.json"])
    commit = git_run(["git", "commit", "-m", f"Termux report {payload.get('id', 'unknown')}"])
    if commit.returncode != 0 and "nothing to commit" not in (commit.stdout + commit.stderr).lower():
        raise RuntimeError("git commit failed: " + commit.stderr[-300:])
    push = git_run(["git", "push", "origin", "HEAD:main"], timeout=60)
    if push.returncode != 0:
        pull = git_run(["git", "pull", "--rebase", "origin", "main"], timeout=60)
        if pull.returncode != 0:
            raise RuntimeError("git rebase failed: " + pull.stderr[-300:])
        push = git_run(["git", "push", "origin", "HEAD:main"], timeout=60)
        if push.returncode != 0:
            raise RuntimeError("git push failed: " + push.stderr[-300:])


audit("started", version=VERSION, mode="managed_termux", real_trading=False)
while True:
    try:
        fetch = git_run(["git", "fetch", "--quiet", "origin", "main"], timeout=45)
        if fetch.returncode != 0:
            audit("fetch_error", detail=fetch.stderr[-500:])
            time.sleep(POLL_EVERY)
            continue
        shown = git_run(["git", "show", f"origin/main:{COMMAND_PATH}"])
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
        try:
            result = execute(command)
            payload = {"ok": True, "id": command_id, "action": action, "time": now(), "result": result}
            audit("executed", id=command_id, action=action)
        except Exception as exc:
            payload = {"ok": False, "id": command_id, "action": action, "time": now(), "error": f"{type(exc).__name__}: {exc}"}
            audit("denied_or_failed", id=command_id, action=action, detail=payload["error"])
        LAST_ID.write_text(command_id, encoding="utf-8")
        publish(payload)
        audit("published", id=command_id, action=action)
    except Exception as exc:
        audit("loop_error", detail=f"{type(exc).__name__}: {exc}")
    time.sleep(POLL_EVERY)
