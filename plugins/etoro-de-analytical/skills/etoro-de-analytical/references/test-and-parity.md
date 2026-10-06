# Test and parity bar

## Before PR (`dev`/`execute`)

- [ ] Evaluator subagent PASS on domain refs applied
- [ ] SSDT scripts re-runnable (CREATE OR ALTER / guarded DDL)
- [ ] STG smoke: proc/TVF executes for a sample date (or documented blocker)
- [ ] Impact report attached / linked
- [ ] No secrets in files

## Transpile / migrate

- [ ] Money column sums + key counts vs Synapse (or classic host if that’s the source)
- [ ] TVF remap verified (no rogue `_foundation_*`)
- [ ] Status tag set; registration withheld

## Validation depth (learned 2026-09-28)

- [ ] Any reason-code/flag-based metric cross-checked against a relevant dimension (e.g.
      instrument type), not validated on row count / volume alone — a majority-class false
      positive can look perfectly plausible while being wholly wrong.
- [ ] A live-fixed notebook-owned SP/table re-verified against the known test case if any
      meaningful time passed since the fix and its PR hasn't merged — silent reverts look
      identical to the original bug.
- [ ] For DDR/BI features specifically: the full path to the actual consuming report/extract
      traced (see `skills-corpus.md` → "Downstream reach check"), not just "a table with the
      right columns exists."

## CI awareness (DataPlatform)

Expect humans to run/observe: `ci-synapse`, `databricks-ci` / asset-bundle validate, `skills-ci` when skills touched. Don’t claim CI green without evidence.
