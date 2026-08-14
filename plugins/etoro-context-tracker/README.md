# etoro-context-tracker

Superlight **token-conservation** plugin. One job: keep you aware of conversation growth and force a clean handoff before the thread gets expensive. Also measures **user** overhead (rules + skill descriptions + MCP) and offers a one-line audit when it is fat.

**Not** part of the heavy etoro-official marketplace bundle (30 plugins). Intentionally standalone so it does not compete for context with SDD / domain packs.

| IDE | Numbers | Install |
|---|---|---|
| **Cursor** | Self-estimate (`~`) — no per-session usage API | `install.py --target cursor` → `~/.cursor/plugins/local/` |
| **Claude Code** | Exact — transcript `message.usage` via thin hook | `install.py --target claude` (marketplace) |
| **Codex** | Exact — rollout `token_count` via thin hook | `install.py --target codex` (hooks merge) |
| **Databricks Genie** | Self-estimate (`~`) via space Instructions | Paste [`instructions/genie-context-tracker.md`](instructions/genie-context-tracker.md) |

Works on **macOS, Linux, and Windows** — one Python installer; thin `install.sh` / `install.ps1` wrappers.

### Compact / clear reset

| Surface | Mechanism |
|---|---|
| Claude / Codex | `SessionStart` hook (`compact\|clear`) writes a baseline; next footer counts turns since that epoch |
| Cursor | Rule: after auto-compact, recount only visible human turns |
| Genie | Same as Cursor, in space Instructions |

After install: **Cursor** → Reload Window + new chat. **Claude/Codex** → new session (no Cursor reload required for those apps). **Genie** → paste/update Instructions in the Genie UI.

Overlap note: `etoro-claude-statusline` (Guy Cohen) is a **Claude terminal statusline**. This plugin is the **in-chat footer + handoff** across Cursor / Claude / Codex. Complementary, not a duplicate.

## What it costs in context

- Cursor: one alwaysApply rule (~0.8–1.0K tokens). No hooks. No MCP. Turn-1 measure script is opt-in via Shell.
- Claude / Codex: hook injects ~100–200 tokens of numbers per turn; skill/AGENTS is short.
- Audit playbook lives in `context-overhead-audit` and loads **only** when the user says **audit overhead**.

## Footer

Last line of every reply:

```diff
+ ⚡ Turn 3 | ~18K chat / ~88K total | 🟢
```

Yellow is plain text (no fence). Red is a single-line `diff` fence starting with `-`.
One row only — Cursor chat cannot color arbitrary markdown text; `diff` fences are the only reliable tint.

On 🔴: write `audits/handoff/…` once (goal, decisions, files, verified, open threads, next step), then point at the path.

## User overhead offer

Disk inventory of **user-controlled** surface (alwaysApply rules + skill descriptions + MCP names) — not built-in tools.

| Threshold | When |
|---|---|
| `user_overhead >= 20K` | Offer on turn 1 (once) |
| `user_overhead >= 20K` | Offer after turn 10 if missed turn 1 (once) |
| below 20K | Silence — footer only |

Offer text:

```text
💡 overhead: user baseline ~{N}K (rules+skills+MCP) — say **audit overhead** to shrink it.
```

Saying **audit overhead** loads the `context-overhead-audit` skill (ranked tables; canvas optional in Cursor).

## Install

From this directory (or via the [repo root README](../../README.md)). Needs **Python 3** on PATH:

```bash
# Any OS — canonical entrypoint
python3 scripts/install.py --target all

# macOS / Linux wrapper
./scripts/install.sh --target cursor

# Windows wrapper (PowerShell)
.\scripts\install.ps1 -Target Cursor
```

Common flags (same on all platforms via `install.py`):

```bash
# After Reload Window + new chat confirms the footer works, drop the old
# global alwaysApply copy so the rule isn't loaded twice (~1–1.5K saved):
python3 scripts/install.py --target cursor --remove-global-rule

# If the plugin rule does not load (footer missing), fall back to global:
python3 scripts/install.py --target cursor --also-sync-global-rule

# Claude / Codex / all
python3 scripts/install.py --target claude
python3 scripts/install.py --target codex
python3 scripts/install.py --target all

# Point at a specific interpreter (Codex hook + running install.py)
python3 scripts/install.py --target codex --python /usr/local/bin/python3
```

Claude marketplace (from the cloned repo root):

```bash
claude plugin marketplace add /path/to/agentplugins
claude plugin install etoro-context-tracker@agentplugins
```

Or from GitHub directly:

```bash
claude plugin marketplace add https://github.com/gmanova/agentplugins.git
claude plugin install etoro-context-tracker@agentplugins
```

Session-only (does not persist): `claude --plugin-dir "/path/to/agentplugins/plugins/etoro-context-tracker"`

Manual measure:

```bash
python3 scripts/measure_user_overhead.py --force
```

**Interpreter note:** Claude hooks use `python3 … || python …` (same pattern as the official Databricks plugin). Codex install writes an absolute interpreter path into `~/.codex/hooks.json`, so it does not depend on which name is on PATH after install.
## Layout

```
.cursor-plugin/plugin.json       Cursor manifest (rules only — no hooks)
.claude-plugin/plugin.json       Claude manifest + hooks
rules/context-tracker.mdc        Cursor alwaysApply footer + overhead trigger
skills/context-tracker/SKILL.md  Claude skill
skills/context-overhead-audit/   Opt-in audit playbook
hooks/claude/hooks.json          UserPromptSubmit + SessionStart compact|clear
hooks/codex/hooks.json           UserPromptSubmit + SessionStart compact|clear
scripts/inject_banner.py         Shared Claude/Codex usage reader + baseline subtract
scripts/reset_baseline.py        SessionStart compact|clear → write baseline
scripts/measure_user_overhead.py Disk inventory of user overhead
scripts/install.py               Cross-platform installer (canonical)
instructions/genie-context-tracker.md  Paste into Genie space Instructions
scripts/install.sh               macOS/Linux wrapper → install.py
scripts/install.ps1              Windows wrapper → install.py
scripts/merge_codex_hooks.py     Idempotent ~/.codex/hooks.json merge
AGENTS.md                        Codex instruction snippet
```

Distributed from [gmanova/agentplugins](https://github.com/gmanova/agentplugins).
