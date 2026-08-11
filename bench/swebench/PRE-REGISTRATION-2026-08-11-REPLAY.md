# Pre-registration — 2026-08-11 factory replay (Step 4) on manifest `923aef05add32124`

**Written and committed before the run.** Nothing below this line is edited once
data exists; the outcome goes in a section at the bottom.

## What this run is

The plan's **Step 4**: re-run the `factory` arm on the pinned SWE-rebench
manifest with Steps 2–3 applied, to measure whether the dev-loop behaviour
changes and the machinery fixes move the resolve rate.

It is a **replay of one arm**, not a new sweep. The comparators are:

| arm | number | where it came from |
|---|---:|---|
| `factory` (sweep 2, before these fixes) | 10/19 = 53% | `results-archive/2026-08-10T21-53-14.959258Z/` |
| `openhands` (**same-sweep control**, Step 0) | 10/15 = 67% | `results-archive/2026-08-11T03-34-18.520898Z/`, backed up to `/home/k/backups/sf-bench-openhands-control-2026-08-11/` |
| `solo-noreview` (sweep 2) | 9/19 = 47% | same sweep-2 archive |
| `claude-5` (sweep 2) | 11/14 = 79% | same sweep-2 archive |

## The denominator moved: n=18, not 19

The re-run gold-patch control (PR #313, `selftest.json` `checked_at`
2026-08-11T03:53:03Z) rules **`pandas-dev__pandas-63945` a BROKEN instance**: its
own gold patch does not resolve, because its declared `fail_to_pass` id
`TestPandasContainer::test_url` is a **network** fixture and grading runs
`--network none`, so the id skips and can never pass. `google__flax-5171` stays
excluded as before.

So this replay runs **18** instances, and every prior rate must be re-derived on
the same 18 before it is compared. Rates over 19 and rates over 18 are not
comparable, and the report is the only place either may be quoted from.

## Deviations from sweep 2 — every behaviour change, disclosed in advance

All of these landed between sweep 2 and this replay. They are **not separable**
from each other in this design; a difference in the result is attributable to the
set, never to a member.

**Dev-loop behaviour (PR #310):**

1. A dev turn may no longer end on prose. A run whose last event is an agent
   message carrying neither a tool call nor a terminal marker is continued in the
   same conversation, at most twice.
2. The dev persona now demands an executable **reproduction that fails before any
   production edit**, replacing "write tests, make them green".
3. The dev persona now **permits scope-widening** past the file the issue names.
4. `_BENCH_ROOT_CAPS` writes the bench root's spend caps explicitly. **This is a
   real per-row budget change**: sweep 2's rows inherited the settings-model
   defaults of $2/h and $10/day, four times tighter than the dev loop's own $8
   per-story budget, and `hourly_cap` truncated 4 of 38 chain rows — including
   `vyper-4801` after one inner attempt.

**Machinery (PRs #312, #314):**

5. Diff capture targets the manifest's **base commit SHA** first, and an empty
   capture from an untrustworthy tree is **refused** rather than published as
   `empty_patch`.
6. The dev stall guard only counts attempts whose tail shows **real test
   results**; `_MAX_DEV_SAME_SIGNATURE` is unchanged at 2.
7. The slop detector uses `swebench-base` as its base ref and scores only files
   the branch authored. Its veto is unchanged.
8. `tests_green` requires a non-empty production delta **under the bench driver
   only** (`gates.require_production_delta`).
9. An empty diff with retry headroom routes back to dev instead of blocking
   terminally. The reviewer LLM is still never called on an empty diff.
10. Graded test files whose content changed are **restored** from their
    first-lock digest before the next dispatch.

**Common to the control:** (5) also applies to the `openhands` arm, which ran
before it. Zero openhands rows had an empty capture from an untrustworthy tree, so
the change could not have altered that arm's result — disclosed rather than
assumed, and re-derivable from `diff_integrity` on the replay's rows.

**Unchanged:** the model routing (dev standard and hard both
`azure/deepseek-v4-pro`; reviewer and acceptance author `azure/Kimi-K2.7-Code`),
the retry cap of 4, the 16-tick and 5400 s budgets, the 600-iteration inner cap,
the acceptance oracle authored spec-only before dev dispatch, the story template
bytes, and grading.

## Pre-committed criteria

From the plan, unchanged:

1. **Primary: 12/19 on a replay.** The plan states in the same sentence that this
   is **a projection, not a measurement** — `tox`'s recovered patch has never been
   submitted to `grade()`, and only its `schema.json` hunk is byte-identical to
   Claude's. Re-expressed on the working set: **12/18 = 67%**. If it lands at
   11/18, that is the result; the projection is not a target.
2. **Zero machinery-attributable empty-patch rows.** An `empty_patch` row is
   machinery-attributable when `diff_integrity.trustworthy` is false or the row
   was refused; it is NOT machinery-attributable when the dev genuinely changed
   nothing on a healthy tree.
3. **Containment bypass 0 of 18** — `test_readonly.bypassed_count` 0 on every row,
   or, where non-zero, `restored_test_files` non-empty for the same row (the
   breach was repaired before any green could rest on it).
4. **A null result is reportable, not a re-run.** No re-rolls of an outcome. An
   infrastructure loss (a provider error that produced no metered result, a
   sandbox crash, a harness defect) may be re-run **once**, disclosed, both
   outcomes published if they differ.
5. **`dev_inner_loop_stops` is mandatory reporting** per row, now that it reaches
   `result.json`. A row truncated by a guard must be visible as such.
6. **No cross-sweep delta is a measured improvement.** Sweep 2 → replay confounds
   ten disclosed changes. The `factory` − `openhands` pair within this manifest is
   the only comparison that holds the model fixed and varies the harness, and it
   is still k=1 at n≈15–18, where MDE ≈ ±38 pp.

## What this run cannot show

Three things, stated now so no reading of the result can imply them:

- **It cannot show the chain is worth its cost.** The same-sweep control is 67% at
  $1.46/resolved against the chain's 53% at $5.02. Even the projected 12/18 = 67%
  only reaches parity, at several times the cost. The machinery fixes remove
  self-inflicted losses; they cannot add capability, because the chain has one dev
  and no selection term (Phase C is cancelled).
- **It cannot settle the operator thesis.** `gate_enforced: false` on every row,
  the driver terminates at `reviewer_done`, and there is no PM, SM, contract,
  merge gate or deploy. The plan moves Phase D's primary gate to live-chain units
  (sacrifice stories merged per day, $ per merged story) for exactly this reason.
- **It cannot resolve a delta at this n.** k=1, n=18, MDE ≈ ±38 pp. k ≥ 3 remains
  the bar.

## Spend

Projected from sweep 2's measured factory arm: **~$50** for 18 instances
(sweep 2 was $50.18 for 19). Caps: $120/h, $300/day. Operator notices at
$50/$75/$100 on actual accumulated spend. Run at full width (18 workers, one
batch) per the 2026-08-11 operator instruction, so wall clock is bounded by the
slowest instance rather than by batch count.

Evidence backed up before the run:
`/home/k/backups/sf-bench-openhands-control-2026-08-11/` (1,789 files, SHA256
verified) — `runs/` is gitignored and a re-run destroys it.
