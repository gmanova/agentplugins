# Performance — Synapse SynapseSQLPool1

## Don't assume a Synapse table's partition scheme carries over to its Databricks mirror

Synapse-side partitioning (e.g. `BI_DB_PositionPnL` genuinely `PARTITION([DateID] RANGE LEFT FOR
VALUES (...))`) is a Synapse-only fact. The Databricks Parquet mirror of the same table is
frequently re-partitioned on a derived `etr_y`/`etr_ym`/`etr_ymd` triplet instead. If you're
authoring a query/proc that runs on the Synapse side, `DateID` joins are fine there — the risk is
specifically when the *same* logic gets ported to the Databricks side (DE-Marketing) and the join
column is copied over unchanged. See `databricks-dab-uc.md` for the full mirror-partitioning
write-up and the fix pattern (`DESCRIBE DETAIL`, join on `etr_ymd` instead).

## A missing rollup view / missing Daily-Panel join is invisible, not just "less optimal"

Not a query-performance issue, but the equivalent failure mode: a `BI_DB_DDR_Fact_*` table with no
per-customer/day rollup view, or a rollup view that exists but isn't joined into
`BI_DB_V_DDR_Daily_Panel`, means the data never reaches Tableau's extract — regardless of how
correct or well-indexed the fact table itself is. Trace the literal `SELECT FROM` chain the BI
tool's extract uses before declaring a DDR feature "done"; see `skills-corpus.md` → "Downstream
reach check."
