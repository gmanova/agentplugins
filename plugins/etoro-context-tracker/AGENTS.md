# Context tracker (Codex)

This file is installed into `~/.codex/AGENTS.md` (or appended) by `scripts/install.ps1 -Target Codex`.

The `UserPromptSubmit` hook injects an `⚡ CONTEXT` system message with **exact** numbers
from the session rollout's `token_count` events (`input_tokens`, `model_context_window`).

## Last line of every reply

Condense the hook message — do not reprint it raw:

```
⚡ Turn {N} | {ctx}/{window} ({pct}%) | ${cost} | {light}
```

Exact — do not recompute. If the hook says tracker offline, self-estimate and mark with `~`.

## One-row color

| State | Emit |
|---|---|
| 🟢 | single-line `diff` fence, line starts with `+` |
| 🟡 | plain text + `context growing` |
| 🔴 | single-line `diff` fence, line starts with `-` |

## Red → handoff once

Write `audits/handoff/{YYYY-MM-DD-HHmm}-{slug}.md` (else `scratch/handoff/`, else `~/.codex/handoffs/`).
Sections: Goal · Decisions · Files changed · Verified · Open threads · Exact next step.

## Suppress

"stop nudging" → drop the footer and overhead offers for the rest of the thread.

## User overhead

The hook may append `user_overhead≈NK` and a one-line offer when disk-measured
rules+skills+MCP exceed 20K (immediate on turn 1, or after turn 10 if missed):

```
💡 overhead: user baseline ~{N}K (rules+skills+MCP) — say **audit overhead** to shrink it.
```

Surface the offer once. When the user says **audit overhead**, follow the
`context-overhead-audit` skill.

## What Codex does NOT have

There is no Team Marketplace / one-click install for Codex. This plugin reaches Codex only
via the installer (hooks merge + this AGENTS snippet). That is intentional and permanent
until OpenAI ships a marketplace equivalent.
