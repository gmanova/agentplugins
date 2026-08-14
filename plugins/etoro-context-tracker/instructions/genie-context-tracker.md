# Context tracker (Genie Instructions)

Paste this block into a Genie space **Instructions** field. Genie has no hooks — the model self-estimates and must reset after auto-compact.

## Footer — last line of every reply

```text
⚡ Turn {N} | ~{chat}K chat / ~{total}K total | {light}
```

- Always prefix estimates with `~`.
- Green (`chat` < 40K): optional one-line diff fence starting with `+`
- Yellow (40–90K): plain text + `context growing`
- Red (`chat` > 90K): note that the thread should be restarted / hand off key state

## Numbers

- `N` = human user turns in the **current visible** conversation (1-indexed).
- `chat ≈ (N × 2) + (tool-ish exchanges × 2)` in K (rough).
- `total ≈ chat + baseline` where baseline ≈ 30–50K for a typical Genie space with tables + instructions.
- Baseline alone is not a reason to panic — watch **chat** growth.

## Post-compact / new epoch (CRITICAL)

Genie auto-compacts when context is full. After compaction you will see a **summary of earlier turns** and only recent messages.

When that happens:
1. Restart counting — `N` = human turns **after** the summary only.
2. Do not carry forward old turn totals or a prior red warning.
3. Only warn red again if the **post-compact** visible chat is still large.

New chat → Turn 1.

## Suppress

User says "stop nudging" → drop the footer for the rest of the thread.
