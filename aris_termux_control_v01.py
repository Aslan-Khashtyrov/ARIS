#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "0.6"
HOME = Path.home().resolve()
ROOT = (HOME / "Arbitrage").resolve()
STATE = ROOT / "guardian_state"
JOURNAL = ROOT / "journal"
COMMAND_PATH = "remote/termux_command.json"
REPORT_PATH = ROOT / "remote" / "termux_status.json"
LAST_ID = STATE / "termux_control_last_id"
AUDIT = JOURNAL / "termux_control_audit.jsonl"
HEARTBEAT = STATE / "termux_control_heartbeat.json"
POLL_EVERY = 20

# Security invariant: GitHub-originated commands are data, not shell input.
# The remote bridge may only answer a PING. It cannot read or write arbitrary
# local files, execute programs, manage processes, or perform trading actions.
ALLOWED_ACTIONS = frozenset({"PING"})
ALLOWED_FIELDS = frozenset({"id", "action", "note"})
COMMAND_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
MAX_NOTE_LENGTH = 500


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_runtime_dirs() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    JOURNAL.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temp_name = handle.name
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def audit(event: str, **fields: Any) -> None:
    record = {"time": now(), "event": event, **fields}
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_heartbeat(phase: str, **fields: Any) -> None:
    atomic_write_json(
        HEARTBEAT,
        {
            "time": now(),
            "pid": os.getpid(),
            "version": VERSION,
            "mode": "github_ping_only",
            "phase": phase,
            **fields,
        },
    )


def git_run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def safe_identifier(value: object) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._:-]+", "_", str(value or "").strip())
    return cleaned[:128] or "invalid"


def validate_command(command: object) -> tuple[str, str]:
    if not isinstance(command, dict):
        raise ValueError("command must be a JSON object")

    unexpected = set(command) - ALLOWED_FIELDS
    if unexpected:
        raise PermissionError("UNEXPECTED_FIELDS")

    command_id = str(command.get("id", "")).strip()
    if not COMMAND_ID_PATTERN.fullmatch(command_id):
        raise ValueError("invalid command id")

    action = str(command.get("action", "")).strip().upper()
    if action not in ALLOWED_ACTIONS:
        raise PermissionError("ACTION_NOT_ALLOWED_PING_ONLY")

    note = command.get("note")
    if note is not None and (
        not isinstance(note, str) or len(note) > MAX_NOTE_LENGTH
    ):
        raise ValueError("invalid note")

    return command_id, action


def execute(command: object) -> tuple[str, str, dict[str, Any]]:
    command_id, action = validate_command(command)
    return (
        command_id,
        action,
        {
            "pong": True,
            "version": VERSION,
            "mode": "github_ping_only",
            "real_trading": False,
        },
    )


def require_clean_repository() -> None:
    unstaged = git_run(["git", "diff", "--quiet"])
    staged = git_run(["git", "diff", "--cached", "--quiet"])
    if unstaged.returncode != 0 or staged.returncode != 0:
        raise RuntimeError("repository has tracked local changes")

    branch = git_run(["git", "branch", "--show-current"])
    if branch.returncode != 0 or branch.stdout.strip() != "main":
        raise RuntimeError("controller requires local main branch")


def publish(payload: dict[str, Any]) -> None:
    require_clean_repository()

    merge = git_run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "merge",
            "--ff-only",
            "origin/main",
        ],
        timeout=45,
    )
    if merge.returncode != 0:
        raise RuntimeError("cannot fast-forward: " + merge.stderr[-300:])

    atomic_write_json(REPORT_PATH, payload)
    add = git_run(["git", "add", "--", "remote/termux_status.json"])
    if add.returncode != 0:
        raise RuntimeError("git add failed: " + add.stderr[-300:])

    commit = git_run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-m",
            f"Termux report {payload.get('id', 'unknown')}",
            "--",
            "remote/termux_status.json",
        ]
    )
    combined = (commit.stdout + commit.stderr).lower()
    if commit.returncode != 0 and "nothing to commit" not in combined:
        raise RuntimeError("git commit failed: " + commit.stderr[-300:])
    if commit.returncode != 0:
        return

    push = git_run(["git", "push", "origin", "HEAD:main"], timeout=60)
    if push.returncode == 0:
        return

    rebase = git_run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "pull",
            "--rebase",
            "origin",
            "main",
        ],
        timeout=60,
    )
    if rebase.returncode != 0:
        git_run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "rebase",
                "--abort",
            ]
        )
        raise RuntimeError("git rebase failed: " + rebase.stderr[-300:])

    push = git_run(["git", "push", "origin", "HEAD:main"], timeout=60)
    if push.returncode != 0:
        raise RuntimeError("git push failed: " + push.stderr[-300:])


def process_once() -> None:
    write_heartbeat("polling")
    fetch = git_run(
        [
            "git",
            "fetch",
            "--quiet",
            "--no-tags",
            "origin",
            "refs/heads/main:refs/remotes/origin/main",
        ],
        timeout=45,
    )
    if fetch.returncode != 0:
        write_heartbeat("fetch_error", returncode=fetch.returncode)
        audit("fetch_error", detail=fetch.stderr[-500:])
        return

    shown = git_run(["git", "show", f"origin/main:{COMMAND_PATH}"])
    if shown.returncode != 0:
        write_heartbeat("command_unavailable")
        return

    fingerprint = hashlib.sha256(shown.stdout.encode("utf-8")).hexdigest()
    previous = LAST_ID.read_text(encoding="utf-8").strip() if LAST_ID.exists() else ""
    if fingerprint == previous:
        return

    raw_id: object = "invalid"
    raw_action: object = "UNKNOWN"
    try:
        command = json.loads(shown.stdout)
        if isinstance(command, dict):
            raw_id = command.get("id", "invalid")
            raw_action = command.get("action", "UNKNOWN")
        command_id, action, result = execute(command)
        payload = {
            "ok": True,
            "id": command_id,
            "action": action,
            "time": now(),
            "result": result,
        }
        audit("executed", id=command_id, action=action)
    except Exception as exc:
        command_id = safe_identifier(raw_id)
        action = safe_identifier(raw_action).upper()
        payload = {
            "ok": False,
            "id": command_id,
            "action": action,
            "time": now(),
            "error": f"{type(exc).__name__}: {exc}",
        }
        audit(
            "denied_or_failed",
            id=command_id,
            action=action,
            detail=payload["error"],
        )

    publish(payload)
    LAST_ID.write_text(fingerprint, encoding="utf-8")
    write_heartbeat("published", command_id=command_id, action=action)
    audit("published", id=command_id, action=action)


def main() -> None:
    ensure_runtime_dirs()
    audit(
        "started",
        version=VERSION,
        mode="github_ping_only",
        real_trading=False,
        local_read=False,
        local_write=False,
        process_control=False,
        shell_access=False,
    )
    while True:
        try:
            process_once()
        except Exception as exc:
            write_heartbeat("loop_error", error_type=type(exc).__name__)
            audit("loop_error", detail=f"{type(exc).__name__}: {exc}")
        time.sleep(POLL_EVERY)


if __name__ == "__main__":
    main()
