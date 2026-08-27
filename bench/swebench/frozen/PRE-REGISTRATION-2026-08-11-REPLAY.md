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

---

# OUTCOME — 2026-08-11, written after the data existed

Run: 18 instances, 4 workers, 12,260 s wall, `sweep done ... 18 ok, 0 failed`.
Evidence: `results-archive/2026-08-11T16-22-03.186645Z/` — `report --check`
returns **CHECK OK**, byte-for-byte re-derivable, 76 diagnostic files / 39.1 MB
now snapshotted into the archive (the Tier-1 "the archive cannot reproduce the
analysis" gap is closed in practice, not just in intent).

## The number

**10 of 18 = 56%.** The pre-registered primary was 12/18. It was missed, and the
projection is reported as missed rather than re-expressed on a denominator that
would flatter it. The harness's own audited-valid convention prints **10/17 =
59%** because `vyper-4801` failed its audit; the pre-registered denominator is 18
and 10/18 is the number this document is answerable for.

## Every arm re-derived on the SAME 18 instances

| arm | resolved | rate | total $ | $/resolved | median wall |
|---|---:|---:|---:|---:|---:|
| **factory (this replay)** | **10/18** | **56%** | **81.00** | **8.10** | 1,804 s |
| `openhands`, same-sweep control | 12/18 | 67% | 14.34 | 1.19 | 454 s |
| `factory`, sweep 2 (before the fixes) | 10/18 | 56% | 50.18 | 5.02 | 1,038 s |
| `solo-noreview`, sweep 2 | 9/18 | 50% | — | — | — |

Paired against the control: both 9 · factory-only 1 · openhands-only 3 ·
neither 5. **McNemar exact two-sided p = 0.625.** Criterion 6 stands: this is
k=1 at n=18 and no delta here is a measured result.

## The finding: the fixes worked, and bought zero net rate

The replay scores **exactly what sweep 2 scored on the same 18 rows — 10/18 —
but the composition changed completely.** Three rows gained, three lost:

| gained | why | lost | why |
|---|---|---|---|
| `jsonpickle-588` | kept its full retry budget instead of dying at 2 on a collection error (#312) | `line-bot-981` | **new machinery loss** — see below |
| `tox-3931` | diff capture recovered 3,388 B instead of 0 (#312/#314) | `openharness-217` | dev stochasticity (resolved in launch 2) |
| `canvasapi-716` | reached a resolving patch | `hiero-1914` | dev stochasticity |

All three gains are the exact rows the machinery fixes targeted. They landed.
The rate did not move, because two of the three were paid back by ordinary
run-to-run variance and one by a **new** machinery defect. Cost per resolved went
the wrong way: **$5.02 → $8.10**, because deviation 4 removed sweep 2's $2/h
truncation and long rows now run to the 5,400 s wall-clock cap instead of being
cut short. Total spend was **$81.00 against a ~$50 projection, 62% over.**

## Pre-committed criteria, evaluated as written

1. **Primary 12/18 — MISSED.** Landed 10/18 = 56%.
2. **Zero machinery-attributable empty patches — PASSES as written, but the
   criterion is too narrow to be worth much.** Both `empty_patch` rows
   (`exstruct-113`, `vyper-4801`) have `trustworthy: true` and `refused_paths:
   []`, so neither is machinery-attributable by the stated definition. **The
   definition anticipated diffs that are too SMALL and has no clause for diffs
   that are too LARGE**, so it scores a pass while `line-bot-981` — a 575 KB
   diff that failed to apply — goes uncounted. Recorded as a defect in the
   criterion, not as a clean result.
3. **Containment bypass 0 of 18 — FAILS.** `test_readonly.bypassed_count > 0` on
   **10 of 18 rows**, and on **2** the repair did not succeed:
   `canvasapi-716` and `hiero-1914` both have `restored_test_files: []` with 11
   `restore_errors` reading *"restored … but the digest still differs — the edit
   was committed, not just written"*. Deviation 10 restores the **working tree**;
   a committed edit survives it. The other 8 rows were genuinely repaired, so the
   mechanism works — it just cannot reach a commit. Grading strips test files, so
   no score is contaminated; the chain's own green is.
4. **One re-run allowed — EXCEEDED, disclosed.** This was the third launch. See
   Amendment 1; launch 2's six rows are published there.
5. **`dev_inner_loop_stops` reported per row.** Non-empty on 2 of 18:
   `exstruct-113` (`attempts_cap`, 3 inner attempts) and `vyper-4801`
   (`attempts_cap`, plus `budget_exhausted: wall-clock-cap`, 6,341 s against the
   5,400 s cap). All other 16 rows are `[]`.
6. **No cross-sweep delta quoted as an improvement.** Honoured. The sweep-2 →
   replay comparison confounds fifteen disclosed changes and is reported as
   composition, not as a gain.

## Two machinery defects this run found

**A. `_branch_has_production_delta` asks a ref, not the pinned SHA.**
`handlers.py:3695` resolves `swebench-base` and diffs the branch against it. On
`tox-3931` the dev's gitlink surgery put the chain's own commits **on** that ref
(`base_ref_ahead_of_expected: 2`), so the diff was empty and the function mapped
empty → `False` ("confirmed no production delta") instead of `None` ("cannot
determine"). A green run touching `src/tox/session/cmd/schema.py` was forced red
**twice**; because the forced-red tail is identical every time, the stall guard
then fired at 2 of 4 deterministically. This is the same `ref-not-SHA` class
`_capture_diff` was fixed for in #312 — the second consumer was missed. It cost
no resolve here (grading reads the SHA-anchored diff, and tox still graded
`resolved`) but it produced a false-negative verdict and would park a correct fix
on the live chain.

**B. A dissolved submodule is captured as a 575 KB diff that cannot apply.**
`line-bot-981`, a row every prior same-model arm resolved, graded
`patch_did_not_apply`. Its diff opens with `deleted file mode 160000` /
`-Subproject commit 982bad2…` and then re-adds all 39 vendored `line-openapi/`
files. The grade log shows **every file applying cleanly, including both real
fixes**, and the apply step still returning exit 2 on the gitlink deletion.
`diff_integrity.trustworthy` is `true` — the predicate checks base-ref and
head-SHA relationships and has no assertion for submodule teardown or size
explosion. **This is a machinery-attributable lost resolve.**

Both defects share one upstream cause: the dev's `mv .git .git.file && ln -s`
gitlink surgery, which is now implicated in three distinct capture failures.

## What this run does NOT show

- **It does not show the chain is worth its cost, and the gap widened.** The
  single agent is 12/18 = 67% at **$1.19/resolved** against the chain's 10/18 =
  56% at **$8.10/resolved** — **6.8× the cost for a lower rate**, on the same
  manifest, same dev model, same week. Sweep 2's ratio was 2.8×; the machinery
  fixes made the cost ratio worse, not better.
- **It does not show the fixes were worthless.** Three targeted rows were
  recovered exactly as designed. It shows removing self-inflicted losses cannot
  raise the rate while the chain has one dev and no selection term — the identity
  `score = capability − tax + selection` with the third term pinned at zero.
  Phase C is cancelled, so nothing in the plan adds that term.
- **It cannot settle the operator's tasks/day thesis.** `gate_enforced` is
  `false` on all 18 rows, the driver stops at `reviewer_done`, and there is no
  PM, SM, contract, merge gate or deploy. The plan's Phase D moves the primary
  gate to live-chain units for exactly this reason.
- **It cannot resolve a delta at this n.** k=1, n=18, p=0.625.

## Verdict quality regressed

Chain-verdict precision **7/12 = 58%** (sweep 2: 71%), recall **7/10 = 70%**.
Three rows ended in a blocked state while producing a resolving patch —
`tox-3931`, `canvasapi-716`, `jsonpickle-588`. The one genuinely positive finding
of sweep 2 did not replicate, and at these interval widths it never could have.

## Provider errors

`RateLimitError` appears in 41 files, concentrated in `rapid-mlx-289` and
`exstruct-113`. Both rows completed and `rapid-mlx-289` resolved, so at 4 workers
the SDK's retries absorbed them — the behaviour #315 predicted, and the reason 4
is the right default rather than 18.

---

# Correction 1 — 2026-08-11, after publication

Four independent evidence re-reads of the run tree (see `POSTMORTEM-2026-08-11.md`)
found four errors in the outcome section above. The outcome text is left intact;
these supersede it.

1. **The "both defects trace to the dev's gitlink surgery" attribution is WRONG
   for `line-bot-981`.** That row's full trajectories contain **no dev git
   plumbing at all** — only a chain `worktree_create`. `git worktree add` does not
   materialise submodules as gitlinks the way a clone does, so the prepared tree
   carried `line-openapi` as plain files and the diff against the pinned base SHA
   necessarily contains the teardown. It is a **chain workspace-preparation**
   defect, not a dev-behaviour one. `tox-3931` IS dev-side (`git
   --git-dir=<repo>/.git commit` appears in its trajectory). A prompting fix would
   not have closed the second hole.
2. **The arms are NOT budget-matched, and the adapter claims they are.**
   `swebench_adapter.py:4831–4835` asserts "the shared 5400 s wall clock binds
   first for both". Iteration caps do match (600); **per-conversation wall clock
   does not**. Each chain dev attempt is capped at **1,800 s**
   (`factory/runner.py:68`), while the control runs one 5,400 s conversation. The
   control's winning `exstruct-113` trajectory took 1,807 s — longer than any
   chain attempt may live — and `vyper-4801`'s three chain attempts each died at
   1,800 s with `files_touched: []`. This is an **undisclosed arm asymmetry inside
   a disclosed identical-budget claim**, and it biases in the chain's favour: the
   true chain-vs-solo gap may be larger than measured.
3. **`exstruct-113` is classified "not machinery-attributable" only because
   criterion 2 models diffs, not feedback channels.** Two of its four attempts
   died to infrastructure; the other two deadlocked because the production-delta
   gate reported `Summary: tests not green after run` directly above a tail
   reading `11 passed in 0.82s`, with no reason given.
4. **A live-chain-equivalent number is missing and should have been reported.**
   The benchmark grades the diff; the live chain ships on a verdict. Three of the
   ten resolves (`tox-3931`, `canvasapi-716`, `jsonpickle-588`) ended in blocked
   states that would never merge. **Under `reviewer_done`-only semantics the
   factory is 7/18 = 39%.**

Minor: the count of vacuous (zero-assert) acceptance-oracle files is **7 of 18**.
