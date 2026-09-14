# Source registry template

Host: `.claude/de-analytical/source-registry.md`

## Required — prod code

| Source | Kind | Purpose |
|--------|------|---------|
| eToro/DataPlatform | git | `SynapseSQLPool1/sql_dp_prod_we/**`, `databricks/` (DE + data-skills) |
| eToro/DE-Marketing | git | Marketing/DDR analytical SPs and related |

## Required — impact / evidence

| Source | Kind | Purpose |
|--------|------|---------|
| eToro/data-ontology | MCP | vault_impact / lineage / resolve |
| eToro/mcp-dataplatform | MCP | sb_*, generic_*, uc_*, dbx_* |
| synapse_sql (STG) | MCP | Staging validate |
| DataPlatform `databricks/data-skills` | git path | Skills corpus compare + auto PR |

## Soft

| Source | Kind | Purpose |
|--------|------|---------|
| Atlassian | MCP | Jira DA/DSM/… |
| synapse_prod_sql | MCP | Prod read-only |
| Migration Transpiler agent | teammate | transpile handoff only |

## Out of scope (do not bind)

| Source | Why |
|--------|-----|
| guyman-tr/Databricks_Knowledge* | Lab — not this project |
| Manual slash graduation (`/skills-push`, etc.) | Graduation = automated PR open, not a human command |

Degradation: if a required source is down, record gap and STOP on write/PR modes.
