# Host binding — DE analytical persona

## Program

- Name:
- In-scope schemas: DWH_dbo, BI_DB_dbo, Dealing_*, eMoney_dbo, DWH_staging, Dealing_staging, …
- Repos: DataPlatform (SynapseSQLPool1 + databricks/data-skills), DE-Marketing

## Out of scope

- Databricks_Knowledge and other lab repos
- Manual slash graduation

## Mission

Unattended: implement + open code/skills PRs for human merge.

## Local machine bindings (fill in per person, per machine — never edit the shared skill files for this)

- Databricks CLI profile name(s) for prod / DE-STG: ______ / ______
  (referenced generically as `<your-profile>` in `references/databricks-dab-uc.md` — that file
  is never supposed to name a specific profile)
- MCP connector in use for Databricks (if any), and its actual tool names: ______
  (the write-tool-lockout lesson in `databricks-dab-uc.md` generalizes across connectors; the
  literal tool names it shows are one worked example, not this program's contract)
- OS / shell for any local automation you build on top of this persona (PowerShell, bash, etc.):
  ______ — note that `tools/lesson_sync/` in the `Databricks_Knowledge` lab repo is a
  Windows-only, single-machine example of "auto-fold new lessons into this plugin" and is not
  part of this plugin; it does not travel with a copy of this directory.
