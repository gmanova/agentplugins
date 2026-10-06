# T-SQL → Databricks SQL: Lakebridge/BladeBridge pitfalls

Sources:
- the BladeBridge config reference (`knowledge/lakebridge/bladebridge-configuration.md`);
- the eToro migration profile (`proposals/synapse-migration-profile-for-databricks-consultants-2026-06-08.md`);
- Databricks gotchas found live during the ACATS work.

Treat transpiler output as a draft. Every item below is a manual-review checkpoint.

## Substitutions the transpiler makes, and where they break

1. **ISNULL → COALESCE.** BladeBridge renames it mechanically, but the semantics differ. `ISNULL` returns the type/length of its *first* argument; `COALESCE` resolves to the highest-precedence type across all arguments. This can silently widen or change the type of a computed column, so check the types on business-critical conversions.

2. **CONVERT(type, expr, style) → CAST(expr AS type), and the style is dropped.** The template `CAST($2 AS $1)` has no slot for `style`, so a format such as `CONVERT(VARCHAR(8), @date, 112)` (yyyymmdd) is lost. Rewrite by hand with `date_format()`.

3. **Integer division changes meaning.**
   - T-SQL `INT / INT` **truncates** (`5/2 = 2`). Databricks SQL `/` **does not**: it returns a fractional result (`5/2 = 2.5`); use `div` for integer division.
   - Ported code that relied on truncation silently changes results. Bucketing, `DateID/100` to get a month, and percent calculations are typical cases.
   - Code that already casts to decimal (`1.0 *`, `CAST … AS DECIMAL`) is safe on both sides. Don't strip those casts during review.

4. **OUTER APPLY / CROSS APPLY → `LEFT JOIN LATERAL (...) ON true` / `JOIN LATERAL (...)`.** Spark SQL has no APPLY. It's in active use: 23 Synapse procs, e.g. `SP_AML_BI_Alerts_New`, `SP_CID_DailyPanel_Club`, `SP_Deposit_Reversals_PIPs`. This is a restructuring, not a rename, so verify every one.

5. **Inline TVFs** (`RETURNS TABLE AS RETURN (SELECT ...)`) are common in the source, e.g. `Function_Trading_Volume_PositionLevel` and `Function_AUM_OptionsPlatform`. On Databricks:
   - **SQL TVF parameters can't be folded at plan time.** A body that filters a partition column by the parameter full-scans the source (measured at 200s+ for a single-partition read). For date-scoped logic, substitute the date as a literal (`EXECUTE IMMEDIATE` or caller templating) rather than relying on the parameter.
   - **`CREATE OR REPLACE FUNCTION` cost-plans the whole body at DDL time.** It took about 8 minutes on a full-history parquet view. It looks hung, but it's a one-time cost.
   - Some Synapse TVFs have **no UC port**: the 7 `Function_DDR_Aggregation_*` functions. Check whether a view re-derives the logic instead.

6. **No JOIN directly after `LATERAL VIEW`** (you get `PARSE_SYNTAX_ERROR at 'LEFT'`). Put the `LATERAL VIEW explode(...)` in its own CTE, then JOIN in the outer query.

7. **TOP (n) → LIMIT n.** T-SQL allows `TOP … ORDER BY` inside derived tables. Add an explicit, deterministic tiebreak when porting, since a bare `TOP` was already nondeterministic. *(General dialect knowledge; no eToro incident on record yet.)*

8. **`#temp` tables** (673 occurrences in DataPlatform SQL) have no direct equivalent:
   - read-only, session-scoped use → `CREATE OR REPLACE TEMPORARY VIEW`;
   - multi-pass mutation (INSERT then UPDATE) → restructure into chained CTEs, or use a real scratch Delta table and drop it afterwards.

   A temp view can't be mutated. Shared scratch tables (e.g. `_tmp_ddr_pop`) break concurrent runs, so run serially.

9. **Dynamic SQL (`sp_executesql`), cursors, TVPs and `RAISERROR`** make up the biggest manual-remediation bucket across the 1,283 Synapse SPs. No mechanical rule covers them, so always hand-review.

## NULL semantics in parity checks

`CASE WHEN a = b THEN 'PASS' ELSE 'FAIL' END` returns `FAIL` when either side is NULL. That includes `SUM` over an empty set. Use `a IS NOT DISTINCT FROM b`, or `COALESCE(a,0) = COALESCE(b,0)` when 0 is a safe default.

## Type mapping (eToro convention, June 2026 profiler)

| Synapse | Databricks | Note |
|---|---|---|
| `money` / `smallmoney` | `DECIMAL(19,4)` | Verify every transpiled money column's width |
| `datetime` / `datetime2` | `TIMESTAMP_NTZ` | Synapse has no timezone; be consistent |
| `tinyint` | `SMALLINT` | No `TINYINT` on Databricks |

## Table-specific checks on every port

- `dim_position.etr_ymd` is not the event date; filter on `OpenDateID` / `CloseDateID`.
- Parquet sources must be filtered/joined on their partition column (see `external-tables-and-partitioning.md`).
- Write explicit column lists in INSERTs. `SELECT *` into a Databricks table caused positional column misalignment in DDR (2026-09-28).
