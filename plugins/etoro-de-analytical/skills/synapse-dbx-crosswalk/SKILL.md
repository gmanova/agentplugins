---
name: synapse-dbx-crosswalk
description: >-
  Cross-platform knowledge for changing a data object on BOTH Azure Synapse
  (DataPlatform SynapseSQLPool1: DWH_dbo, BI_DB_dbo, Dealing_*, eMoney_dbo,
  DWH_staging, Dealing_staging) and Databricks Unity Catalog in the same task.
  Covers: resolving a Synapse table to its UC counterpart (generic pipeline /
  gold naming, provenance, freshness), Synapse external (parquet) tables and
  partition columns, Lakebridge/BladeBridge T-SQL→Databricks SQL pitfalls, and
  the cross-platform parity method. Use when editing a Synapse object and its
  Databricks sibling together, tracing Synapse→UC lineage, debugging a parity
  mismatch, or hand-porting a T-SQL snippet. Do NOT use for a full pipeline/ADF
  migration cutover or multi-day autoloop run; that stays with /migration-autoloop.
---

# synapse-dbx-crosswalk

This skill is knowledge only and has no side effects. It informs decisions that you then carry out through `etoro-de-analytical` and your normal Databricks/Synapse tooling.

## Inline vs. hand off to the transpiler

**Handle inline with this skill:**
- Resolve one Synapse table or SP to its UC counterpart, or the reverse.
- Diagnose one parity mismatch between a Synapse object and its UC sibling.
- Port a small T-SQL snippet or formula by hand as part of a larger change (e.g. ACATS: the same formula in a Synapse TVF and a Databricks view).
- Decide whether a source's partition column matters for a query.

**Hand off to `/migration-autoloop` (the migration-transpiler harness):**
- Migrating a whole ADF pipeline or SP end to end, with its own QA-parity gate and registry tracking.
- Anything needing the `migration_tables` / `migration_parallel` quarantine schemas, ring sequencing, or multi-day orchestration.
- A change big enough to need its own `seeds/adf_pipelines.csv` entry.

Rule of thumb: if you'd need to run a script from `tools/migration_autoloop/`, it's a migration, so hand off. If the question is "what's the UC name for this" or "why do the two platforms disagree", use this skill.

When you do run the transpiler on a snippet, its output is a **draft**. Review it against `references/tsql-to-dbsql-pitfalls.md` before trusting it.

## 1. Synapse table → UC counterpart

Full recipe: `references/generic-pipeline-and-freshness.md`.
0. **Is it a Synapse external table, i.e. lake-sourced?** Check this first, with a cheap `git grep "CREATE EXTERNAL TABLE [<Schema>].[<Table>]"` in DataPlatform `SynapseSQLPool1/sql_dp_prod_we`. Names don't reveal it; `Dealing_staging` alone has 326. If it is external, it is **not** in the generic pipeline by design: read `DATA_SOURCE` + `LOCATION` for the lake path and resolve UC from that path. See `references/external-tables-and-partitioning.md` §A.
1. Otherwise, start from the naming convention: `<SCHEMA>.<Table>` → `main.<schema_lower>.gold_sql_dp_prod_we_<schema_lower>_<table_lower>`; `BI_DB_dbo.SP_DDR_X` → `main.de_output.sp_ddr_x`. Exceptions exist, so don't fuzzy-match.
2. Confirm the object exists via `system.information_schema.tables` / `routines`. `SHOW FUNCTIONS` misses `CREATE PROCEDURE` objects.
3. **Confirm provenance.** The `gold_sql_dp_prod_we_*` prefix covers both real Synapse mirrors and native Databricks builds (all DDR gold tables are native). Check which job populates the table.
4. Check whether the export for *this table* is active (`Is_Active` in OpsDB). Activation is per table.
5. A Synapse object can have **no** UC sibling. The 7 `Function_DDR_Aggregation_*` functions were never ported.

## 2. External tables and partitioning

Full detail: `references/external-tables-and-partitioning.md`.
- **§A, lake-sourced:** external tables (468 in BI_DB_dbo, 326 in Dealing_staging, and more) read from the lake, so they are never exported. 122 SPs create external tables dynamically. CETAS inside an SP is the reverse: Synapse *writes* to the lake.
- **§B, partition rule:**
  1. Is the source parquet? Check `DESCRIBE DETAIL` → `format`.
  2. If it's parquet, filter/join on its partition column. Example: PositionPnL → `pnl.etr_ymd = to_date(CAST(v.DateID AS STRING),'yyyyMMdd')`.
  3. If it's Delta, partitioning doesn't matter.
- `dim_position.etr_ymd` is **not** the event date. Never filter dim_position on it.

## 3. T-SQL → Databricks SQL pitfalls

Full list: `references/tsql-to-dbsql-pitfalls.md`. The ones that bite most:
- `CONVERT` style codes are dropped.
- ISNULL vs COALESCE typing.
- `INT/INT` truncation is lost on Databricks.
- APPLY → LATERAL.
- TVF parameters defeat pruning.
- `CREATE FUNCTION` eager-plans the body.
- No JOIN directly after `LATERAL VIEW`.
- `#temp` tables.
- Dynamic SQL and cursors.

## 4. Parity method

Full method: `references/parity-method.md`.
- Lock one business date.
- Compare money sums and key counts by dimension.
- Use NULL-safe comparisons.
- Explain every delta.
- **Never assume Synapse is truth.**
- Choose probe dates where the competing formulas would *disagree*.
- Check for `dim_position` mirror gaps before blaming logic.

## References

- `references/generic-pipeline-and-freshness.md`
- `references/external-tables-and-partitioning.md`
- `references/tsql-to-dbsql-pitfalls.md`
- `references/parity-method.md`
