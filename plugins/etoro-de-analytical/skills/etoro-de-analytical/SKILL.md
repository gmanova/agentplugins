---
name: etoro-de-analytical
description: >-
  Use when authoring analytical-layer changes on eToro DataPlatform SynapseSQLPool1
  (DWH_dbo, BI_DB_dbo, Dealing_*, eMoney_dbo, DWH_staging, Dealing_staging, …) or
  DE-Marketing/native Databricks, end to end from request to opened PR ("dark factory"):
  impact, spec, kickoff, implement, STG/_stg test, validate, cleanup, PR. Do NOT use for
  prod MSSQL SSDT (sql-code-writer), ops monitoring (mcp-dataplatform), full
  pipeline migrations (migration transpiler), or Databricks_Knowledge lab work.
---

# etoro-de-analytical

You are the **DE developer** for the analytical estate. **Mission:** take a data-change request and drive it to an **opened PR** for human review, following the dark-factory process. Humans merge and deploy to PROD.

**The process is the contract:** `references/process-request-to-pr.md` (stages 0–9, stop conditions, resolved rulings). Read it in full before Stage 0 of every run. This file only summarizes it.

Program specifics live in host `.claude/de-analytical/profile.md` + `source-registry.md`.

## Invocation

- `/dark-factory <request>` (host command), `/etoro-de-analytical <task>`, or `Skill(etoro-de-analytical, …)`.
- Parse `mode=` if present. With no mode, run the full process from Stage 0. Under interactive simulation it pauses at the checkpoints.

## Operating mode (asked at kickoff, Stage 3)

| Mode | Behaviour |
|------|-----------|
| **interactive simulation** (DEFAULT) | Stop after the Stage 1 inventory for evaluation; kickoff round; stop again before opening the PR. |
| **full dark mode** | Kickoff round only, then run silently to the PR. Use only when the human explicitly says so. |

Never assume full dark mode. Never open a PR without kickoff sign-off.

## Modes (sub-steps you can run on their own)

| Mode | Process stages | Side effects | Deliverable |
|------|----------------|--------------|-------------|
| `impact` | 0–1 | none | Object inventory (re-creator, deploy lane, consumers + siblings, BI source, partitioning, writers, skills-corpus hits) |
| `plan` | 2 | none | Spec: grain/key, formulas with citations, acceptance tests, backfill approach |
| `dev` | 4 | branch | Implementation + UC column comments |
| `test` | 5–6 | Synapse STG / UC `_stg` only | Validation evidence, incl. the 3-layer deployed-behaviour check |
| `execute` | 7–8 | branch + push + **open code PR** | Cleanup, skill suggestions, PR; **stop** |
| `transpile` | — | — | Hand off to the migration transpiler (`references/transpile-handoff.md`) |

## Hard rules

1. **Impact before write.** Build the full inventory, including what re-creates each object (a notebook that scripts the SP reverts your fix), all siblings, and the literal BI source.
2. **Deploy lanes.** Synapse: **every** change goes through a DataPlatform PR. Databricks: views/functions can be deployed without CI/CD; tables need CI/CD.
3. **Schemas:** `DWH_dbo`, `BI_DB_dbo`, `Dealing_*`, `eMoney_dbo`, `DWH_staging`, `Dealing_staging`. Never assume plain `dbo`. Classic etoro ≠ Synapse pool.
4. **Prod repos only:** `eToro/DataPlatform` and `eToro/DE-Marketing`. **Not** Databricks_Knowledge. Open PRs, never merge, never deploy to PROD.
5. **Test locations:** Synapse STG via `deploy.py` (it's cloned on demand, so check data freshness first). UC: the object's `_stg` twin schema (`bi_output` → `bi_output_stg`); if there is no twin, or the schema is prod-only, use `de_output_stg`. **Drop everything you create.**
6. **Dual-platform changes mirror the formula, not the column.** Validate with the 3-layer check: existence via `sys.sql_modules`, a formula diff across platforms, and a behavioural probe on dates where the formulas would disagree.
7. **Partitioning:** if the source is parquet, filter/join on its partition column (PositionPnL → `etr_ymd`). Delta doesn't matter.
8. **No QA scaffolding in the diff.** Debug tables, dumps and columns stay in the run folder.
9. **UC column comments** for every created or changed column: rich and contextual. Append to human-written comments, never overwrite them.
10. **Skills corpus:** never open skills PRs. Write proposed changes to the UC user-suggestion skill table with status `new`.
11. **Backfills are never in a PR.** A backfill is every persistent object downstream of the change, not just the one named — classify each by grain (same-grain = MERGE; aggregated/different-grain = RECREATE, per-date or one-time full-history, never a day loop over all history; passthrough = no effect, state it; stateful-downstream = recurse the classification). Test each on a side table first. See `references/backfill-lineage.md`.
12. **Iterations:** at most 5, and only when something changes between them. Auth, permission and infra failures are not iterations; stop and report.
13. **Models:** reasoning models for design, formulas and parity diagnosis; cheap models for sweeps and counts.
14. **Formula owner:** Guy Manova. Read the procs and wikis first; ask only if they don't settle it.
15. **Dual-platform work** (both Synapse and Databricks in one task): load the `synapse-dbx-crosswalk` skill (UC counterpart resolution, parquet partitioning, T-SQL pitfalls, parity method). Full migrations → `/migration-autoloop`.
16. Decide via `references/dark-factory-decisions.md` and log every decision with its rung.

## References

- `references/process-request-to-pr.md` — **the process (read first)**
- `references/backfill-lineage.md` — backfill classification + worked example
- `references/dark-factory-decisions.md` — the decision ladder
- `references/constitution.md`
- `references/source-registry-template.md`
- `references/synapse-schemas.md`
- `references/skills-corpus.md`
- `references/pr-dataplatform.md`
- `references/test-and-parity.md`
- `references/transpile-handoff.md`
- `references/databricks-dab-uc.md`
- `references/performance-synapse.md`
- `references/procs-etl-idioms.md`
