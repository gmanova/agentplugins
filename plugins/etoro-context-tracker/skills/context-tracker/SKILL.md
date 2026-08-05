---
name: context-tracker
description: Superlight token-conservation footer. Always follow when composing a reply — append the one-line context tracker as the last line. Exact numbers come from the UserPromptSubmit hook banner when present; otherwise self-estimate with ~. Also surface the overhead offer when the banner or measure says so; if the user says audit overhead, load context-overhead-audit.
---

# Context tracker (Claude Code)

## Last line of every reply

If context contains a `SESSION turn=` / `⚡ CONTEXT` / hook banner with real usage, **condense it** — do not reprint the raw block:

```
⚡ Turn {N} | {ctx} ({pct}%) | ${cost} | {light}
```

Those numbers are **exact** (transcript `message.usage`). Do not recompute them.

If no hook banner is present, self-estimate and mark with `~` (same formula as the Cursor rule).

## User overhead offer

If the hook banner includes `user_overhead≈…K` and/or the 💡 overhead offer line, surface the offer **once** to the user (do not spam). Thresholds are enforced by the hook (20K immediate / 20K after turn 10 if missed).

When the user says **audit overhead**, load the `context-overhead-audit` skill and follow it.

## One-row color

| State | Emit |
|---|---|
| 🟢 | single-line `diff` fence, line starts with `+` |
| 🟡 | plain text + `context growing` |
| 🔴 | single-line `diff` fence, line starts with `-` |

Never a three-row block. Fall back to plain emoji if fences look wrong.

## Red → handoff file once

Write `audits/handoff/{YYYY-MM-DD-HHmm}-{slug}.md` (else `scratch/handoff/`, else `~/.claude/handoffs/`) with Goal · Decisions · Files changed · Verified · Open threads · Exact next step. Point at the path in the footer. Once per thread.

## Suppress

"stop nudging" → drop the footer and overhead offers for the rest of the thread.
