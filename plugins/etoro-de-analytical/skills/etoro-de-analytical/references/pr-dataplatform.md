# PR expectations — unattended review path

## Repos

- `eToro/DataPlatform` — SynapseSQLPool1 SSDT and/or `databricks/data-skills` (and related databricks paths)
- `eToro/DE-Marketing` — when the change belongs there

## Rules

- Base: `dev` (or repo default integration branch).
- Branch naming: `cursor/<slug>` or fleet convention.
- Title: include Jira key when known.
- Body: impact summary, skills corpus hits, STG evidence, open questions.
- **Open PR and stop. Never merge** (DataPlatform, DE-Marketing, skills paths).
- Skills corpus changes → open skills PR automatically (do not require `/skills-push` or any manual graduation command).
- Prefer one logical change-set; split code vs skills PRs if CI/ownership demands it — both still automated.
