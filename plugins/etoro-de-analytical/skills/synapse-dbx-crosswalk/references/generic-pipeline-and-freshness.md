# Generic pipeline mapping and freshness

## What the "generic pipeline" is

The generic pipeline is eToro's standard Synapse → data-lake export. Its config lives in **OpsDB**, a separate Azure SQL database (DataPlatform path `SynapseSQLPool1/opsdb-dataplatform-prod-we/`):

- **`OpsDB.dbo.generic_inc_process_config`:** the activation table. Column `Is_Active` (bit); history is kept in the temporal table `History.generic_inc_process_config`.
- **`OpsDB.dbo.SQLSources_Config`:** the read surface.
- **`dbo.v_TableStatusConfiguration`:** the health/freshness surface (`.../dbo/Views/dbo.v_TableStatusConfiguration.sql`).
  - It joins `SQLSources_Config` to `dbo.DataLakeTableStatus`.
  - It reports `FrequencyMinute` (expected cadence; default 1440 = daily) and `CreationTimestamp` per table.
  - `SP_Generic_Alerts_*` read from it.
- **Direct access:** Key Vault `kv_dataplatform`, secret `operationsDB-connectionString`.
- **UC workaround mirror:** `main.general.bronze_opsdb_dbo_sqlsources_config`. Its sibling `bronze_opsdb_dbo_vw_unitycatalog_mapping_tables` has column drift (stale headers), so read it positionally.

**Activation is per table, not global.** Seven DDR tables plus Customer_Periodic_Status were set to `Is_Active=0` (2026-07-21 and 08-18), while 278+ other rows remain active and run daily. Never say "the export is off" in general; say it per table.

## Naming convention: Synapse object → UC counterpart

- `Synapse <SCHEMA>.<Table>` → `main.<schema_lower>.gold_sql_dp_prod_we_<schema_lower>_<table_lower>`
- `BI_DB_dbo.SP_DDR_X` → `main.de_output.sp_ddr_x`

**Known exceptions:**
- `SP_DDR_Fact_Fact_MIMO_AllPlatforms` (the source name doubles `Fact_`) → `sp_ddr_fact_mimo_allplatforms`.
- The SCD table is spelled `dailystatus`, not `Daily_Status`.
- `main.etoro_kpi_prep.gold_de_user_dim_ddr_customer_dailystatus_scd` doesn't follow the convention at all.
- These were **never ported**:
  - 10 Synapse DDR SPs, including all three `SP_DDR_Fact_MIMO_*_Platform`, `SP_DDR`, `SP_DDR_Aggregated` and `SP_DDR_Process_Monitor`;
  - all 7 `Function_DDR_Aggregation_*` TVFs.

  The UC view layer (`main.etoro_kpi.ddr_*_v`) sometimes re-derives the same logic itself instead.

## Provenance: the prefix can mislead

`gold_sql_dp_prod_we_*` covers two different kinds of table:
- **Real Synapse-ETL mirrors,** e.g. `..._positionpnl`: parquet, partitioned on `etr_*`.
- **Native Databricks builds that kept the legacy name.** All DDR gold tables are native: they run under job `5263962954799003`, and their Delta history shows a real `SP_DDR_*` job as author.

Before assuming a mirror or dual-writer relationship, check who populates the table. Use `system.information_schema.routines` or the Delta history author.

Consequence: Synapse DDR and Databricks DDR run **independently**. A formula change must land on both platforms (see the mirror rule in `etoro-de-analytical`).

## Migration-POC mapping (a different surface)

The migration-autoloop POC only uses `dwh_daily_process.qa.gold_phase_table_mapping` (`migration_table_name`, `gold_table_name`, `is_active`), read by `tools/migration_autoloop/evaluate_proc_parity.py::_mapped_tables`. Don't use it for general Synapse → UC resolution.

## Freshness: two independent signals

1. **OpsDB cadence:** `v_TableStatusConfiguration.FrequencyMinute` plus `CreationTimestamp`, i.e. "is this table late against its own SLA?"
2. **Migration-autoloop signals** (`tools/migration_autoloop/freshness.py`):
   - `bronze_ready(target_date, proc_names)`: every required `daily_snapshot` partition is present and non-empty.
   - `gold_state(gold_table, target_date, date_column=None)` works through three tiers:
     - (a) `etr_ymd = target_date` row count > 0;
     - (b) if there's no `etr_ymd`, `MAX(date_column) >= target_date_id`;
     - (c) otherwise, the latest Delta-history commit date. Tier (c) fails with `DELTA_ONLY_OPERATION` on a parquet external table; use OpsDB for those.

Also: Synapse **STG** is cloned on demand, not nightly, so check `MAX(DateID)` of each source before testing there.

## Resolution recipe

0. **External-table check first:** grep DataPlatform for `CREATE EXTERNAL TABLE [<Schema>].[<Table>]`. If it is external (lake-sourced), it is NOT in the generic pipeline by design; resolve UC from its `LOCATION` path instead (`external-tables-and-partitioning.md` §A).
1. Apply the naming convention for a first guess.
2. Confirm existence and object type via `system.information_schema.tables` / `routines`. `SHOW FUNCTIONS` / `DESCRIBE FUNCTION` only see `routine_type='FUNCTION'`.
3. Confirm provenance: mirror or native build.
4. Check `Is_Active` in OpsDB if the question is specifically whether the export is running.
