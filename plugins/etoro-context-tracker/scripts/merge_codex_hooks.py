#!/usr/bin/env python3
"""Merge etoro-context-tracker UserPromptSubmit hook into ~/.codex/hooks.json.

Writes a portable `command` (POSIX / macOS / Linux) and a PowerShell
`commandWindows` so the same install works on all platforms.
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path


MARKER = "etoro-context-tracker/scripts/inject_banner.py"


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "usage: merge_codex_hooks.py <hooks.json> <python.exe> <inject_banner.py>",
            file=sys.stderr,
        )
        return 2
    hooks_file = Path(sys.argv[1])
    py_exe = _norm(sys.argv[2])
    script = _norm(sys.argv[3])

    # POSIX: works on macOS/Linux; Codex uses `command` off Windows.
    cmd_posix = f"{shlex.quote(py_exe)} {shlex.quote(script)} codex"
    # Windows: PowerShell form for commandWindows.
    cmd_win = f"& '{py_exe}' '{script}' 'codex'"

    entry = {
        "hooks": [
            {
                "type": "command",
                "command": cmd_posix,
                "commandWindows": cmd_win,
                "timeout": 5,
            }
        ]
    }

    cfg: dict = {"hooks": {}}
    if hooks_file.is_file():
        try:
            cfg = json.loads(hooks_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cfg = {"hooks": {}}
    cfg.setdefault("hooks", {})
    lst = list(cfg["hooks"].get("UserPromptSubmit") or [])
    already = False
    for item in lst:
        for h in item.get("hooks") or []:
            for k in ("command", "commandWindows"):
                if MARKER in _norm(str(h.get(k) or "")):
                    already = True
    if already:
        print("ALREADY")
        return 0
    lst.append(entry)
    cfg["hooks"]["UserPromptSubmit"] = lst
    hooks_file.parent.mkdir(parents=True, exist_ok=True)
    hooks_file.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("MERGED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
