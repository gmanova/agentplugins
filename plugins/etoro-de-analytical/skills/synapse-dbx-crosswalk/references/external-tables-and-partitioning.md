# Synapse external tables (lake-sourced) and partitioning

## A. Lake-sourced tables: check this FIRST for every Synapse source

**Synapse external tables read from the data lake.** The data already lives in the lake, so by design these tables are **not** in the generic pipeline and are **not** exported to the lake. Don't look for an OpsDB `generic_inc_process_config` row, and don't expect a `gold_sql_dp_prod_we_*` mirror produced by the export. Find the lake path instead, and from it the UC object that reads the same files.

**Names don't tell you.** Many have no "External" in the name, especially in `Dealing_staging`, e.g. `Dealing_staging.CopyFromLake_etoro_Hedge_ExecutionLog` and `Dealing_staging.Dealing_DUCO_Status`.

### Detection: a cheap repo grep, done in the Stage 1 inventory

Everything is in the DataPlatform repo under `SynapseSQLPool1/sql_dp_prod_we/`. Use `git grep`, not ripgrep, which times out on this repo.

```bash
# Is object X an external table?  (folder + DDL keyword)
git -C DataPlatform grep -l -i "CREATE EXTERNAL TABLE \[<Schema>\]\.\[<Table>\]" origin/dev -- SynapseSQLPool1/sql_dp_prod_we
# Its lake path (LOCATION) and container (DATA_SOURCE):
git -C DataPlatform show "origin/dev:SynapseSQLPool1/sql_dp_prod_we/<Schema>/External Tables/<Schema>.<Table>.sql" | grep -i -E "LOCATION|DATA_SOURCE|FILE_FORMAT"
# SPs that (re)create external tables dynamically (dated paths, CETAS):
git -C DataPlatform grep -l -i "CREATE EXTERNAL TABLE" origin/dev -- 'SynapseSQLPool1/sql_dp_prod_we/*/Stored Procedures/*'
```

Footprint on `origin/dev` (2026-10-06):

| Location | Count |
|---|---|
| `BI_DB_dbo/External Tables` | 468 |
| `Dealing_staging/External Tables` | 326 |
| `dbo/External Tables` | 59 |
| `DWH_dbo/External Tables` | 22 |
| `eMoney_dbo/External Tables` | 18 |
| `Dealing_dbo/External Tables` | 8 |
| SPs containing `CREATE EXTERNAL TABLE` (80 of them in `Dealing_staging`) | 122 |

To confirm live on Synapse: `sys.external_tables` joined to `sys.external_data_sources` (gives the `location`).

### Reading the lake path

```sql
CREATE EXTERNAL TABLE [Dealing_staging].[CopyFromLake_etoro_Hedge_ExecutionLog] (...)
WITH (DATA_SOURCE = [internal-sources],
      LOCATION = N'Bronze/etoro/Hedge/ExecutionLog/etr_y=2025/*',
      FILE_FORMAT = [SynapseParquetFormat], ...)
```

- **Full path** = the data source's root + `LOCATION`.
- **Data sources** (by count of external-table DDLs): `internal-sources` 602, `dealing_trigger_from_synapse` 216, `analysis` 25, `export` 17, `external-sources` 8, `tmp_databricks_` 8, plus a few `*_dldataplatformprodwe_*` variants.
- The data-source DDL isn't in the repo as a file. Dynamic SPs show the pattern `abfss://<container>@dldataplatformprodwe.dfs.core.windows.net`, e.g. `internal-sources` → container `internal-sources`. Confirm via `sys.external_data_sources`.
- **`LOCATION` reveals the layer and source system:** `Bronze/<sourceDB>/<schema>/<table>/…`. On Databricks, look for the UC table (usually `bronze_*` or a mirror) or volume that reads the same path.
- Some locations pin a partition, e.g. `etr_y=2025/*`. The Synapse table then covers only that slice, and the UC counterpart may hold more.

### What to do with a lake-sourced source

1. **Don't** add it to, or look for it in, the generic pipeline export. It's already in the lake.
2. Resolve the UC counterpart from the **lake path**, not from the gold naming convention.
3. Its freshness is whatever lands the files (an upstream ingestion), not the OpsDB export cadence.
4. A dynamic-SP external table (a dated path, re-created per run) depends on that SP's run. Record the SP as the re-creator in the inventory.
5. **CETAS** (`CREATE EXTERNAL TABLE … AS SELECT` inside an SP; 17 seen) goes the other way: Synapse **writes** to the lake. Those paths are *outputs*; a Databricks consumer may read them.
6. The files are parquet, so the partition rule (B) applies to the Databricks side.

## B. Partition rule (owner: Guy Manova)

1. **Check whether the source is parquet:** lake files, a Synapse external table, or a non-Delta UC table. In UC, check `DESCRIBE DETAIL` → `format`, `partitionColumns`.
2. **If it's parquet:** filter/join on its partition columns, usually `etr_y`/`etr_ym`/`etr_ymd`. Otherwise there's no pruning and the scan is unbounded.
3. **If it's Delta:** partitioning doesn't matter.

**Incident (ACATS, 2026-09):**
- Synapse `BI_DB_PositionPnL` is range-partitioned on `DateID`.
- Its UC mirror `main.bi_db.gold_sql_dp_prod_we_bi_db_dbo_bi_db_positionpnl` is **parquet** partitioned on `(etr_y, etr_ym, etr_ymd)`. `etr_ymd` is a `DATE`, 1:1 with DateID.
- The fix:

```sql
pnl.DateID = v.DateID                                   -- Synapse-valid, full scan on the UC parquet mirror
pnl.etr_ymd = to_date(CAST(v.DateID AS STRING), 'yyyyMMdd')  -- correct
```

**Counter-example:** `dim_position.etr_ymd` is **not** the event date. Filtering on it drops the CLOSE leg: 16 rows become 0. Filter dim_position on `OpenDateID` / `CloseDateID`. Whether `etr_ymd` is the right key is a per-table fact.

**Freshness:** parquet has no Delta history, so `DESCRIBE HISTORY` checks fail (`DELTA_ONLY_OPERATION`).
