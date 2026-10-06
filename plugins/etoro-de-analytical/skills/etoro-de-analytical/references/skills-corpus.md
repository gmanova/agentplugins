# Skills corpus — auto-write surface

Skills are part of this persona’s deliverables, not a follow-up chore.

## When

After `impact` (and again before PR): if schemas/objects/routing/semantics change, compare against `DataPlatform/databricks/data-skills` (and data-rules if present).

## What to detect

- Stale table/SP selection guidance
- Missing FX / instrument / domain fragments
- Broken links to renamed/moved objects
- New entities that need a skill or rule fragment

## What to do

1. Author the skill/rule updates in-repo.
2. Open a PR to the skills path on DataPlatform (unmerged).
3. Cross-link code PR ↔ skills PR in both bodies.

## What not to do

- Do not ask a human to run `/skills-push` or similar.
- Do not skip corpus compare because “it’s only a column.”

## Downstream reach check — before declaring a feature done

Landed 2026-09-28 after the ACATS_IN/ACATS_OUT feature: a correct fact table with the right
columns is NOT the same as "the report can see it." `BI_DB_DDR_Fact_Trading_Volumes_And_Amounts`
had no rollup view and was never joined into `BI_DB_V_DDR_Daily_Panel` — every column on it,
correct or not, was structurally unreachable by Tableau. Before closing out any BI/DDR feature:
trace the FULL path to the literal object the consuming tool's extract/report `SELECT FROM`s, not
just to "a gold/fact table exists." Ask "what does the extract literally select from," not
"does a table with the right shape exist." Same principle for skills/wiki: when a feature spans
multiple objects touched across sessions, after any single object's PR lands, re-check the FULL
original object list before declaring the feature closed — reporting "I fixed the one thing I was
already looking at" is not the same as "every deploy-with-no-IaC gap is closed." Re-derive that
list from the objects actually deployed, don't rely on remembering it from earlier in a long
thread.

## Keep UC comments current, not just present

A UC column comment that was correct when written can drift stale the moment the underlying
`CASE WHEN` logic changes — e.g. a guard clause added to fix a false-positive bug landed on one
view's comment but not on a sibling view's copy of the same flag. Comment presence is not the bar;
comment-matches-current-logic is. When a bug-fix changes a column's formula, grep every UC object
carrying that column name (not just the one you were editing) and check its comment still matches.
