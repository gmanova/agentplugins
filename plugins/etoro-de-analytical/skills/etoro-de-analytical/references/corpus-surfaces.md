# Corpus surfaces — all three are deliverables

"The corpus" is not one thing. A semantic change to an analytical object lands on **three** documentation surfaces, and all three are part of the same change-set, not follow-up chores. Missing one ships a codebase that contradicts its own documentation.

| Surface | Where it lives | How it ships | Reader |
|---|---|---|---|
| **Skills corpus** | `DataPlatform/databricks/data-skills/skills/**` (+ `data-rules` if present) | PR to DataPlatform, automated | AI assistants + analysts routed through them |
| **Semantic wiki** | the lab repo's `knowledge/synapse/Wiki/<schema>/<type>/<Object>.md` (+ `.lineage.md`) | lab-repo edit; the `.md` is the authored source | humans reading object docs |
| **UC column comments** | `<Object>.alter.sql`, **generated from** the wiki `.md` | regenerate, then deploy to Unity Catalog | anyone running `DESCRIBE`, plus Genie/assistant grounding |

## Order of operations

1. **Wiki `.md` first** — it is the source of truth that the comments are generated from. Edit Section 4 / Elements (or whatever the object's column catalogue is called), plus any prose or query-advisory section that states the old rule.
2. **Regenerate the alter script — never hand-edit it.** These files carry a `-- Generated: … | <tool>` header. There is a targeted regeneration tool in the lab repo (`tools/regenerate_alter_for_files.py <paths>`); it rewrites only the column-comment block and preserves header, table comment, tags and execution footer. Verify with the parity auditor (`tools/audit_wiki_alter_comment_parity.py --under <schema>`) — the object should come back clean.
3. **Deploy the comments** only when the code change actually lands. Comments that describe unmerged behaviour are worse than stale ones.
4. **Skills corpus** in the same change-set, as its own PR, cross-linked to the code PR.

## What to look for on each surface

Don't just find the changed identifier — find every **statement of the rule**, wherever it is phrased:
- the column's own description/comment (the derivation, usually quoted as a `CASE`)
- query-advisory tables ("to find X, filter `…`")
- prose in the overview/row-scale sections that characterises the data
- worked SQL examples and their inline comments
- KPI/recipe catalogues, which often restate the rule in business language
- *quantified claims* — cross-tabs, percentages, row/dollar counts. These are the most dangerous: they look authoritative and they silently stop being true. If a change invalidates a published number, **re-measure it**; never leave it, and never guess a replacement.

## Generated vs authored — check before editing

Some trees are exports, not sources. `git log --format='%an' -50 -- <path> | sort | uniq -c`: a bot dominating means the tree is regenerated, often by wiping and rewriting, so an edit there is deleted rather than merely inert. Discovery dumps, column-lineage JSON, Tableau custom-SQL captures and UC schema exports are all evidence, not edit targets — they re-materialise correct once the real change lands. See `databricks-dab-uc.md`.

## Forks of the same corpus

A lab copy of a corpus that also exists in the prod repo will drift, and a drifted hub can end up citing a sub-skill that now says the opposite. Treat the prod repo as source of truth, check whether a lab fork exists before editing either, and don't fix a stale fork by hand — raise whether it should be re-synced or replaced by a pointer.
