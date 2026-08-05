#!/usr/bin/env python3
"""Append the context-tracker section to ~/.codex/AGENTS.md (UTF-8 safe, idempotent).

PowerShell 5.1's Get-Content/Set-Content mangle UTF-8 emoji, so the merge runs here.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "# Context tracker (Codex)"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: merge_codex_agents.py <agents.md> <snippet.md>", file=sys.stderr)
        return 2
    target = Path(sys.argv[1])
    snippet = Path(sys.argv[2]).read_text(encoding="utf-8")

    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    if MARKER in existing:
        print("already has context-tracker section")
        return 0

    if existing and not existing.endswith("\n"):
        existing += "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(existing + "\n" + snippet, encoding="utf-8")
    print(f"appended context-tracker section -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
