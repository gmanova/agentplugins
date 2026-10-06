# Procs / ETL idioms — traps found in production code

## `SELECT *`-based ETL is a standing landmine when the source view's schema changes

Positional `INSERT INTO target SELECT *, current_timestamp() AS X FROM some_view` silently
misaligns the moment the view gains/reorders columns, because the destination table's own
`ALTER TABLE ADD COLUMNS` history doesn't have to match the view's column *order*. Concretely:
a view gained two new trailing columns; the destination table already had two *different*
trailing columns from an earlier `ALTER TABLE ADD COLUMNS ... AFTER UpdateDate`. Running the
unmodified SP would have written flag values into a timestamp column and a timestamp into a flag
column — no error, just silently wrong data. **Before editing or rerunning any `SELECT *`-based
INSERT after a source view's schema changed:** diff column *order* via
`information_schema.columns` on both sides, not just presence. Fix by rewriting to an explicit
column list on both the INSERT and SELECT sides.

## Reason-code / flag columns need a dimension cross-check, not just a row-count sanity check

A flag built from a single reason code (e.g. `OpenPositionReasonID = 13`) can be **shared** across
semantically different scenarios (e.g. genuine ACATS transfers AND ordinary Crypto position
opens use the same reason code). A row count that "looks plausible" can be 100% wrong — in this
feature, ALL 288 first-day "ACATS-in" rows turned out to be Crypto, zero genuine Stocks/ETF.
**Before declaring any reason-code-based metric validated:** spot-check the actual dimension
breakdown (e.g. `InstrumentTypeID`) of what's being counted, not just the row/volume total. Add
the missing dimension guard once found (here: `AND InstrumentTypeID IN (5,6)`) and re-validate
against a date known to contain genuine cases of the rarer class.

## An "open" and its matching "close" often need asymmetric formulas — don't force symmetry

Position-open metrics may need to branch on whether the position is still open at EOD (unrealized,
mark-to-market) vs. closed same-day (realized) — e.g. `Amount + COALESCE(EOD_PnL_snapshot,
NetProfit)`. The matching close-side metric is frequently NOT symmetric: a close is always fully
realized, so `Amount + NetProfit` alone is already complete with no branching needed. Confirm the
asymmetry with the domain owner rather than assuming the open/close pair must mirror each other —
forcing false symmetry (or assuming a missing branch on the close side is a bug) wastes a review
cycle on a non-issue.

## A live-fixed notebook-owned SP is provisional, not done

See `databricks-dab-uc.md` ("Deployment target discipline") — the same lesson restated as a
procs/ETL-specific checklist item: re-verify a notebook-owned SP/table fix (re-run the known test
case) any time meaningful wall-clock has passed since the fix and its owning PR hasn't merged yet.
A silent revert looks identical to the original bug (same corrupted-column signature), not like an
error.
