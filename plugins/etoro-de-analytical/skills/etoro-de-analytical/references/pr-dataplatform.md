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

## DE-Marketing branch naming — check recent PRs, don't default to `fix/...`

DE-Marketing's actual convention is `<type>/DSM-NNNN_slug` (examples: `Bug/dsm-2870_Risk_
classification_merge_failure`, `feature/DSM-3130-AppsFlyer_NewApps_eToro_AI`), even with no real
Jira ticket — a `DSM_<slug>` placeholder branch name matching the visual prefix is acceptable
without one. Before opening a DE-Marketing PR, check recent branch/PR names for this pattern and
match it. GitHub does not allow renaming an open PR's head branch — if you opened one with the
wrong convention, the fix is: rename local branch, push new branch, close the old PR referencing
the new one, delete the old remote branch, open a fresh PR. Don't try to work around this any
other way.
