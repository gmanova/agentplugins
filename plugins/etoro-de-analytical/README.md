# etoro-de-analytical

DE/BI-hybrid persona for **prod** analytical work:

- `eToro/DataPlatform` → `SynapseSQLPool1/sql_dp_prod_we` (+ data-skills)
- `eToro/DE-Marketing`

**Mission:** unattended code + skills PRs to production review (humans merge).

**Not in scope:** Databricks_Knowledge lab, Bonnie prod SSDT, ops-only monitoring.

See `DE-ANALYTICAL-PERSONA-PLAN.md` for the full design.

## What ships with this plugin vs. what's local to one machine

Everything under `plugins/etoro-de-analytical/` is meant to be portable — copy this directory to
share the persona with someone else. Before you do, know the two seams where a specific person's
setup leaks in, and fix/fill them per `host-binding/profile-template.md` rather than assuming they
carry over:

1. **Databricks CLI profile names** (e.g. `DEFAULT`, `dbx-de-stg`, or whatever's in your own
   `~/.databrickscfg`) are never hardcoded in these reference files — they're written as
   `<your-profile>` placeholders on purpose. Fill in your own via `host-binding/profile-template.md`.
2. **MCP connector/tool names** (e.g. a `databricks_sql_execute_sql`-style tool) depend on which
   MCP server is configured for the sharing recipient. The *lessons* about MCP write-tool
   behavior generalize; the literal tool names in `databricks-dab-uc.md` do not — treat them as
   one worked example, not a contract.

**NOT part of this plugin, do not assume it ships with it:** `tools/lesson_sync/` (a separate
directory in the `Databricks_Knowledge` lab repo, one level up from here) is a Windows-only,
absolute-path, single-machine automation — a PowerShell script + a Windows Scheduled Task that
watches one person's local Claude Code memory folder and feeds new lessons back into this plugin.
It will not run, and isn't meant to run, anywhere but the machine it was set up on. If you want the
same "lessons keep landing here automatically" behavior elsewhere, that mechanism needs to be
rebuilt for the new environment (different OS scheduler, different memory-folder path, different
`claude` binary location) — copying the `.ps1` file alone will not work.
