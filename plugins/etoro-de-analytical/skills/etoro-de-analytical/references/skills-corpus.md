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
