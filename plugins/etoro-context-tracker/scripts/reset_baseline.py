#!/usr/bin/env python3
"""SessionStart hook: reset tracker baseline after compact or clear.

Writes a per-session baseline so inject_banner.py counts turns/cost only
since the reset (full transcript JSONL still grows forever).

Arg: claude | codex
Stdout: SessionStart hook JSON. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Same directory imports
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from inject_banner import (  # noqa: E402
    _read_stdin,
    clear_offer_shown,
    find_codex_rollout,
    parse_claude,
    parse_codex,
    session_fingerprint,
    write_baseline,
)


def _reason(data: dict) -> str:
    for key in ("source", "matcher", "reason", "compact_trigger"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip().lower()
    # Nested shapes some hosts use
    for nest in ("hook_event_info", "hookEventInfo", "session"):
        obj = data.get(nest)
        if isinstance(obj, dict):
            for key in ("source", "matcher", "reason"):
                v = obj.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip().lower()
    return "compact"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    mode = (sys.argv[1] if len(sys.argv) > 1 else "claude").lower()
    data = _read_stdin()
    reason = _reason(data)
    if reason not in ("compact", "clear", "manual", "auto"):
        # Still reset — SessionStart matcher already filtered compact|clear
        if "clear" in reason:
            reason = "clear"
        else:
            reason = "compact"

    stats = None
    tp = data.get("transcript_path") or data.get("transcriptPath")
    sid = str(data.get("session_id") or data.get("sessionId") or "")

    if mode == "claude" and tp:
        stats = parse_claude(Path(tp))
    elif mode == "codex":
        path = Path(tp) if tp else find_codex_rollout(sid or None)
        stats = parse_codex(path) if path else None

    turns = int((stats or {}).get("turns") or 0)
    cost = float((stats or {}).get("cost") or 0.0)
    fp = session_fingerprint(mode, data)

    write_baseline(
        {
            "fp": fp,
            "turns_at_reset": turns,
            "cost_at_reset": cost,
            "reason": reason,
            "mode": mode,
            "transcript_path": str(tp or ""),
            "session_id": sid,
        }
    )
    clear_offer_shown(fp)

    note = (
        f"⚡ CONTEXT reset after {reason} — counting turns from a fresh epoch "
        f"(baseline turns={turns}). Emit footer Turn 1 on the next reply unless "
        f"new turns have already accrued."
    )
    out = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": note,
        },
        "additionalContext": note,
        "systemMessage": note,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Fail open — never block compact/clear
        print(json.dumps({"continue": True}))
        raise SystemExit(0)
