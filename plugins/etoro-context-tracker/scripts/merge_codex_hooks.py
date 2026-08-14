#!/usr/bin/env python3
"""Merge etoro-context-tracker hooks into ~/.codex/hooks.json.

Merges both UserPromptSubmit (inject_banner) and SessionStart compact|clear
(reset_baseline). Writes portable POSIX `command` + PowerShell `commandWindows`.

usage: merge_codex_hooks.py <hooks.json> <python.exe> <plugin_scripts_dir>
  (or legacy) merge_codex_hooks.py <hooks.json> <python.exe> <inject_banner.py>
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path


INJECT_MARKER = "etoro-context-tracker/scripts/inject_banner.py"
RESET_MARKER = "etoro-context-tracker/scripts/reset_baseline.py"


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _entry(py_exe: str, script: str, arg: str) -> dict:
    cmd_posix = f"{shlex.quote(py_exe)} {shlex.quote(script)} {arg}"
    # Escape single quotes for PowerShell single-quoted strings
    py_ps = py_exe.replace("'", "''")
    sc_ps = script.replace("'", "''")
    cmd_win = f"& '{py_ps}' '{sc_ps}' '{arg}'"
    return {
        "hooks": [
            {
                "type": "command",
                "command": cmd_posix,
                "commandWindows": cmd_win,
                "timeout": 5,
            }
        ]
    }


def _already(lst: list, marker: str) -> bool:
    for item in lst:
        for h in item.get("hooks") or []:
            for k in ("command", "commandWindows"):
                if marker in _norm(str(h.get(k) or "")):
                    return True
    return False


def _merge_event(cfg: dict, event: str, entry: dict, marker: str) -> str:
    lst = list(cfg["hooks"].get(event) or [])
    if _already(lst, marker):
        return "ALREADY"
    # SessionStart needs matcher for compact|clear
    if event == "SessionStart":
        entry = {
            "matcher": "compact|clear",
            **entry,
        }
    lst.append(entry)
    cfg["hooks"][event] = lst
    return "MERGED"


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "usage: merge_codex_hooks.py <hooks.json> <python.exe> <inject_banner.py|scripts_dir>",
            file=sys.stderr,
        )
        return 2
    hooks_file = Path(sys.argv[1])
    py_exe = _norm(sys.argv[2])
    third = Path(sys.argv[3])

    # Accept either inject_banner.py path (legacy) or scripts directory
    if third.is_dir():
        scripts = third
    elif third.name == "inject_banner.py":
        scripts = third.parent
    else:
        scripts = third.parent

    inject = _norm(str((scripts / "inject_banner.py").resolve()))
    reset = _norm(str((scripts / "reset_baseline.py").resolve()))

    cfg: dict = {"hooks": {}}
    if hooks_file.is_file():
        try:
            cfg = json.loads(hooks_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cfg = {"hooks": {}}
    cfg.setdefault("hooks", {})

    r1 = _merge_event(cfg, "UserPromptSubmit", _entry(py_exe, inject, "codex"), INJECT_MARKER)
    r2 = _merge_event(cfg, "SessionStart", _entry(py_exe, reset, "codex"), RESET_MARKER)

    hooks_file.parent.mkdir(parents=True, exist_ok=True)
    hooks_file.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"UserPromptSubmit={r1} SessionStart={r2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
