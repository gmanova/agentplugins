# Synapse analytical schemas (sql_dp_prod_we)

SSDT root: `eToro/DataPlatform/SynapseSQLPool1/sql_dp_prod_we/`

## Never assume plain `dbo`

Classic `etoro` SQL host ≠ Synapse dedicated pool. Schema names are first-class.

## In-scope (explicit)

| Schema | Role |
|--------|------|
| `DWH_dbo` | Core DWH dims/facts |
| `BI_DB_dbo` | BI / analytical marts & reporting SPs |
| `Dealing_dbo` / `Dealing_*` | Dealing analytical |
| `eMoney_dbo` | eMoney analytical |
| `DWH_staging` | DWH prep / staging |
| `Dealing_staging` | Dealing prep / staging |

## Adjacent (only when impact requires)

`BI_DB_staging`, `DWH_Migration`, `BI_DB_Migration`, `DE_dbo`, `CopyFromLake*`, `EXW_*`, other `eMoney_*`, `Dealing_temporary`, etc.

## Second prod repo

`eToro/DE-Marketing` — domain SP/DDR and related analytical SQL (paths per that repo). Not SynapseSQLPool1, but in-scope for this persona.
