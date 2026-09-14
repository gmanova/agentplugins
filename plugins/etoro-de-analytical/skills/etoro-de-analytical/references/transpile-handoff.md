# Transpile handoff

Use only when the task is Synapse→Databricks migrate under **DataPlatform** policy.

## Locks

- Prefer existing UC views/TVFs (`main.etoro_kpi_prep.*`); **no `_foundation_*` clones** of BI_DB TVFs.
- Migrate landings: `dwh_daily_process.bi_db_migration` (or current DataPlatform standard) — not ad-hoc catalogs.
- **No OpsDB / job registration** until DE review (`*_registration_withheld`).
- Synapse read-only for runtime; author SSDT in DataPlatform git.
- Parity: money/row sums on a locked business date; honest tags only.

## Out of scope for paths

Do not require `Databricks_Knowledge` audits/worktrees. If Migration Transpiler teammate is used, hand off with DataPlatform-relative paths and PR targets only.
