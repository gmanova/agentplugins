# Dark factory: from request to opened PR (DRAFT v0.2, 2026-10-06)

This is the end-to-end process for an agent working on a data change, from the moment it gets a request until a PR is open. It is built from the ACATS retro (Databricks_Knowledge `audits/retro/2026-10-06-acats-dark-factory-lessons.md`) and the decision ladder (`dark-factory-decisions.md` (this folder)).

**Scope.** The process stops at "PR opened". Merging and deploying to PROD are human-gated and come after it. Backfills are not part of the PR (see Stage 7b).

**v0.2.** Incorporates Guy's review of v0.1. All v0.1 ❓ points are now resolved and listed at the end.

**v0.2.1.** Corrects the backfill model (Stage 2, Stage 7b) — see `references/backfill-lineage.md` (this folder).

---

## Principles

1. **Operating mode is chosen at kickoff:**
   - **Interactive simulation:** the current default. The agent stops for evaluation at defined checkpoints.
   - **Full dark mode:** the agent runs unattended from kickoff to PR. This is the target, but the agent is not good enough for it yet.
2. **Nothing counts as "done" until a check independent of the agent's own code confirms it.** That means a row count, a duplicate-key check, a cross-platform comparison, or the stored definition text. The agent's own report does not count.
3. **Track four states per object:** repo, PR branch, test environment, PROD. Each is checked separately. One state never implies another.
4. **No production writes before the PR.** Testing happens in Synapse STG and in `_stg` schemas in UC (Stage 5).
5. **Everything that runs is saved first.** SQL gets written to a repo path before it executes. Nothing that matters lives only in the scratchpad.
6. **Leave no garbage.** Every test object and side table the run creates is dropped before the PR, and each drop is recorded.
7. **Match the model to the job.** Use reasoning models for design, formula derivation, parity diagnosis and transpile review. Use cheap models for inventory sweeps, grep fan-out, row-count checks and doc drafting.
8. **Domain owner for formulas:** Guy Manova. When procs and wikis don't settle a formula, the agent cites or asks Guy.

---

## Stage 0 — Intake (agent, ~minutes)

- Restate the request as a single sentence covering:
  - the target metric or behaviour;
  - the consuming surface (which report, dashboard or extract);
  - the platforms involved (Synapse only, Databricks only, or both).
- Create the run folder `audits/dark-factory/<yyyy-mm-dd>-<slug>/` containing:
  - `ledger.md`: per-object state table (see Stage 9);
  - `decisions.md`: each decision plus the ladder rung it fell under;
  - `sql/`: every statement the agent will run.
- Classify the request: new metric, bugfix, refactor, migration/transpile, or backfill. Each type uses different acceptance tests (Stage 2).

## Stage 1 — Discovery and impact (agent, read-only)

Build the **object inventory** before any design work. For every object touched, record:

