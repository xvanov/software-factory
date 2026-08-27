# Pre-registration — B.1 Phase 1a, the reviewer ablation

**Written before any paid call. Committed before the run.** Same discipline as
`PRE-REGISTRATION-1.6.md`, and for the same reason: this harness has been
retracted four times, twice because a framing was chosen after the data existed.
Everything below is fixed now. Every cell is filled from an archived artifact or
printed as `n/a` with a reason.

- Suite: **SWE-rebench**, pinned manifest `923aef05add32124`, the **same 19
  working-oracle instances** as the published five-arm run.
- n = 19, **k = 1**, `attempt` must be **1** on every row.
- **No re-rolls.** `PRE-REGISTRATION-1.6.md` Rule 5 applies verbatim and by
  reference: an audit-invalid row is published invalid and never re-run; a
  budget-exhausted row is a counted attempt; an infrastructure loss (provider
  429, sandbox crash) may be repaired once, disclosed, both attempts recorded.
- Budget: **~$35 target, $50 hard stop.** On approaching $50 the run stops and
  the operator is told.

## Why this probe exists, and why it is first

The chain resolves **7/19 = 37%** where **one** OpenHands agent on the same
model resolves **10/19 = 53%**, at 2.8× the cost per resolved instance
(`PLAN.md` §1). `PLAN.md` B.1 proposes collapsing the code-producing personas
into one long-horizon agent. That is the largest deletion in the plan, so it is
gated on measurement.

This probe is deliberately the cheapest slice of it: it removes **one** thing,
needs **zero** production code, and can kill the whole item for ~$35 if the
premise is wrong.

Evidence the premise rests on, all pre-existing:

- **P1** — no entry in the SWE-bench Verified top 20 decomposes by SDLC role,
  and there is no sequential-critic persona anywhere in it. EPAM *removed* its
  unit-testing stage and its multi-iteration loop and scored 76.8%.
- **P5(b)** — ImpossibleBench: multiple submissions with feedback raised
  test-exploitation **33% → 38%**. More review cycles, more gaming.
- **P5(c)** — AXIOM: complex agentic judge systems scored α **37–49.5** against
  **62.5–63.0** for a single simple prompt. More pipeline, less validity.
- **§1 #6** — our reviewer loop is not inert. Cycles are `0×7, 1×9, 2×2, 3×1`
  across the 19 published factory rows. It engages, and the resolve rate does
  not move.
- **A.4** — a measured replay: giving the reviewer *better* evidence (execution
  output instead of diff text) made it **worse**, Δ **−16.7 pp**, control ≥
  treatment in 9 of 9 replicate pairings.

## The two arms

**An arm is a (harness, model set) pair. Neither half may be omitted when a
number from this run is quoted.**

| id | harness | model(s), by role | budget | what it measures |
|---|---|---|---|---|
| `factory` | the chain — story seeded at `SM_DONE`, **dev + reviewer**, dev inside an OpenHands sandbox, run-until-green | dev standard `azure/deepseek-v4-pro` · dev hard-tier escape `azure/gpt-5.3-codex` · reviewer `azure/gpt-5.4` · acceptance author `azure/gpt-5.4` | 16 orchestrator ticks; OpenHands `max_iterations` 600 per dev session; 5400 s wall | the product as published |
| `solo-noreview` | the SAME chain driver with the **reviewer round-trip removed** — dispatch set `{dev}`, terminal green `tests_green` | dev standard `azure/deepseek-v4-pro` · dev hard-tier escape `azure/gpt-5.3-codex` · acceptance author `azure/gpt-5.4` | identical: 16 ticks, 600 iterations, 5400 s wall | the product **minus the reviewer** |

`solo-noreview` is `base="factory"` in `_ARMS`: the same `run_factory` driver,
the same code path, one registry entry.

## The single variable

Exactly two lines of behaviour differ, both inside the driver's dispatch loop:

| | `factory` | `solo-noreview` |
|---|---|---|
| personas the driver will dispatch | `{dev, review}` | `{dev}` |
| terminal states | `{reviewer_done, blocked_tests_need_clarification, blocked_review_nonconvergent, blocked_underspecified}` | `{tests_green, blocked_tests_need_clarification, blocked_review_nonconvergent, blocked_underspecified}` |
| the chain's own green claim (`factory_says_green`) | `state == reviewer_done` | `state == tests_green` |

