#!/usr/bin/env python3
"""Inject a one-line context banner for Claude Code or Codex.

Claude: reads transcript JSONL message.usage (exact).
Codex:  reads rollout JSONL token_count events (exact).
Cursor: not used — Cursor has no per-session usage API; the alwaysApply rule estimates.

Also appends user_overhead from measure_user_overhead.py (cached) and a
one-line audit offer when thresholds fire (once per cache TTL).

Stdout is the host-specific hook JSON. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


# Fractions of the context window, chosen so a 200K window keeps the original
# 40K / 90K trip points and a 1M window scales instead of sitting permanently red.
WARN_RATIO = 0.20
CRIT_RATIO = 0.45
WARN_TURNS = 20
CRIT_TURNS = 40

# A session may run on a larger window than the 200K default (1M beta). Nothing in
# the transcript states the window, so infer it from the largest context actually
# observed rather than reporting an impossible >100%.
WINDOW_TIERS = (200_000, 500_000, 1_000_000)

OFFER_IMMEDIATE_K = 20
OFFER_DEFERRED_K = 20
OFFER_DEFERRED_TURN = 10


def _read_stdin() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _fmt_tok(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _window_for(peak_ctx: int) -> int:
    override = (os.environ.get("CONTEXT_TRACKER_WINDOW") or "").strip()
    if override.isdigit() and int(override) > 0:
        return int(override)
    for tier in WINDOW_TIERS:
        if peak_ctx <= tier:
            return tier
    return WINDOW_TIERS[-1]


def _light(ctx: int, turns: int, window: int) -> tuple[str, str]:
    if ctx >= window * CRIT_RATIO or turns >= CRIT_TURNS:
        return "🔴", "handoff soon — write audits/handoff/ then start a fresh thread"
    if ctx >= window * WARN_RATIO or turns >= WARN_TURNS:
        return "🟡", "context growing"
    return "🟢", ""


def _temp_dir() -> Path:
    return Path(os.environ.get("TEMP") or os.environ.get("TMPDIR") or os.environ.get("TMP") or "/tmp")


def _offer_state_path() -> Path:
    return _temp_dir() / "etoro-overhead-offer-shown.json"


def _baseline_path() -> Path:
    return _temp_dir() / "etoro-context-tracker-baseline.json"


def session_fingerprint(mode: str, data: dict) -> str:
    """Stable key for baseline / offer state across compact resets."""
    tp = data.get("transcript_path") or data.get("transcriptPath") or ""
    sid = data.get("session_id") or data.get("sessionId") or ""
    parts = [mode, str(tp).replace("\\", "/"), str(sid)]
    return "|".join(parts)


def write_baseline(payload: dict) -> None:
    path = _baseline_path()
    try:
        existing: dict = {}
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
        sessions = existing.get("sessions") if isinstance(existing.get("sessions"), dict) else {}
        fp = str(payload.get("fp") or "")
        if not fp:
            return
        sessions[fp] = payload
        path.write_text(
            json.dumps({"sessions": sessions}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def load_baseline(fp: str) -> dict | None:
    path = _baseline_path()
    if not fp or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        sessions = data.get("sessions") if isinstance(data, dict) else None
        if isinstance(sessions, dict) and fp in sessions:
            row = sessions[fp]
            return row if isinstance(row, dict) else None
        # Legacy single-object shape
        if isinstance(data, dict) and data.get("fp") == fp:
            return data
    except (OSError, json.JSONDecodeError):
        return None
    return None


def apply_baseline(stats: dict | None, fp: str) -> dict | None:
    """Subtract turns/cost accumulated before the last compact/clear."""
    if not stats:
        return stats
    base = load_baseline(fp)
    if not base:
        return stats
    out = dict(stats)
    turns = int(out.get("turns") or 0)
    cost = float(out.get("cost") or 0.0)
    turns_at = int(base.get("turns_at_reset") or 0)
    cost_at = float(base.get("cost_at_reset") or 0.0)
    out["turns"] = max(0, turns - turns_at)
    out["cost"] = max(0.0, cost - cost_at)
    out["reset_reason"] = str(base.get("reason") or "")
    return out


def clear_offer_shown(fingerprint: str) -> None:
    """Allow the overhead offer to fire again after compact/clear."""
    path = _offer_state_path()
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("fingerprint") == fingerprint:
            path.unlink(missing_ok=True)  # type: ignore[arg-type]
    except (OSError, json.JSONDecodeError, TypeError):
        try:
            path.unlink()
        except OSError:
            pass


def _load_user_overhead() -> dict | None:
    """Fail-open: never break the footer if measure fails."""
    try:
        script_dir = Path(__file__).resolve().parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from measure_user_overhead import load_or_measure  # type: ignore

        return load_or_measure()
    except Exception:
        return None


def _should_offer(overhead_k: float, turn: int) -> bool:
    if overhead_k >= OFFER_IMMEDIATE_K:
        return True
    if overhead_k >= OFFER_DEFERRED_K and turn >= OFFER_DEFERRED_TURN:
        return True
    return False


def _offer_already_shown(fingerprint: str) -> bool:
    path = _offer_state_path()
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("fingerprint") == fingerprint
    except (OSError, json.JSONDecodeError):
        return False


def _mark_offer_shown(fingerprint: str, overhead_k: float) -> None:
    path = _offer_state_path()
    try:
        path.write_text(
            json.dumps({"fingerprint": fingerprint, "overhead_k": overhead_k}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def overhead_suffix(turn: int) -> str:
    """Append user_overhead + optional one-line offer. Empty string on failure."""
    data = _load_user_overhead()
    if not data or data.get("error"):
        return ""
    try:
        overhead_k = float(data.get("user_overhead_k") or 0)
    except (TypeError, ValueError):
        return ""
    if overhead_k <= 0:
        return ""
    n = int(round(overhead_k))
    lines = [f"user_overhead≈{n}K (rules+skills+MCP, disk)"]
    fp = str(data.get("fingerprint") or "")
    # turn in banner is often turns+1 (next reply); callers pass that value
    if _should_offer(overhead_k, turn) and not _offer_already_shown(fp):
        lines.append(
            f"💡 overhead: user baseline ~{n}K (rules+skills+MCP) — say **audit overhead** to shrink it."
        )
        _mark_offer_shown(fp, overhead_k)
    return "\n" + "\n".join(lines)

def parse_claude(transcript: Path) -> dict | None:
    if not transcript.is_file():
        return None
    turns = 0
    last_ctx = 0
    peak_ctx = 0
    cost = 0.0
    # The compaction request itself is logged with the full pre-compact context as its
    # input. Reading it back would report the tokens that were just discarded, so any
    # usage row older than the summary is stale until the next real turn lands.
    stale_ctx = False
    # Rough Anthropic-ish rates for relative discipline, not billing truth.
    rates = {"in": 3.0 / 1e6, "out": 15.0 / 1e6, "cr": 0.30 / 1e6, "cw": 3.75 / 1e6}
    try:
        with transcript.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role = (obj.get("type") or obj.get("role") or "").lower()
                msg = obj.get("message") or obj
                if obj.get("isCompactSummary") or (
                    isinstance(msg, dict) and msg.get("isCompactSummary")
                ):
                    stale_ctx = True
                if role in ("user", "human") or obj.get("type") == "user":
                    # Skip tool-result echoes when possible
                    content = msg.get("content") if isinstance(msg, dict) else None
                    if isinstance(content, list) and content and isinstance(content[0], dict):
                        if content[0].get("type") == "tool_result":
                            continue
                    turns += 1
                if role in ("assistant",) or obj.get("type") == "assistant":
                    u = (msg.get("usage") if isinstance(msg, dict) else None) or obj.get("usage") or {}
                    if not u:
                        continue
                    inp = int(u.get("input_tokens") or 0)
                    cr = int(u.get("cache_read_input_tokens") or 0)
                    cw = int(u.get("cache_creation_input_tokens") or 0)
                    out = int(u.get("output_tokens") or 0)
                    last_ctx = inp + cr  # visible context roughly
                    peak_ctx = max(peak_ctx, last_ctx)
                    stale_ctx = False
                    cost += inp * rates["in"] + out * rates["out"] + cr * rates["cr"] + cw * rates["cw"]
    except OSError:
        return None
    if last_ctx <= 0 and turns <= 0:
        return None
    return {
        "turns": turns,
        "ctx": 0 if stale_ctx else last_ctx,
        "cost": cost,
        "window": _window_for(peak_ctx),
        "exact": True,
        "pending": stale_ctx,
    }


def parse_codex(transcript: Path) -> dict | None:
    if not transcript.is_file():
        return None
    turns = 0
    ctx = 0
    window = 258_400
    total_in = 0
    total_out = 0
    try:
        with transcript.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == "event_msg":
                    payload = obj.get("payload") or {}
                    if payload.get("type") == "token_count":
                        info = payload.get("info") or {}
                        last = info.get("last_token_usage") or {}
                        total = info.get("total_token_usage") or {}
                        ctx = int(last.get("input_tokens") or total.get("input_tokens") or 0)
                        window = int(info.get("model_context_window") or window)
                        total_in = int(total.get("input_tokens") or 0)
                        total_out = int(total.get("output_tokens") or 0)
                # Rough turn count: user message items
                if obj.get("type") == "response_item":
                    item = obj.get("payload") or obj
                    if (item.get("role") or "").lower() == "user":
                        turns += 1
                if obj.get("type") == "event_msg" and (obj.get("payload") or {}).get("type") == "user_message":
                    turns += 1
    except OSError:
        return None
    if ctx <= 0:
        return None
    # Codex ChatGPT plan — report API-equivalent only as relative signal
    cost = total_in * (1.25 / 1e6) + total_out * (10.0 / 1e6)
    return {"turns": max(turns, 1), "ctx": ctx, "cost": cost, "window": window, "exact": True}


def find_codex_rollout(session_id: str | None) -> Path | None:
    root = Path.home() / ".codex" / "sessions"
    if not root.is_dir():
        return None
    if session_id:
        hits = sorted(root.rglob(f"*{session_id}*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if hits:
            return hits[0]
    hits = sorted(root.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return hits[0] if hits else None


def build_line(stats: dict | None) -> str:
    if not stats:
        turn = 1
        line = (
            "⚡ CONTEXT tracker offline (no usage yet)\n"
            "Emit a self-estimated footer as the LAST line of your reply, marked with ~."
        )
        line += overhead_suffix(turn)
        return line

    turns = int(stats.get("turns") or 0)
    turn = turns + 1
    ctx = int(stats.get("ctx") or 0)
    window = int(stats.get("window") or 200_000)
    cost = float(stats.get("cost") or 0.0)
    if stats.get("pending"):
        light, action = _light(0, turns, window)
        line = f"⚡ CONTEXT turn={turn} | ctx=fresh after compact | ${cost:.3f} | {light}"
    else:
        pct = 100.0 * ctx / window if window else 0.0
        light, action = _light(ctx, turns, window)
        line = (
            f"⚡ CONTEXT turn={turn} | ctx={_fmt_tok(ctx)}/{_fmt_tok(window)} "
            f"({pct:.0f}%) | ${cost:.3f} | {light}"
        )
    if action:
        line += f" — {action}"
    if stats.get("reset_reason"):
        line += f"\n(epoch after {stats['reset_reason']})"
    line += "\nEmit as the LAST line of your reply (one-row color: 🟢=`diff`/`+`, 🟡=plain, 🔴=`diff`/`-`). Exact numbers — do not recompute."
    line += overhead_suffix(turn)
    return line


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    mode = (sys.argv[1] if len(sys.argv) > 1 else "claude").lower()
    data = _read_stdin()
    stats = None
    fp = session_fingerprint(mode, data)

    if mode == "claude":
        tp = data.get("transcript_path") or data.get("transcriptPath")
        if tp:
            stats = parse_claude(Path(tp))
        stats = apply_baseline(stats, fp)
        banner = build_line(stats)
        # Claude Code UserPromptSubmit additionalContext
        out = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": banner,
            },
        }
        # Also set legacy field some builds read
        out["additionalContext"] = banner
        print(json.dumps(out, ensure_ascii=False))
        return 0

    if mode == "codex":
        sid = str(data.get("session_id") or data.get("sessionId") or "")
        tp = data.get("transcript_path") or data.get("transcriptPath")
        path = Path(tp) if tp else find_codex_rollout(sid or None)
        stats = parse_codex(path) if path else None
        stats = apply_baseline(stats, fp)
        banner = build_line(stats)
        print(json.dumps({"continue": True, "systemMessage": banner}, ensure_ascii=False))
        return 0

    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"continue": True}))
        raise SystemExit(0)
