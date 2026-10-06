# Backfill: walk the full lineage, classify every persistent object

**Correction (2026-10-06, Guy):** a "backfill" is not one table. It is every
persistent object downstream of the change, each handled according to its own
grain. Treating backfill as "write a MERGE for the one table I changed" misses
objects that need a different strategy, or need nothing, or need attention the
agent wouldn't guess from the name.

## The classification

For every persistent object in the downstream lineage of the change (walk it
the same way Stage 1 inventories consumers — don't stop at the first hop):

| Shape | What it means | Strategy |
|---|---|---|
| **Same-grain, stable key** | A row backfill maps 1:1 (or by a deterministic key) onto existing rows — e.g. position-grain or transaction-grain fact tables like `v_fact_customeraction_w_metrics`. | Map the affected keys, **MERGE/UPDATE** only the changed columns. Cheap, easy. |
| **Aggregated, different grain** | The object `GROUP BY`s a dimension combination (e.g. CID × InstrumentTypeID × IsBuy × ... × DateID). A root-level change can add, remove, or shift which dimension combinations exist for a given key — a MERGE can leave stale buckets behind or miss new ones. | **RECREATE**, not merge. Two sub-cases below. |
| **Pure passthrough** | Recomputes fresh from the upstream object every time it's read; carries no independent persisted state. | No backfill effect. State this explicitly with what you checked — don't just assume it. |
| **Downstream object with its own derived state** | Carries persisted state keyed off the values being changed — classifiers, first-trade/first-X dates, cohort or segment assignment, running totals, snapshots. | Evaluate on its own terms: does the change move anyone's classification, first-date, or snapshot? If yes, it needs its own entry in this same table — recurse the classification into it. Don't assume "downstream" means "safe." |

### Recreate sub-cases (aggregated grain)

1. **Only specific dates/partitions are affected** (e.g. a bugfix changing a
   subset of history): reuse the object's own incremental build logic,
   parameterized by date, and delete+reinsert (or truncate+insert, if
   partition-scoped) **just those dates**. This is a bounded loop over the
   affected set — not the "massive day loop" the no-day-loop rule bans, which
   is about looping over all history when one set-based statement would do.
2. **The whole history is affected** (new column, or a formula change that
   alters every date): a **one-time, single set-based `TRUNCATE` + `INSERT`**
   over the full history. Still one statement, not a day loop — the aggregation
   function can usually be called once across the whole date range. Call out
   explicitly:
   - the execution window (avoid the daily ETL; a multi-hour backfill run in
     the middle of the morning batch or evening cutover can get killed or
     corrupt a concurrent load — see [[project_ddr_trading_volumes_databricks_native_fix_needed]]
     and the retro's lesson on scheduling collisions);
   - expected runtime, so whoever runs it knows what "still running" looks like;
   - that it is destructive mid-flight (the table is empty between the
     `TRUNCATE` and the `INSERT` completing) — never run it against a table
     anything else reads concurrently without a stated window.

## Worked example — `BI_DB_DDR_Fact_Trading_Volumes_And_Amounts` (Jira 344484)

This Synapse DDR fact table is CID × dimension-combination grain (not
position/transaction grain), fed by `Function_Trading_Volume`. Both patterns
appear in the real change:

**Per-date recreate** (the nightly incremental SP, same shape as case 1 above):

```sql
DELETE FROM BI_DB_dbo.BI_DB_DDR_Fact_Trading_Volumes_And_Amounts WHERE DateID = @dateID

INSERT INTO BI_DB_dbo.BI_DB_DDR_Fact_Trading_Volumes_And_Amounts (...)
SELECT ftv.DateID, ..., SUM(ftv.VolumeOpen), ...
FROM BI_DB_dbo.Function_Trading_Volume(@dateID, @dateID, 0) ftv
GROUP BY ftv.DateID, ftv.CID, ftv.InstrumentTypeID, ...
```

Delete-then-insert for the date, not an UPDATE — because the set of dimension
combinations present for that date can differ run to run.

**One-time full-history rebuild** (case 2 above — a single statement, no loop,
run once with an explicit maintenance window noted in the script header):

```sql
/* CAREFUL: the insert takes a couple of hours, so run it in the afternoon -
   not in the morning when it's busy and not in the evening when it can
   get cut off by the daily ETLs */

TRUNCATE TABLE BI_DB_dbo.BI_DB_DDR_Fact_Trading_Volumes_And_Amounts

INSERT INTO BI_DB_dbo.BI_DB_DDR_Fact_Trading_Volumes_And_Amounts (...)
SELECT ftv.DateID, ..., SUM(ftv.VolumeOpen), ...
FROM BI_DB_dbo.Function_Trading_Volume(20070827, <yesterday's DateID>, 0) ftv
GROUP BY ftv.DateID, ftv.CID, ftv.InstrumentTypeID, ...
```

One `INSERT ... GROUP BY` call across the entire history range — the table
function can evaluate the full range in one pass, so there's no need to chunk
it by date even though the result is a full rebuild.

**Downstream of this table** (e.g. `ddr_customer` status/periodic tables fed
by it): in this case, no effect — they don't carry their own aggregates off
these columns. That has to be checked per change, not assumed; when it *is* a
new column or a shifted value that an SCD/classifier table keys off, that
table needs its own classification and backfill plan from the table above.

## Apply this per object, in the run folder

Record, per persistent object touched: grain shape, chosen strategy, the
statement (or pointer to it), and verification (row counts / dup-key check /
cross-platform parity, per [[parity-method]]). This is the same ledger the
process doc's Stage 9 table tracks — add the "Backfill strategy" column there
rather than keeping it separate.
