# Cross-platform parity method

## 1. Lock one business date

- Separate `target_date` (the data date, D-1) from `run_date` (D).
- The two platforms finish their ETL at different times, so comparing "live state" produces timing-artifact deltas.
- Observed: a Monday run gave 12 FAIL / 4 PASS because it started before the gold ADF pipeline had finished. The same logic on a quiet Sunday gave 13 PASS / 0 FAIL.
- Synapse STG is cloned on demand and can be stale. Check `MAX(DateID)` before choosing a date.

## 2. Choose probe dates where the formulas would disagree

Convenient dates prove nothing if the competing formulas agree on them.

ACATS-in example:
- Prorated `Amount` and `InitialAmountCents/100` agree unless there was a partial close.
- The 09-28 to 10-05 parity dates had no partial closes, so a formula divergence between Synapse and Databricks went unseen until a later date.

**Pick at least one date that exercises each branch of the changed formula.**

## 3. Compare money sums and key counts by dimension

- A flag metric needs a dimension breakdown, not just a total.
- In the ACATS case, all 288 first-day "ACATS-in" rows turned out to be crypto, while the total looked plausible.
- Compare per (DateID, key): counts, money sums, and zero duplicate keys.

## 4. Use NULL-safe comparison

Use `IS NOT DISTINCT FROM` or `COALESCE(a,0) = COALESCE(b,0)`, never bare `=`.

## 5. Explain every delta

- Every delta gets a root cause: timing, a scope mismatch (full-history gold vs a one-day increment), a permission-denied source, or a mirror gap. Never "small, ignore".
- **Mirror gaps:** the Databricks `dim_position` mirror can be missing position legs.
  - ACATS: 3 (CID, DateID) pairs explained the whole IN delta of 118,367.96 to the cent.
  - Check leg counts per key on both platforms before suspecting logic.
- Per-dimension row-count passes are cheap and catch real proc gaps: one proc wrote 84 of 1,230 gold rows, another wrote 0 of 16,244.

## 6. Weekday/weekend and open/close asymmetry can be legitimate

- Some gold tables populate differently on weekends. Confirm with the domain owner before calling it a bug.
- Open and close legs often need asymmetric formulas. A close is fully realized; an open may embed unrealized PnL. ACATS: IN = `InitialAmountCents/100 + PnL`, OUT = `Amount + NetProfit`.

## 7. Never assume Synapse (the older platform) is truth

Measure **both** platforms against an independent, observable reality.

Precedent: a finding that "Databricks over-flags 6.5x" **inverted** once it was tested against `dim_position`. Synapse was under-flagging by 67.5% (~$52M/yr) because of a stale free-text filter.

How to apply:
- Use a behavioural test that's independent of both implementations.
- Calibrate it with a positive control and a negative control.
- Run the decisive proof on the legacy platform's own source (e.g. `DWH_dbo.Dim_Position`).
- Volume-match the comparison sets.
- Don't use free-text metadata as a gate.

## 8. Deployed-behaviour check (before PR and after the PROD deploy)

- **(a) Existence:** use `sys.sql_modules`, not `INFORMATION_SCHEMA.ROUTINES`, which misses inline TVFs.
- **(b) Formula diff:** compare the changed expression across the two platforms. A keyword `LIKE` is not a check.
- **(c) Behavioural probe:** run the step 2 probe dates on both deployed platforms and compare per key.