| Field | Why (ACATS evidence) |
|---|---|
| Platform + full name | Synapse and Databricks DDR run independently. ACATS was blocked on the wrong platform. |
| **What re-creates it** (a notebook with `CREATE OR REPLACE`, the deploy pipeline, the on-demand STG clone, the UC export bot, or nothing) | An SP whose DDL lived in a scheduled notebook reverted the fix every day. Guy's notebooks are thin wrappers that call the SP, but others script the SP inside the notebook, so this must be checked every time. |
| Deploy lane | **Synapse: every change needs a DataPlatform PR**, because DataPlatform governs it and CI/CD applies. **Databricks:** some object types (views, functions) don't require CI/CD, so they are deployed but not necessarily changed through a PR. Tables and other object types go through CI/CD. |
| **All consumers, including every sibling in the family** | The 7 `Function_DDR_Aggregation_*` functions were missed. The Daily Panel join was missing. |
| The literal BI source ("what does the extract SELECT FROM") | Tableau reads from Synapse, not Databricks. |
| Downstream status/SCD tables | The customer daily/periodic status tables were never scoped. |
| **Storage format and partitioning of every large join target** | See the partition rule below. |
| Scheduled jobs that write the same table, and when they run | The manual rerun collided with the service broker, which doubled the rows (2x). |
| **Is each Synapse source an external (lake-sourced) table?** (`git grep "CREATE EXTERNAL TABLE [<Schema>].[<Table>]"` in DataPlatform; names don't reveal it, e.g. 326 in `Dealing_staging`) | External tables read from the lake and are never in the generic pipeline. Their UC counterpart comes from the `LOCATION` path, not the gold naming convention. See `synapse-dbx-crosswalk`. |
| Data-skills corpus entries that describe these objects | `trading-volumes.md` still documents `BI_DB_VolumeQA`. Feeds Stage 7a. |

**Partition rule:**
1. Check whether the source is parquet (raw files or a non-Delta external table).
2. If it is, find the partition column and filter or join on it. Example: PositionPnL must use `etr_ymd`, not DateID, otherwise the scan is unbounded.
3. If it is Delta, partitioning doesn't matter; Delta handles pruning.

**Read before asking.** Gather this from proc and view definitions, `information_schema`/`sys.sql_modules`, repo history and wikis. Don't ask the user for anything that can be read.

**Checkpoint (interactive simulation mode only):** stop after the inventory and present it for evaluation before writing the spec.

## Stage 2 — Spec (agent drafts, human confirms at kickoff)

- **Grain and dedup key.** State them explicitly, e.g. "one row per position-leg; key = PositionID+leg". Write the duplicate-key test now.
- **Formulas.** Cover sign conventions, the amount source (`InitialAmountCents` vs prorated `Amount`), the PnL source, and the gating, e.g. instrument type and ActionTypeID family. Cite where each rule came from. If the sources don't settle it, the owner is Guy.
- **Mirror rule for dual-platform changes.** Every formula change lands on both platforms in the same run, and the agent checks the formula itself, not just that the column exists. ACATS shipped `InitialAmountCents` on Databricks only; the PROD pre-check passed because it only looked for column names.
- **Acceptance tests,** written before any code:
  - flag breakdown by dimension (e.g. InstrumentTypeID), not just counts;
  - reconciliation of amounts against ground truth (Dim_Position) on 2–3 non-VIP dates, including at least one date with a partial close;
  - expected cross-platform deltas, each with a predicted cause;
  - zero duplicate keys;
  - per-DateID row counts unchanged for columns the change doesn't touch.
- **Backfill approach** (if historical data needs correcting): a backfill is **every persistent object downstream of the change**, not just the one the request named. Walk the lineage from Stage 1's inventory and classify each object (full detail + worked example in `references/backfill-lineage.md`):
  1. **Same grain, stable key** (e.g. position/transaction-grain facts): map the affected keys, MERGE/UPDATE only the changed columns.
  2. **Aggregated, different grain** (e.g. a DDR-style fact table grouped by a dimension combination): MERGE is unsafe — it can leave stale buckets or miss new ones. RECREATE instead: either a bounded per-date delete+reinsert over just the affected dates, or, if the whole history is affected, a one-time single set-based `TRUNCATE`+`INSERT` (not a day loop) with an explicit execution window and runtime called out.
  3. **Pure passthrough downstream objects:** no backfill effect — but state that explicitly with what was checked, don't assume it.
  4. **Downstream objects with their own derived state** (classifiers, first-X dates, cohort assignment, snapshots): evaluate whether the change moves any of that; if so, it needs its own entry in this same classification, recursively.
  5. Test every chosen strategy on the side before running it for real.
  6. If an object truly can't be handled by merge or a bulk recreate, **do not fall back to massive day-by-day loops.** Surface it to the human.

## Stage 3 — Kickoff question round (human touchpoint)

One message that bundles:
1. **Operating mode:** full dark mode or interactive simulation. Default to interactive simulation until told otherwise.
2. **Spec confirmation:** grain, formulas, acceptance tests, backfill approach.
3. **Genuine forks only** (ladder rung 4): alternatives that are each defensible but have different effects.
4. **Policy gates** (rung 3): writes to production-by-default repos (DataPlatform, DE-Marketing).
5. **Actions the classifier will block,** requested upfront: `KILL`, global config edits, background prod writes, OAuth logins.
6. **The object inventory,** so the human can add any consumer the agent missed.

Every request gets a kickoff in the current small scope. In a massive scope, a kickoff per request may not be feasible; that is parked.

## Stage 4 — Implement (agent, on a branch)

- Use a branch per repo, following that repo's naming convention. DataPlatform uses `DA-NNNN_slug` with a title format; DE-Marketing uses `<type>/DSM_slug`. Check recent PRs first.
- Every changed object gets a source file in the repo. This includes UC objects that had no IaC before; capture them from the live `SHOW CREATE` output rather than retyping them.
- Use explicit column lists. No `SELECT *` in INSERTs.
- **No QA scaffolding in the diff.** Debug tables, QA dumps and extra debug columns go into `sql/qa/` in the run folder, never into the PR. Example: `BI_DB_VolumeQA` got ACATS columns and shipped to PROD.
- **UC column comments.** For every column the change creates or changes, write a rich, contextual UC comment: create one where the comment is blank, update it where one exists. Existing human-written comments are added to, never overwritten. The comment ships with the change.

### Cross-platform work (occasional)

Load the **`synapse-dbx-crosswalk`** skill (in this plugin); it holds the knowledge below in detail.

Most requests touch only one platform, and the agent works natively in each one. When a request needs both platforms (ACATS did), or a Synapse → Databricks refactor:
- **Use the transpiler** as the starting point. Don't hand-port.
- **Review its output** for known T-SQL patterns that Lakebridge transpiles wrongly (inline TVFs, `OUTER APPLY`, implicit conversions, `CONVERT` styles, integer division, NULL semantics in `CASE`/`ISNULL`). Treat the output as a draft, never as truth.
- **Locate the generic pipeline mappings** that move each Synapse source into UC, so you know the real UC counterpart and how fresh it is.
- **Identify Synapse external tables** (they are parquet-backed; the partition rule applies) and decide how each one is sourced on the Databricks side.

## Stage 5 — Deploy to the test environment (agent)

| Platform | Where | How |
|---|---|---|
| Synapse | STG (`sql_dp_stg_we_BI_no_retention`) | `tools/synapse_stg_deploy/deploy.py` (default env STG). Never MCP for DDL. |
| Databricks | The `_stg` twin of the object's schema (see below) | `dbx_query.py` / CLI. Never MCP `confirm_write`. |

**Databricks test location.** The catalog doesn't matter; `main` is shared across workspaces, so "DE-STG" gives no isolation. The schema does:
- If the object exists in a schema that has a `_stg` twin, test there. Example: `bi_output` → `bi_output_stg`.
- If the object is new, or lives in a prod-only schema with no `_stg` twin (e.g. BI_DB or DWH mirrors), use `de_output_stg`.
- Either way, the run cleans up after itself (Stage 7).

**Other rules:**
- **STG is cloned on demand, so its data can be stale.** Check `MAX(DateID)` of every source table first, and record the usable date window in the ledger.
- **Re-deploy from the PR branch immediately before validating.** Don't trust an earlier deploy.
- **Long calls:** a timeout on the client side does not mean the call failed. Never re-issue it; poll the target instead.
- **Reruns:**
  - Check the state and schedule window of any scheduled job that writes the same table.
  - Run serially, because shared temp tables like `_tmp_ddr_pop` break concurrent runs.
  - Avoid the morning bronze ingestion window (~07:30–08:30 UTC). A failure mid-proc leaves the date empty, because the DELETE has already committed.
- **Synapse MCP lock trap:** the MCP session holds an open transaction, so even its reads hold locks. Query any table you intend to drop or rebuild through pyodbc autocommit.

## Stage 6 — Validate (agent)

1. **Deployed-behaviour check (three layers).** Run all three before the PR, and again in the post-merge runbook after the PROD deploy.
   - **(a) Existence:** use `sys.sql_modules.definition` / `routine_definition`. `INFORMATION_SCHEMA.ROUTINES` misses inline TVFs.
   - **(b) Formula diff:** extract the changed expression from the stored definition on **each** platform and diff them. A keyword or column-name `LIKE` is not a check. ACATS-in passed `LIKE '%ACATS%'` while still using a different formula from Databricks.
   - **(c) Behavioural probe:** choose probe dates/keys where the old and new formulas (or the two platforms' formulas) would *disagree*, e.g. a partial close for ACATS-in. Run the deployed objects on both platforms and compare the values per key. Convenient dates that happen to make the formulas agree prove nothing.
2. Run the Stage 2 acceptance tests.
3. **Cross-platform parity** on the overlapping date window. Every delta needs a cause, and none are waved through as "Synapse is legacy".
4. **Independent-signal check:** compare the test output with what the DDR monitor would see (per-DateID counts and sums).
5. **Downstream run:** all consumers compile and return rows, i.e. a `SELECT TOP 10` from every function and view in the inventory.

**Iteration rule:**
- Failures loop back to Stage 4, up to **5 iterations**.
- An iteration counts only if **something changes** between attempts: code, a join, a hypothesis being tested.
- Rerunning the same code, auth failures, permission errors and infrastructure flakiness are not iterations. Don't loop on them; stop and report.
- After 5 real iterations, open the PR as **draft** with the failure documented rather than spinning.

## Stage 7 — Cleanup and side outputs (agent)

- Drop every test and side object the run created (`tmp_*`, `__df_*`, objects deployed into `_stg` schemas that didn't exist before), and record each drop in the ledger.
- Check the diff for QA scaffolding, debug columns and commented-out experiments.
- Move every SQL file that matters from the scratchpad into the run folder or the repo.
- Update memory with any new durable lesson (not run state).

### 7a — Data-skills corpus

- Evaluate whether any data-skills corpus entry is affected by the change. Start from the inventory field in Stage 1.
- If one is, generate the proposed change and insert it into the UC **user-suggestion skill table** with status `new`. Downstream automations pick it up from there.
- **The dark-factory agent never opens skills PRs itself.**

### 7b — Backfill (outside the PR)

- Backfills are **not** part of any PR. They contain no schema or code change, so CI/CD doesn't apply.
- A backfill is the full downstream lineage, each object classified and handled per `references/backfill-lineage.md` — not just the object named in the request. Re-run the Stage 1 inventory's consumer list against the backfill, not just the formula change.
- The backfill statements (one set per classified object) and their parity results live in the run folder.
- A backfill may be run once its side-table tests pass and the code it depends on is deployed in PROD. Include, per object:
  - its classification (same-grain merge / aggregated recreate / passthrough-no-effect / stateful-downstream) and why;
  - the collision window to avoid (ETL schedule, concurrent reads);
  - pre/post verification queries;
  - a rollback.

## Stage 8 — Open the PR (agent)

The PR body contains:
1. **Summary:** what changes and why, in one paragraph.
2. **Object ledger:** each object with change type, deploy lane, and who re-creates it.
3. **Validation evidence:** test results with the actual numbers, the parity table, and an explanation of each delta.
4. **Decision log:** each decision and its ladder rung.
5. **Deploy runbook for after merge:** dependency order, the exact commands, and post-deploy definition checks. The PROD deploy is currently done by a human.
6. **Pointers:** the run folder (backfill plan, parity evidence) and the skill-suggestion rows submitted.
7. **Open questions/risks.**

DataPlatform lands via a PR only, never a direct push. No PR is opened without kickoff sign-off.

## Stage 9 — Handoff/ledger (continuous)

`ledger.md` starts with this table and is rewritten in place each session, not appended to:

| Object | Repo | PR branch | Test env def ✓ | PROD def ✓ | Verified how | Re-created by | Backfill strategy |
|---|---|---|---|---|---|---|---|

Retracted findings are deleted, not struck through, below a "DO NOT" block. Size each session to finish one object chain before the context tracker turns 🔴.

---

## Stop conditions (agent halts and reports)

- A policy gate that wasn't cleared at kickoff.
- Any action that would write to a PROD table, view or SP.
- An unexplained cross-platform delta after 5 real iterations.
- A failure that isn't fixable by changing anything: auth, permissions, or infrastructure.
- The classifier blocks the same action twice. Report it; don't find a workaround.
- A classified object can't be handled by either merge or a bulk (single-statement or bounded per-date) recreate.
- Data-loss or irreversibility risk.

## Resolved points (v0.1 ❓ → Guy's answers)

| # | Question | Answer |
|---|---|---|
| 1 | Standard UC sandbox location | The `_stg` twin of the object's schema. If there is none, or the schema is prod-only, use `de_output_stg`. Always clean up. |
| 2 | Extra check-in after inventory? | Yes, while we're building: the kickoff asks for full dark mode vs interactive simulation, and interactive simulation is the default. |
| 3 | Owner of the post-merge Synapse PROD deploy | A human, fully. Bot reviewers and deployers come later. |
| 4 | Draft PRs without kickoff sign-off? | No for now (small scope, each request gets a kickoff). Parked for massive scope. |
| 5 | Formula owner | Guy Manova. |
| 6 | Backfill in the PR? | Never. Backfills are run once their tests pass; CI/CD doesn't apply. |
| 7 | What counts as "the backfill"? (v0.2.1 correction) | Every persistent object downstream of the change, not just the one named in the request — each classified by grain (same-grain merge vs. aggregated recreate vs. passthrough vs. stateful-downstream) and handled accordingly. See `references/backfill-lineage.md`. |