Held **byte-identical**, and asserted in tests rather than claimed here:

- the rendered story file — one `_STORY_TEMPLATE`, pinned by a sha256 test, and
  a test that diffs the rendered task text across arms and asserts equality.
  Prompt asymmetry was the subject of a previous retraction;
- the dev persona prompt, the context prelude, `routes.yaml`, the OpenHands
  sandbox and its default toolset, `max_iterations`;
- the dev inner loop and every deterministic gate it runs;
- the acceptance-oracle authoring step and its spec-only prompt assembly;
- the read-only test-file lock, the collect precheck, the prepared clone, the
  install replay, `split_diff` / `assert_no_test_edits`, the grading oracle, the
  audit, the wall clock and the step budget;
- **no navigation-tooling change.** B.2 is a separate item on purpose. Moving
  two variables at once makes neither attributable.

Nothing under `factory/**` changes. No persona changes. No prompt changes.

### Disclosed confound, stated before the data exists

The comparison `factory` rows come from the committed archive
`results-archive/2026-08-04T23-19-24.998844Z/`. Those rows were produced
**before** PR #238 put the chain's acceptance-oracle authoring inside the
factory arm's measured path. `solo-noreview` runs on current `origin/main`, so
it **has** that step.

So `solo-noreview` differs from *today's* `factory` code in exactly one
variable (the reviewer), and from the *archived* `factory` rows in two (the
reviewer, plus the acceptance authoring step being present).

Why this is accepted rather than re-run: re-measuring `factory` doubles the cost
to ~$62 and breaches the $50 hard stop. The authoring step's measured
contribution is **$0.0087 of a $0.5752 row**, it is invisible to the dev
(certified per row by a trail scan), and its merge gate is **not run**
(`gate_enforced: false`), so its only causal route to the resolve rate is the
fail-closed refusal path — which produces *invalid* rows, counted and disclosed,
never silent ones. Any refused `solo-noreview` row is reported as invalid with
its reason.

## Primary metric and denominator

- **Primary metric:** `resolved / audited-valid`, where *resolved* is the hidden
  oracle's `RESOLVED` verdict on the stripped production diff, and
  *audited-valid* is a row that is clean end-to-end (run ok **and** audit ok)
  under manifest `923aef05add32124`.
- **Denominator:** audited-valid rows only. An oracle pass from a run-failed or
  audit-failed row is reported in `resolved_but_run_failed` /
  `resolved_but_audit_failed` and never in the headline.
- **95% CI:** Clopper-Pearson exact.
- **Paired test:** **McNemar exact**, two-sided, over instances where **both**
  arms have an audited-valid row.
- **Secondary, pre-committed:** total `$` (price-table estimate over measured
  tokens — one basis, comparable between these two arms), `$ / resolved`,
  `reviewer_cycles` (must be **0** on every `solo-noreview` row — a non-zero
  value means the ablation did not apply and the row is void), median wall
  clock, fresh input tokens, and chain-verdict precision/recall.

## The prediction

**Written down before the run, as a point estimate, not as a hypothesis test.**

1. **No material change in resolve rate.** `solo-noreview` lands within ±2
   instances of `factory`'s 7/19, i.e. **5–9 of 19 (26–47%)**. Point estimate:
   **7/19 = 37%**.
2. **Roughly 25% lower cost.** Point estimate **~$27** total against `factory`'s
   $35.94, i.e. **$25–30**. The reviewer is 31 of the published run's 70 model
   calls but on the cheaper-per-call side of the mix, and removing it also
   removes the dev re-work each cycle triggers.
3. **`reviewer_cycles = 0` on every row**, `dev_retries` unchanged in
   distribution.

## The MDE, and why no decision rule here is a significance test

**At n=19, k=1 the MDE is ≈ ±38 pp** (Fisher, 80% power, α=.05, against the
published baseline). The archives contain 10 same-condition factory
replications: 0/10 oracle flips, i.e. a 95% upper bound of 25.9% on the
per-instance flip probability, which is **±3 instances at n=19**.

Therefore, and this binds every sentence written about this run:

- **No decision rule below is phrased as a significance test.** No "p < 0.05",
  no "significant", no "detected". The McNemar p is reported because the shape
  of the pre-registered tables requires it, and it is reported as a **descriptive
  discordance statistic**, not as a decision input.
- Differences smaller than ~38 pp are **not measurable here**. A null is
  therefore the *expected* outcome and is *useful*: it is what licenses B.1
  Phase 1b to proceed on cost grounds.
