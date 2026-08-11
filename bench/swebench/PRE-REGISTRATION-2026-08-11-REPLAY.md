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

---

# Amendment 1 — 2026-08-11, still BEFORE any published data

**Why this exists.** Everything above was written and committed on 2026-08-11
before PRs #315–#320 existed. Two launches were then attempted and **neither
produced a publishable arm result**; both failed for reasons the text above did
not anticipate, and both were fixed in code that is now in the tree. Amending is
therefore mandatory: running under behaviour the pre-registration does not
disclose would make the disclosure list false.

Nothing above this line is altered. This section only **adds** disclosures and
**supersedes** one operational sentence. It is committed before the run; the
commit order is the proof, and no outcome section exists yet.

## The two aborted launches, disclosed in full

| launch | width | what happened | rows | spend | evidence |
|---|---:|---|---:|---:|---|
| 1 | 18 | Every row died on `LLMRateLimitError` against the shared Azure `deepseek-v4-pro` deployment. 20 trajectories carried the event; 5 "completed" rows had `files_touched: []` and no `SELF_SUMMARY` — the sandbox never worked. | 0 usable | ~$4.10 | destroyed by launch 2 |
| 2 | 4 | Killed by the operator at 6/18. **5 of the 6 rows landed in `blocked_tests_need_clarification` with a green test tail** — `require_production_delta` asked "did THIS ATTEMPT touch a non-test file" instead of "does the BRANCH carry a production delta", so a green attempt that only re-ran tests was forced red. 1 resolve in 5 graded rows; `pyinfra-1665`, a sweep-2 resolve, regressed to `right_place_wrong_fix`. | 6 of 18 | $23.41 | `/home/k/backups/sf-bench-replay-attempt2-aborted-2026-08-11/` (176 files, SHA256 verified) |

Both are **infrastructure/harness losses** under criterion 4, not outcomes: no
arm result was computed, reported or published from either. But criterion 4 says
such a loss "may be re-run **once**". This is the **third** launch, so the strict
reading of that clause is exceeded, and it is recorded here rather than argued
away. Launch 2's six rows are published alongside the replay in the report
whether or not they differ, per the same criterion's "both outcomes published"
requirement.

Launch 2's row table, verbatim from the backed-up `result.json` files, so it can
be compared against the replay's rows:

```
alibaba__opensandbox-816    blocked_tests_need_clarification  green=False diff=5787B  retries=3 rc=1  right_place_wrong_fix  $6.17
harumiweb__exstruct-113     blocked_tests_need_clarification  green=False diff=6883B  retries=2 rc=0  wrong_place            $5.90
hkuds__openharness-217      reviewer_done                     green=True  diff=1447B  retries=0 rc=0  resolved               $1.62
pyinfra-dev__pyinfra-1665   blocked_tests_need_clarification  green=False diff=1357B  retries=2 rc=1  right_place_wrong_fix  $3.30
tox-dev__tox-3931           blocked_tests_need_clarification  green=False diff=3314B  retries=2 rc=0  right_place_wrong_fix  $4.67
ucfopen__canvasapi-716      blocked_tests_need_clarification  green=False diff=1092B  retries=2 rc=1  right_place_wrong_fix  $1.75
```

Note `tox-3931`: deviation 5's diff-capture fix **works** — 0 B became 3,314 B —
and the recovered patch still grades `right_place_wrong_fix`. **One of the two
gains the 12/18 projection rests on is therefore already dead before this run
starts**, and the projection is not revised downward to protect it. It stays at
12/18 as written, and is still a projection, not a target.

## Deviations 11–15 — everything that landed after the text above

11. **`gates.require_production_delta` asks the BRANCH (#317).** Deviation 8's
    gate is re-implemented: it diffs the story branch against its base for any
    non-test change, rather than reading one attempt's `files_changed`. It
    **fails open** — when the delta cannot be determined the green is kept — on
    the rule that a gate for a rare "green on an empty tree" must never degrade
    to "block every story", which is exactly what launch 2 did. Scope is
    unchanged: bench driver only.
12. **The empty-diff → dev-retry route is bounded (#319).** Deviation 9 as
    originally written could route an empty diff back to dev without consuming
    the retry budget, i.e. unboundedly. It now consumes the budget and stops at
    the cap. Four review findings from the same PR ride along and are not
    separable from it.
13. **Sweep width is provider-bound at 4 (#315).** `run-all --workers` now
    defaults to `_PROVIDER_SAFE_WORKERS = 4` rather than the host width, because
    the quota is tokens/minute on one shared deployment and SDK backoff
    (`num_retries=5`, `retry_multiplier=8.0`, `retry_max_wait=64`) cannot buy
    throughput above it. Free steps (`selftest`, grading, pytest) still run at
    host width. **This supersedes the Spend section's "Run at full width (18
    workers, one batch)" sentence**, which is now known to be the instruction
    that destroyed launch 1. Wall clock is consequently bounded by batching plus
    the slow tail, ~2 h, not by the slowest instance alone.
14. **`factory-self-deploy.service` pins `PATH` (#318)** and **the sacrifice
    `security.md` context doc was refreshed (#320)**. Neither touches the bench
    driver, the chain handlers the bench exercises, or grading. Disclosed
    because they are in the tree the replay runs from, not because a mechanism
    is claimed.
15. **The bench run tree is empty at launch.** Launch 2's `runs/` and its
    `sweep-factory.json` were moved to the backup above and removed from the
    worktree, so no aborted row can blend into the replay's report. `#316` (a
    sacrifice `api_surface` snapshot refresh) is in the tree for the same
    reason as 14.

**Attribution is unchanged and gets weaker, not stronger.** The disclosed set is
now fifteen changes, not ten. A difference between sweep 2 and this replay is
attributable to the **set**, never to a member, and criterion 6 stands: the
`factory` − `openhands` pair inside this manifest is the only comparison that
holds the model fixed.

## Spend, restated

Launches 1 and 2 already spent **~$27.51**. The replay itself is still projected
at **~$50** for 18 rows. Operator notices at $50/$75/$100 fire on actual
accumulated spend and are reported when crossed. Caps unchanged: $120/h,
$300/day.
