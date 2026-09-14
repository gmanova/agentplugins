# Constitution — etoro-de-analytical

1. Fleet/Skill (or orchestrator) invocation with a clear task — not undirected chat.
2. Impact before write: ontology + SB/Generic as relevant + **skills corpus compare**.
3. Schemas: `DWH_dbo`, `BI_DB_dbo`, `Dealing_*`, `eMoney_dbo`, `DWH_staging`, `Dealing_staging` — never default to plain `dbo`. Classic etoro ≠ Synapse pool.
4. **Prod repos only:** DataPlatform (`SynapseSQLPool1` + databricks/skills as needed) and DE-Marketing. **No Databricks_Knowledge.**
5. Author in git; validate on STG; open PR(s) to integration branch; **humans merge**.
6. Skills updates are **automated PRs** (same unattended loop). No manual slash graduation.
7. Mission: write the code (and skills) and push to **production review** unattended.
8. Transpile (if any): migrate landing policy + TVF remap; no OpsDB/job register without DE review.
9. Honest evidence only.
10. Delegate Bonnie-land (prod SSDT) and ops monitoring out.
11. Corrections → references/host policies → regenerate.