- A null **cannot** be reported as "the reviewer does nothing". It can only be
  reported as "removing the reviewer did not move the resolve rate by an amount
  this design can see, and it cost ~25% less".

## Pre-committed decision rules

1. **`only-factory ≥ 5 of 19` is a STOP signal for B.1.** If the factory arm
   resolves five or more instances that `solo-noreview` misses, the reviewer is
   doing real work on this task shape. That gets said plainly, in these words,
   and B.1 does not proceed on this evidence.
2. **Report `only-factory` and `only-solo` separately**, never only their
   difference. The net is the least informative number on the page.
3. **A null result is the expected and useful outcome. Do not tune anything to
   move the number.** If the arm is iterated on at all, **every iteration is
   disclosed with its own number**, because selecting the best of k on the test
   set is exactly how earlier results here were retracted.
4. **This licenses nothing in production.** It measures **one task shape**:
   single-issue patching against a hidden oracle. Loop 1 builds an app from a
   backlog — a different shape, and the one where role decomposition has
   published support (P4/CAID: isolated worktrees + branch-and-merge, +6.0 pp at
   the frontier model and +14.7 pp at the weakest, on Commit0-Lite). No
   sentence anywhere may read as "the reviewer can be removed from the factory".
5. **Cost is a first-class outcome.** If the resolve rate is unchanged and the
   cost falls, that is the finding, and it is a cost finding — not a quality
   finding.
6. **Empty / test-only production diff audit.** Count and report every row where
   the chain certified green (`factory_says_green: true`) on a production diff
   that is empty or contains no production file. That class exists in the record
   — `harumiweb__exstruct-113 / factory` went green on a zero-byte patch
   (`prediction_sha256: e3b0c442…7852b855`) — and A.2's precondition now guards
   it. The count is reported either way, including zero.
7. **Integrity rows are published, not repaired.** Oracle-probe hits, retrieval
   actions, refused paths, acceptance-trail hits: each publishes the row as
   invalid with its reason.

## Tables, fixed now

### Table B1-1 — headline

| arm | harness | model(s) the LEDGER says ran | resolved / audited-valid | rate | 95% CI (Clopper-Pearson) | invalid rows | budget-exhausted | fresh in | cache read | out | wall s (median) | $ | $ / resolved |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| factory | | | / | % | [ , ] | | | | | | | | |
| solo-noreview | | | / | % | [ , ] | | | | | | | | |

### Table B1-2 — per-instance outcome matrix

`R` resolved · `F` wrong patch · `E` empty patch · `X` audit-invalid ·
`!` budget-exhausted (counted, never excluded)

One row per pinned instance, both arms, plus the discordance column.

### Table B1-3 — the paired comparison

| comparison | harness varies? | model varies? | paired n | only-factory / only-solo | McNemar exact p (descriptive) | what it isolates |
|---|---|---|---:|---:|---:|---|
| factory vs solo-noreview | yes (reviewer round-trip) | no — both `azure/deepseek-v4-pro` nominal | | / | | **the reviewer round-trip** |

### Table B1-4 — provenance and integrity, per arm

| arm | model ids recorded | per-tier call counts | attempts (must be 1) | audit ok / invalid | trajectories | test files stripped | oracle-probe hits | reviewer_cycles distribution | green-on-empty-diff rows |
|---|---|---|---|---|---|---|---|---|---|
| factory | | | | | | | | | |
| solo-noreview | | | | | | | | | |

### Table B1-5 — chain-verdict quality, per arm

| arm | green definition | precision — P(oracle passes \| chain said green) | recall — P(chain said green \| oracle passes) |
|---|---|---|---|
| factory | `reviewer_done` | / | / |
| solo-noreview | `tests_green` | / | / |

## What this run cannot show

- **Whether the reviewer helps on any other task shape.** It measures
  single-issue patching only. See decision rule 4.
- **Whether removing the reviewer is safe in production.** The production merge
  path has gates this driver never runs (full suite, runtime smoke, CI,
  auto-merge). Removing a reviewer there is a different change with a different
  risk surface.
- **Any difference smaller than ~38 pp.** See the MDE section.
- **Anything about the acceptance oracle's merge gate**, which is not enforced
  in either arm (`gate_enforced: false`).

## Reporting rule

