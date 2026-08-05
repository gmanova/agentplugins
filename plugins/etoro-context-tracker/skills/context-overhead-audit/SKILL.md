---
name: context-overhead-audit
description: >-
  Audit and shrink user context overhead (alwaysApply rules, skill
  descriptions, MCP). Use when the user says audit overhead or accepts an
  overhead offer.
---

# Context overhead audit

Triggered by: user says **audit overhead** (or accepts the tracker’s one-line offer).

You are auditing **user-controlled** prompt cost only — not built-in tools, not IDE scaffolding, not chat growth.

## 1. Measure (disk trigger number)

```bash
python "${PLUGIN_ROOT}/scripts/measure_user_overhead.py" --force
```

If `PLUGIN_ROOT` is unknown, resolve from the installed plugin path (Cursor: `~/.cursor/plugins/local/etoro-context-tracker`, or the repo `plugins/etoro-context-tracker`).

Read JSON fields: `user_overhead_k`, `layers`, `top_offenders`, `counts`.

## 2. Ground truth (prompt introspection)

Disk can overcount disabled-but-cached plugins. From **this** system prompt, count:

| Layer | How |
|---|---|
| Always-applied rules | Bodies actually present under always_applied_workspace_rules / alwaysApply |
| Skill descriptions | Entries in `available_skills` (name + description only) |
| MCP | Server names / tool-name stubs in the MCP catalog |
| Exclude | Built-in tool schemas (Shell, Read, …), mode scaffolding |

Report both numbers: disk vs prompt. Prefer **prompt** for recommendations.

## 3. Rank and recommend

Produce markdown tables (default — portable everywhere):

```markdown
| Layer | Disk K | Prompt K |
|---|---|---|
| alwaysApply rules | … | … |
| skill descriptions | … | … |
| MCP stubs | … | … |
| **user_overhead** | … | … |

| Offender | Kind | Tok | Recommended cut |
|---|---|---|---|
| … | rule/skill/mcp | … | demote / trim desc / disable plugin / dedupe |
```

Cut types (only these):

1. **Demote** `alwaysApply: true` → globs / agent-requestable (wire entry points so the safety net still loads when needed)
2. **Trim skill descriptions** to 150–300 chars (WHAT + WHEN + a few trigger keywords). Never delete skill bodies
3. **Disable unused plugins** / MCP servers the user does not need this month
4. **Collapse duplicate skills** listed from two roots

Do **not** invent cuts for platform-mandatory tools. Do **not** auto-mutate anything destructive without confirming with the user.

## 4. Canvas (optional)

If the host supports `cursor/canvas` and the user is in Cursor, you may also render the same tables as a canvas. Never require canvas. Markdown tables are the deliverable.

## 5. After cuts

1. Re-run `measure_user_overhead.py --force`
2. Tell the user to **Reload Window → new chat** so the prompt drops demoted rules/skills
3. Do **not** rewrite the tracker’s default `baseline ≈ N` unless this workspace explicitly owns that documented estimate and the user asks

## Offer phrase (for agents that surface the trigger)

```text
💡 overhead: user baseline ~{N}K (rules+skills+MCP) — say **audit overhead** to shrink it.
```
