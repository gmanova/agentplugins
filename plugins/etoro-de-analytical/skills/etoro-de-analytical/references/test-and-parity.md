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

## CI awareness (DataPlatform)

Expect humans to run/observe: `ci-synapse`, `databricks-ci` / asset-bundle validate, `skills-ci` when skills touched. Don’t claim CI green without evidence.