Never report a `solo-noreview` number without the `factory` number beside it,
and never report either without the archive it came from. The result file is
`bench/swebench/RESULTS-B1-PHASE1A.md`. `bench/swebench/results.md` is the
report output for a specific archive and is **not** touched by this run.

---

# Addendum — recorded 2026-08-05, mid-run, with 1 of 19 outcomes known

**Nothing above this line was edited.** This addendum is appended because the
confound section above is **incomplete**, and recording that now — before 18 of
the 19 outcomes exist — is worth more than recording it afterwards. State of
knowledge when this was written: the arm code was committed, one paid row had
completed (`conan-io__conan-19735_interface`: chain green, oracle unresolved,
`right_place_wrong_fix`, $0.2935) and the sweep over the other 18 was in flight.

## A second confound, found by checking

The section above disclosed one difference between `solo-noreview` and the
archived `factory` rows (the acceptance-oracle authoring layer). Checking the
commit log against the archived rows' own timestamps found another.

The archived `factory` rows ran **2026-08-03 19:42–20:59 UTC**. Three commits
touched `factory/**` after that:

| commit | date | reaches the bench driver? |
|---|---|---|
| `7a2d7a68` A.2 production-diff precondition + A.3 underspecified terminal state | 2026-08-05 01:30 UTC | **A.3 YES, A.2 no** |
| `69b75d1e` acceptance oracle executable, harness hint | 2026-08-05 19:07 UTC | partly (via the acceptance layer) |
| `79d3576d` A.5 diff-scoped mutation score | 2026-08-05 21:38 UTC | **no** |

Verified rather than assumed:

- **A.2 is a MERGE gate** (`factory/chain/gates/production_tree_changed.py`,
  reached through `auto_merge`/the gate evaluator). This driver has no merge step
  and never calls either — `grep` for `auto_merge`/`evaluate_gates` in
  `bench/swebench_adapter.py` returns nothing. **Nil for both arms.**
- **A.5 touches `gates/tests_meaningful.py` and `auto_merge.py`** — merge-gate
  territory, same argument. **Nil for both arms.**
- **A.3 DOES reach it**, and it is the one that matters: `7a2d7a68` added **35
  lines to `factory/personas/dev.md`** ("Declaring the story underspecified"),
  plus the `blocked_underspecified` state-machine edge and the driver's terminal
  state. So the **dev persona prompt itself differs** between `solo-noreview` and
  the archived `factory` rows. That is a difference on the primary metric's own
  path, and it was not disclosed above.

## What this does to the claim

The paired comparison therefore varies **three** things, not one:

1. the reviewer round-trip (intended);
2. the dev persona prompt (+35 lines, the underspecified escape hatch);
3. the presence of the acceptance-oracle authoring layer.

**So this run BOUNDS the reviewer's contribution; it does not measure it.**
Combined with the ±38 pp MDE already pre-committed above, the honest reading is
narrower than the one this file was written for:

- **Decision rule 1 still stands and is still worth the money.** `only-factory ≥
  5 of 19` is a gross-effect signal, and none of the three variables plausibly
  manufactures five discordant instances in the factory's favour.
- **The cost comparison is the robust half** and is unaffected by confounds 2 and
  3 in any material way (confound 3 adds ~$0.02 per `solo-noreview` row, i.e.
  against it).
- **No sentence in the results file may call this a clean single-variable
  ablation.** It is a bounded probe with a same-commit baseline missing.

## Why it is not fixed by re-running

A same-commit `factory` re-run is the correct fix and costs ~$36 on top of this
arm, which breaches the **$50 hard stop** this run was authorised under. It is
therefore recorded as **the first requirement of B.1 Phase 1b**: run both arms
on ONE commit, in one sweep, before any decision. Re-running only the discordant
instances would be selection on the outcome and is forbidden by Rule 5 above.

## A prediction that is already known to be wrong in its reasoning

Prediction 2 above said "roughly 25% lower cost", reasoning that "the reviewer is
31 of the published run's 70 model calls but on the cheaper-per-call side". The
archived ledger, read while this addendum was written, says the reviewer is
**$0.65 of $35.94 — 1.8%**; the dev is $32.81 of it across 33 calls. So the
mechanism for any saving is **fewer dev calls**, not the reviewer's own tokens.
The point estimate ($25–30) stands as pre-committed and will be scored as
written; the reasoning behind it was wrong and is corrected here rather than
quietly in the results.
